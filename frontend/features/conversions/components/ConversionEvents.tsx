"use client";

import { AlertCircle, CheckCircle2, History, Loader2, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "cn";
import { useConversionEvents } from "../hooks/useConversions";
import type { ConversionEvent } from "../types";

const KIND_META: Record<string, { label: string; dot: string }> = {
  queued: { label: "استلام", dot: "bg-amber-500" },
  started: { label: "بدء المعالجة", dot: "bg-sky-500" },
  page_done: { label: "صفحة ناجحة", dot: "bg-emerald-500" },
  page_failed: { label: "صفحة فاشلة", dot: "bg-red-500" },
  paused: { label: "إيقاف مؤقت", dot: "bg-amber-500" },
  resumed: { label: "استئناف", dot: "bg-sky-500" },
  requeued: { label: "إعادة للطابور", dot: "bg-sky-500" },
  cancelled: { label: "إلغاء", dot: "bg-red-500" },
  completed: { label: "اكتمال", dot: "bg-emerald-500" },
  partial: { label: "اكتمال جزئي", dot: "bg-orange-500" },
  failed: { label: "فشل", dot: "bg-red-500" },
  asset_skipped: { label: "أصل متخطى", dot: "bg-orange-400" },
  log_warning: { label: "تحذير", dot: "bg-yellow-500" },
  queue_unavailable: { label: "الطابور غير متاح", dot: "bg-yellow-500" },
};

function EventRow({ event }: { event: ConversionEvent }) {
  const meta = KIND_META[event.kind] ?? { label: event.kind, dot: "bg-muted-foreground" };
  return (
    <li className="flex items-start gap-2 text-sm">
      <span className={cn("mt-1.5 size-2 shrink-0 rounded-full", meta.dot)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <span className="font-medium">
          {meta.label}
          {event.page_number !== null ? ` — صفحة ${event.page_number}` : ""}
        </span>
        <span className="text-xs text-muted-foreground">
          {[event.method, event.quality !== null ? `${Math.round(event.quality * 100)}٪` : null]
            .filter(Boolean)
            .join(" • ") || event.note || ""}
        </span>
        {event.kind === "page_failed" && event.note && (
          <span className="text-xs text-destructive">{event.note}</span>
        )}
        {(event.kind === "asset_skipped" ||
          event.kind === "log_warning" ||
          event.kind === "queue_unavailable") &&
          event.note && (
            <span className="text-xs text-muted-foreground">{event.note}</span>
          )}
      </div>
    </li>
  );
}

/**
 * بطاقة سجل الأحداث تحت بطاقة التحويل — قراءة فقط عبر TanStack Query،
 * تحديث كل ثانيتين أثناء نشاط التحويل.
 */
export function ConversionEvents({ id, active }: { id: string; active: boolean }) {
  const { data, isPending, isError } = useConversionEvents(id, active);
  const events = data?.data ?? [];

  return (
    <Card className="rounded-2xl bg-white shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <History className="size-4 text-muted-foreground" />
          أحداث التحويل
          {events.length > 0 && (
            <span className="text-xs font-normal text-muted-foreground">
              ({events.length})
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isPending && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            جارٍ تحميل الأحداث...
          </p>
        )}
        {isError && (
          <p className="flex items-center gap-2 text-sm text-destructive">
            <XCircle className="size-4" />
            تعذر جلب الأحداث.
          </p>
        )}
        {!isPending && !isError && events.length === 0 && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <AlertCircle className="size-4" />
            لا أحداث بعد.
          </p>
        )}
        {events.length > 0 && (
          <ul className="flex max-h-64 flex-col gap-2 overflow-y-auto">
            {events.map((event) => (
              <EventRow
                key={`${event.id}-${event.kind}-${event.page_number ?? "na"}`}
                event={event}
              />
            ))}
          </ul>
        )}
        {events.some((event) => event.kind === "page_done" && event.quality !== null) && (
          <p className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
            <CheckCircle2 className="size-3" />
            الجودة من بوابة الفحص (تشمل جزاء CAMeL عند تفعيله).
          </p>
        )}
      </CardContent>
    </Card>
  );
}
