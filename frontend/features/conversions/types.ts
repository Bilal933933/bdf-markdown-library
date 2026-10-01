export type ConversionStatus =
  | "queued"
  | "processing"
  | "paused"
  | "cancelled"
  | "completed"
  | "failed"
  | "partial";

export interface ConversionError {
  code: string;
  message: string;
}

export interface Conversion {
  id: string;
  source_file: string;
  status: ConversionStatus;
  progress: number;
  total_pages: number;
  current_page: number;
  error: ConversionError | null;
}

export interface ConversionEvent {
  id: number;
  kind: string;
  page_number: number | null;
  method: string | null;
  quality: number | null;
  note: string | null;
  request_id: string | null;
  created_at: string | null;
}

export interface SuccessEnvelope<T> {
  data: T;
  meta: { request_id: string };
}

export const ACTIVE_STATUSES: ConversionStatus[] = ["queued", "processing"];
