import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { showApiError } from "@/lib/apiErrors";
import {
  cancelConversion,
  getConversion,
  getConversionEvents,
  getDocumentMarkdown,
  listConversions,
  pauseConversion,
  resumeConversion,
  retryConversion,
  uploadConversion,
} from "../services/conversionsApi";
import { ACTIVE_STATUSES } from "../types";
import type { Conversion, SuccessEnvelope } from "../types";

export const CONVERSIONS_KEY = ["conversions"] as const;

export function useConversionsList() {
  return useQuery({
    queryKey: CONVERSIONS_KEY,
    queryFn: () => listConversions(20, 0),
  });
}

export function useConversionStatus(id: string | null) {
  return useQuery({
    queryKey: ["conversion", id],
    queryFn: () => getConversion(id as string),
    enabled: id !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.data.status;
      return status !== undefined && ACTIVE_STATUSES.includes(status) ? 2000 : false;
    },
  });
}

export function useDocumentMarkdown(id: string, enabled = true) {
  return useQuery({
    queryKey: ["conversion", id, "document.md"],
    queryFn: () => getDocumentMarkdown(id),
    enabled,
  });
}

export function useConversionEvents(id: string | null, active: boolean) {
  return useQuery({
    queryKey: ["conversion", id, "events"],
    queryFn: () => getConversionEvents(id as string),
    enabled: id !== null,
    refetchInterval: active ? 2000 : false,
  });
}

function useControlMutation(
  action: (id: string) => Promise<SuccessEnvelope<Conversion>>,
  successMessage: string
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => action(id),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["conversion", result.data.id] });
      queryClient.invalidateQueries({ queryKey: CONVERSIONS_KEY });
      toast.success(successMessage);
    },
    onError: (error) => showApiError(error),
  });
}

export function useRetryConversion() {
  return useControlMutation(retryConversion, "أُعيد التحويل إلى الطابور.");
}

export function usePauseConversion() {
  return useControlMutation(pauseConversion, "أُوقف التحويل مؤقتًا.");
}

export function useResumeConversion() {
  return useControlMutation(resumeConversion, "استُؤنف التحويل.");
}

export function useCancelConversion() {
  return useControlMutation(cancelConversion, "أُلغي التحويل.");
}

export function useUploadConversion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => uploadConversion(file),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: CONVERSIONS_KEY });
      toast.success(`استُلم الملف: ${result.data.source_file}`);
    },
    onError: (error) => showApiError(error),
  });
}
