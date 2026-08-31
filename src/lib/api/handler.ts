import { NextRequest, NextResponse } from "next/server";
import { normalizeError } from "./errors";
import { apiError, type ApiFailure } from "./response";

type RouteHandler<Ctx> = (
  req: NextRequest,
  ctx: Ctx
) => Promise<NextResponse>;

/**
 * يغلّف أي route handler بمعالجة أخطاء موحّدة. أي خطأ يُرمى داخل الـ handler
 * (سواء AppError مقصود أو خطأ غير متوقع) يُحوَّل تلقائيًا لاستجابة JSON
 * بنفس الشكل عبر apiError، بدل try/catch مكرر في كل route على حدة.
 *
 * الاستخدام:
 * ```ts
 * export const POST = withErrorHandling(async (req) => {
 *   if (!ok) throw new ValidationError("رسالة الخطأ");
 *   return apiSuccess({ ... });
 * });
 * ```
 */
export function withErrorHandling<Ctx = unknown>(
  handler: RouteHandler<Ctx>
): RouteHandler<Ctx> {
  return async (req, ctx) => {
    try {
      return await handler(req, ctx);
    } catch (err) {
      const appError = normalizeError(err);
      return apiError(appError) as NextResponse<ApiFailure>;
    }
  };
}
