export type TaskStatus = "processing" | "completed" | "failed";

export interface OcrTaskResult {
  bookName: string;
  totalPages: number;
  processedPages: number;
  failedPages: number[];
  files: { fileName: string; content: string }[];
}

export interface OcrTask {
  id: string;
  status: TaskStatus;
  progress: number; // 0-100
  createdAt: number;
  updatedAt: number;
  result: OcrTaskResult | null;
  error: string | null;
}
