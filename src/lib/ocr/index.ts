import { getConfig } from "../config";
import { loadPdf } from "./pdf-renderer";
import { ocrPageImage } from "./gemini-client";
import { buildParts, type PageResult, type PartFile } from "./part-writer";

export type { PartFile } from "./part-writer";

export interface OcrPdfOptions {
  /** أول صفحة تُعالج (تبدأ من 1). الافتراضي: 1 */
  startPage?: number;
  /** آخر صفحة تُعالج. الافتراضي: آخر صفحة في الملف */
  endPage?: number;
  /** اسم الكتاب المستخدَم في ترويسات الأجزاء */
  bookName: string;
  /** استدعاء يُبلَّغ عند اكتمال كل صفحة، لتحديث تقدّم المهمة */
  onProgress?: (info: { page: number; totalPages: number }) => void;
}

export interface OcrPdfResult {
  bookName: string;
  totalPages: number;
  processedPages: number;
  failedPages: number[];
  parts: PartFile[];
}

/**
 * يحوّل ملف PDF (في الذاكرة) إلى ملفات Markdown مقسّمة على أجزاء،
 * عبر Gemini Vision OCR.
 *
 * هذه الدالة تحل محل استدعاء `exec("node gemini-ocr.mjs ...")` بالكامل:
 * لا سطر أوامر، لا shell، لا مسارات مبنية من مدخلات مستخدم غير مُعقَّمة —
 * وبالتالي لا ثغرة command injection.
 *
 * مثال استخدام داخل Next.js API route:
 * ```ts
 * const buffer = Buffer.from(await file.arrayBuffer());
 * const result = await ocrPdf(buffer, { bookName: "كتاب النحو" });
 * ```
 */
export async function ocrPdf(
  pdfBuffer: Buffer,
  options: OcrPdfOptions
): Promise<OcrPdfResult> {
  const config = getConfig();
  const pdf = await loadPdf(pdfBuffer);

  try {
    const start = options.startPage ?? 1;
    const end = Math.min(options.endPage ?? pdf.numPages, pdf.numPages);

    if (start < 1 || start > end) {
      throw new Error(
        `نطاق صفحات غير صالح: start=${start}, end=${end}, numPages=${pdf.numPages}`
      );
    }

    const pages: PageResult[] = [];
    const failedPages: number[] = [];

    for (let pageNum = start; pageNum <= end; pageNum++) {
      let text: string;
      let failed = false;

      try {
        const imageBuffer = await pdf.getPageImage(pageNum);
        text = await ocrPageImage(imageBuffer.toString("base64"), config);
      } catch (e) {
        failed = true;
        failedPages.push(pageNum);
        text = `[تعذر استخراج النص من الصفحة ${pageNum}]`;
      }

      pages.push({ pageNumber: pageNum, text, failed });
      options.onProgress?.({ page: pageNum, totalPages: end });

      // فاصل بسيط بين الطلبات لتفادي الضغط على حصة الـ API
      if (pageNum < end) {
        await new Promise((r) => setTimeout(r, config.pageDelayMs));
      }
    }

    const parts = buildParts(
      pages,
      options.bookName,
      pdf.numPages,
      config.pagesPerPart
    );

    return {
      bookName: options.bookName,
      totalPages: pdf.numPages,
      processedPages: pages.length,
      failedPages,
      parts,
    };
  } finally {
    pdf.destroy();
  }
}
