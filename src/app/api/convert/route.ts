import { NextRequest } from "next/server";
import { ocrPdf } from "@/lib/ocr";
import { createTask, updateTaskProgress, completeTask, failTask } from "@/lib/tasks/task-store";
import { ValidationError } from "@/lib/api/errors";
import { apiSuccess } from "@/lib/api/response";
import { withErrorHandling } from "@/lib/api/handler";

export const maxDuration = 300; // اضبط حسب حدود بيئة الاستضافة

/**
 * ملاحظة نشر مهمة: معالجة كتاب كامل (مئات الصفحات) قد تستغرق دقائق —
 * أطول من timeout أي طلب HTTP واحد. لذلك هذا المسار لا ينتظر اكتمال
 * المعالجة: يُنشئ مهمة ويبدأ التنفيذ في الخلفية، ويعيد `taskId` فورًا.
 * الواجهة تستطلع `/api/status/:taskId` لمتابعة التقدم.
 *
 * ⚠️ هذا النمط ("fire and forget" بعد إرجاع الاستجابة) يعمل بشكل موثوق فقط
 * إن كان السيرفر عملية Node طويلة العمر. لا تعتمد عليه على منصة serverless
 * بدون queue حقيقي (BullMQ مثلًا).
 */
export const POST = withErrorHandling(async (req: NextRequest) => {
  const formData = await req.formData();
  const file = formData.get("file");

  if (!(file instanceof File)) {
    throw new ValidationError("لم يتم رفع أي ملف PDF.");
  }

  // تحقق فعلي من نوع الملف في الباك إند (لا يكفي التحقق في الواجهة فقط)
  if (file.type !== "application/pdf") {
    throw new ValidationError("الملف يجب أن يكون بصيغة PDF.", {
      receivedType: file.type,
    });
  }

  const bookName = file.name.replace(/\.pdf$/i, "");
  const buffer = Buffer.from(await file.arrayBuffer());

  const task = await createTask();

  // يعمل في الخلفية بعد إرجاع الاستجابة — لا ننتظره هنا، وأخطاؤه تُسجَّل
  // على المهمة نفسها (failTask) لا كاستجابة HTTP، لأن الاستجابة أُرسلت أصلًا.
  runInBackground(task.id, buffer, bookName);

  return apiSuccess({ taskId: task.id }, 202);
});

async function runInBackground(taskId: string, buffer: Buffer, bookName: string) {
  try {
    const result = await ocrPdf(buffer, {
      bookName,
      onProgress: ({ page, totalPages }) => {
        const percent = Math.round((page / totalPages) * 100);
        void updateTaskProgress(taskId, percent);
      },
    });

    await completeTask(taskId, {
      bookName: result.bookName,
      totalPages: result.totalPages,
      processedPages: result.processedPages,
      failedPages: result.failedPages,
      files: result.parts.map((p) => ({ fileName: p.fileName, content: p.content })),
    });
  } catch (error) {
    console.error("OCR background error:", error);
    await failTask(
      taskId,
      error instanceof Error ? error.message : "خطأ غير معروف أثناء المعالجة"
    );
  }
}
