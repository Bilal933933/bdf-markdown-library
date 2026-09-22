import { toast } from "sonner";

export interface ApiError {
  status: number;
  code?: string;
  message: string;
  details?: unknown;
}

export function isApiError(error: unknown): error is ApiError {
  return typeof error === "object" && error !== null && "status" in error;
}

const NETWORK_MESSAGE = "تعذّر الاتصال بالخادم. تحقق من اتصالك وأعد المحاولة.";
const DEFAULT_MESSAGE = "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.";

export function getErrorMessage(error: unknown, fallback = DEFAULT_MESSAGE): string {
  if (error instanceof TypeError) {
    return NETWORK_MESSAGE;
  }

  const apiError = error as Partial<ApiError> | null;
  return apiError?.message ?? fallback;
}

export function showApiError(error: unknown, fallback?: string): void {
  toast.error(getErrorMessage(error, fallback));
}
