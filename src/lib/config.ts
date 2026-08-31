/**
 * إعدادات التطبيق — تُقرأ وتُتحقق مرة واحدة عند الإقلاع (fail-fast)
 * بدل اكتشاف غياب مفتاح API في منتصف معالجة كتاب من 400 صفحة.
 */

export interface AppConfig {
  geminiKeys: string[];
  geminiModel: string;
  geminiFallbackModels: string[];
  geminiPrompt: string;
  pagesPerPart: number;
  requestTimeoutMs: number;
  maxRetriesPerPage: number;
  pageDelayMs: number;
}

function parseList(value: string | undefined, fallback: string[]): string[] {
  if (!value) return fallback;
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

let cached: AppConfig | null = null;

/**
 * يقرأ ويتحقق من متغيرات البيئة. يرمي خطأ واضحًا فورًا إن كانت ناقصة،
 * بدل فشل غامض بعد دقائق من معالجة OCR.
 */
export function getConfig(): AppConfig {
  if (cached) return cached;

  const geminiKeys = parseList(
    process.env.GEMINI_KEYS ?? process.env.GEMINI_API_KEY,
    []
  );

  if (geminiKeys.length === 0) {
    throw new Error(
      "GEMINI_API_KEY أو GEMINI_KEYS غير مضبوط. أضفه في ملف .env (راجع .env.example)."
    );
  }

  cached = {
    geminiKeys,
    geminiModel: process.env.GEMINI_MODEL || "gemini-3-flash-preview",
    geminiFallbackModels: parseList(process.env.GEMINI_FALLBACK, [
      "gemini-3.1-flash-lite",
      "gemini-3.1-flash-lite-preview",
      "gemini-3.5-flash-lite",
      "gemini-flash-latest",
    ]),
    geminiPrompt:
      process.env.GEMINI_PROMPT || "انسخ محتوى هذه الصفحة نصًا فقط، لا شيء آخر.",
    pagesPerPart: Number(process.env.PAGES_PER_PART) || 40,
    requestTimeoutMs: Number(process.env.OCR_TIMEOUT_MS) || 90_000,
    maxRetriesPerPage: Number(process.env.OCR_MAX_RETRIES) || 20,
    pageDelayMs: Number(process.env.OCR_PAGE_DELAY_MS) || 600,
  };

  return cached;
}

/** يُستخدم في الاختبارات فقط لإعادة ضبط القيم المخزّنة مؤقتًا. */
export function resetConfigCache(): void {
  cached = null;
}
