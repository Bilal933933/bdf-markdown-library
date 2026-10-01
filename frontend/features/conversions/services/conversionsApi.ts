import { apiClient, fetchOutputText } from "@/lib/apiClient";
import { buildListQuery } from "@/lib/query";
import type { Conversion, ConversionEvent, SuccessEnvelope } from "../types";

export function listConversions(limit = 20, offset = 0) {
  return apiClient<SuccessEnvelope<Conversion[]>>(
    `/conversions${buildListQuery({ limit, offset })}`
  );
}

export function getConversion(id: string) {
  return apiClient<SuccessEnvelope<Conversion>>(`/conversions/${id}`);
}

export function getConversionEvents(id: string) {
  return apiClient<SuccessEnvelope<ConversionEvent[]>>(`/conversions/${id}/events`);
}

export function getDocumentMarkdown(id: string) {
  return fetchOutputText(id, "document.md");
}

function controlConversion(id: string, action: "retry" | "pause" | "resume" | "cancel") {
  return apiClient<SuccessEnvelope<Conversion>>(`/conversions/${id}/${action}`, {
    method: "POST",
  });
}

export function retryConversion(id: string) {
  return controlConversion(id, "retry");
}

export function pauseConversion(id: string) {
  return controlConversion(id, "pause");
}

export function resumeConversion(id: string) {
  return controlConversion(id, "resume");
}

export function cancelConversion(id: string) {
  return controlConversion(id, "cancel");
}

export function uploadConversion(file: File) {
  const form = new FormData();
  form.append("file", file);
  return apiClient<SuccessEnvelope<Conversion>>("/conversions", {
    method: "POST",
    body: form,
  });
}
