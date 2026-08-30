const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

export interface ConversionStatus {
  status: 'processing' | 'completed' | 'failed';
  progress: number;
  result?: {
    downloadUrl: string;
    fileName: string;
  };
  error?: string;
}

export async function startConversion(file: File): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${BACKEND_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('فشل في بدء التحويل');
  }

  const data = await response.json();
  return data.taskId;
}

export async function getConversionStatus(taskId: string): Promise<ConversionStatus> {
  const response = await fetch(`${BACKEND_URL}/api/status/${taskId}`);
  if (!response.ok) {
    throw new Error('فشل في جلب حالة التحويل');
  }
  return response.json();
}
