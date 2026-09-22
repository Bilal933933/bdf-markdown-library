/**
 * عميل API مركزي للتواصل مع Document Conversion Engine.
 *
 * - المصادقة عبر ترويسة X-API-Key (تُقرأ من localStorage ما لم تُمرَّر صراحة).
 * - المغلفات: نجاح {data, meta} وخطأ {error: {code, message, details}}.
 * - FormData للرفع (لا تُضبط Content-Type يدويًا معها).
 */

const ENV_API_URL = process.env.NEXT_PUBLIC_API_URL?.trim();
const ENV_API_KEY = process.env.NEXT_PUBLIC_API_KEY?.trim();

const API_BASE_URL = ENV_API_URL || "http://localhost:8123/api/v1";
const STORAGE_KEY = "dce.api_key";

export function getStoredApiKey(): string | null {
  if (typeof window === "undefined") return ENV_API_KEY ?? null;
  return window.localStorage.getItem(STORAGE_KEY) ?? ENV_API_KEY ?? null;
}

export function setStoredApiKey(key: string): void {
  window.localStorage.setItem(STORAGE_KEY, key);
}

interface RequestOptions extends RequestInit {
  /** تجاوز مفتاح التخزين المحلي */
  apiKey?: string | null;
}

interface ErrorPayload {
  error?: { code?: string; message?: string; details?: unknown };
}

/**
 * دالة الطلب الأساسية — تُستدعى فقط عبر TanStack Query، لا من المكونات مباشرة.
 */
export async function apiClient<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { apiKey, headers, ...rest } = options;

  const key = apiKey ?? getStoredApiKey();
  const isFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...rest,
    headers: {
      Accept: "application/json",
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(key ? { "X-API-Key": key } : {}),
      ...headers,
    },
  });

  if (!response.ok) {
    const errorBody = (await response.json().catch(() => null)) as
      | ErrorPayload
      | null;

    throw {
      status: response.status,
      code: errorBody?.error?.code ?? "HTTP_ERROR",
      message:
        errorBody?.error?.message ?? "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.",
      details: errorBody?.error?.details ?? null,
    };
  }

  const text = await response.text();
  return (text ? JSON.parse(text) : null) as T;
}
