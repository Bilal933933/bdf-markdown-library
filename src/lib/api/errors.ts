/**
 * تسلسل أخطاء موحّد لكل الـ API routes. كل خطأ متوقَّع في التطبيق يجب أن
 * يكون نسخة من AppError (أو أحد أصنافها الفرعية) بدل رمي Error عادي —
 * هذا يسمح لمعالج الأخطاء المركزي (api/handler.ts) بمعرفة أي حالة HTTP
 * ورمز خطأ يُرجع، دون أن يخمّن.
 */

export type ErrorCode =
  | "VALIDATION_ERROR"
  | "NOT_FOUND"
  | "UPSTREAM_ERROR"
  | "INTERNAL_ERROR";

export class AppError extends Error {
  readonly statusCode: number;
  readonly code: ErrorCode;
  /** تفاصيل إضافية آمنة للعرض للمستخدم (لا تُسرّب أسرارًا داخلية) */
  readonly details?: unknown;

  constructor(
    message: string,
    statusCode: number,
    code: ErrorCode,
    details?: unknown
  ) {
    super(message);
    this.name = new.target.name;
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}

/** مدخلات غير صالحة من المستخدم (ملف مفقود، نوع خاطئ، حقل ناقص...) */
export class ValidationError extends AppError {
  constructor(message: string, details?: unknown) {
    super(message, 400, "VALIDATION_ERROR", details);
  }
}

/** مورد مطلوب غير موجود (مهمة بمعرّف غير معروف مثلًا) */
export class NotFoundError extends AppError {
  constructor(message: string) {
    super(message, 404, "NOT_FOUND");
  }
}

/** فشل خدمة خارجية (Gemini API مثلًا) بعد استنفاد كل المحاولات */
export class UpstreamServiceError extends AppError {
  constructor(message: string, details?: unknown) {
    super(message, 502, "UPSTREAM_ERROR", details);
  }
}

/**
 * يحوّل أي خطأ (متوقَّع أو غير متوقَّع) إلى AppError صالح للإرجاع للعميل،
 * مع عدم تسريب رسائل الأخطاء الداخلية الخام للمستخدم عند الأخطاء غير المتوقعة.
 */
export function normalizeError(error: unknown): AppError {
  if (error instanceof AppError) return error;

  const message = error instanceof Error ? error.message : String(error);
  console.error("Unhandled error:", error);

  // لا نُظهر تفاصيل الخطأ الداخلي الخام للمستخدم — رسالة عامة فقط
  return new AppError("حدث خطأ غير متوقع في الخادم.", 500, "INTERNAL_ERROR", {
    // يُسجَّل في اللوج فقط عبر console.error أعلاه، لا يُرسل للعميل في details
    internal: process.env.NODE_ENV === "development" ? message : undefined,
  });
}
