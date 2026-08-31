import { NextResponse } from "next/server";
import { AppError, type ErrorCode } from "./errors";

/**
 * شكل موحّد لكل استجابات الـ API — الواجهة الأمامية تتعامل دائمًا مع نفس
 * البنية بغض النظر عن أي endpoint استُدعي، بدل أشكال JSON مختلفة لكل route.
 */
export interface ApiSuccess<T> {
  success: true;
  data: T;
}

export interface ApiFailure {
  success: false;
  error: {
    code: ErrorCode;
    message: string;
    details?: unknown;
  };
}

export type ApiResponse<T> = ApiSuccess<T> | ApiFailure;

export function apiSuccess<T>(data: T, status = 200): NextResponse<ApiSuccess<T>> {
  return NextResponse.json({ success: true, data }, { status });
}

export function apiError(error: AppError): NextResponse<ApiFailure> {
  return NextResponse.json(
    {
      success: false,
      error: {
        code: error.code,
        message: error.message,
        details: error.details,
      },
    },
    { status: error.statusCode }
  );
}
