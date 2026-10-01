"use client";

import { useEffect, useState } from "react";
import {
  AlertCircle,
  Ban,
  CheckCircle2,
  Download,
  ExternalLink,
  FileText,
  Inbox,
  Loader2,
  Pause,
  Play,
  RotateCcw,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn } from "cn";
import { outputUrl } from "@/lib/apiClient";
import { ConversionEvents } from "./ConversionEvents";
import {
  useCancelConversion,
  useConversionStatus,
  useConversionsList,
  usePauseConversion,
  useResumeConversion,
  useRetryConversion,
} from "../hooks/useConversions";
import type { Conversion, ConversionStatus } from "../types";

const STATUS_META: Record<ConversionStatus, { label: string; dot: string; hint: string }> = {
  queued: {
    label: "في الطابور",
    dot: "bg-amber-500",
    hint: "بانتظار عامل المعالجة لبدء هذا الكتاب.",
  },
  processing: {
    label: "يُعالج",
    dot: "bg-sky-500 animate-pulse",
    hint: "جارٍ استخراج الصفحات وتحويلها.",
  },
  completed: {
    label: "مكتمل",
    dot: "bg-emerald-500",
    hint: "اكتمل التحويل — يمكنك المعاينة والتنزيل.",
  },
  failed: {
    label: "فشل",
    dot: "bg-red-500",
    hint: "تعذر إكمال التحويل — راجع رسالة الخطأ.",
  },
  partial: {
    label: "جزئي",
    dot: "bg-orange-500",
    hint: "اكتمل جزئيًا — بعض الصفحات تعذرت.",
  },
  paused: {
    label: "موقوف",
    dot: "bg-slate-400",
    hint: "متوقف مؤقتًا — استأنف لإكمال التحويل من حيث توقف.",
  },
  cancelled: {
    label: "ملغي",
    dot: "bg-zinc-500",
    hint: "أُلغي هذا التحويل نهائيًا.",
  },
};

function StatusBadge({ status }: { status: ConversionStatus }) {
  const meta = STATUS_META[status];
  const pill =
    status === "completed"
      ? "border-emerald-100 bg-emerald-50 text-emerald-700"
      : status === "failed"
        ? "border-red-100 bg-red-50 text-red-600"
        : "border-border bg-muted text-muted-foreground";
  return (
    <Badge variant="outline" className={cn("gap-1.5 rounded-full px-2.5 py-1", pill)}>
      <span className={cn("size-1.5 shrink-0 rounded-full", meta.dot)} />
      {meta.label}
    </Badge>
  );
}

function ListSkeleton() {
  return (
    <div className="flex flex-col gap-2" aria-hidden>
      {[0, 1, 2].map((i) => (
        <div key={i} className="flex items-center gap-3 rounded-lg border p-3">
          <div className="size-9 animate-pulse rounded-lg bg-muted" />
          <div className="flex flex-1 flex-col gap-1.5">
            <div className="h-3.5 w-2/3 animate-pulse rounded bg-muted" />
            <div className="h-3 w-1/3 animate-pulse rounded bg-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ConversionsList({
  onSelect,
  selectedId,
}: {
  onSelect: (id: string) => void;
  selectedId: string | null;
}) {
  const { data, isPending, error, refetch } = useConversionsList();
  const items = data?.data ?? [];

  return (
    <Card className="rounded-2xl bg-white shadow-sm">
      <CardHeader>
        <CardTitle className="text-lg">التحويلات</CardTitle>
        <CardDescription>
          {items.length > 0 ? `${items.length} عناصر — الأحدث أولًا` : "كل كتبك المحوّلة في مكان واحد"}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {isPending && <ListSkeleton />}
        {error && (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed p-6 text-center">
            <AlertCircle className="size-6 text-destructive" />
            <p className="text-sm text-destructive">تعذر جلب القائمة.</p>
            <button
              onClick={() => refetch()}
              className="text-sm font-medium text-primary underline underline-offset-4"
            >
              إعادة المحاولة
            </button>
          </div>
        )}
        {!isPending && !error && items.length === 0 && (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed p-8 text-center">
            <Inbox className="size-8 text-muted-foreground" />
            <p className="text-sm font-medium">لا توجد تحويلات بعد</p>
            <p className="text-xs text-muted-foreground">ارفع كتابك الأول لبدء التحويل.</p>
          </div>
        )}
        {items.map((item) => {
          const selected = item.id === selectedId;
          return (
            <button
              key={item.id}
              onClick={() => onSelect(item.id)}
              aria-current={selected}
              className={cn(
                "flex w-full items-center gap-3 rounded-xl border bg-white p-3 text-right shadow-sm transition-colors hover:bg-accent",
                selected && "border-primary bg-accent"
              )}
            >
              <span className="flex flex-col items-center gap-0.5 rounded-lg bg-red-50/60 p-2">
                <FileText className="size-5 text-red-500" />
                <span className="text-[9px] font-bold text-red-500">PDF</span>
              </span>
              <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="truncate text-sm font-medium">{item.source_file}</span>
                <span className="text-xs text-muted-foreground">
                  {item.total_pages > 0 ? `${item.total_pages} صفحة • ` : ""}
                  {item.progress}٪
                </span>
              </span>
              <StatusBadge status={item.status} />
            </button>
          );
        })}
      </CardContent>
    </Card>
  );
}

const OUTPUT_FILES = [
  { key: "document.md", label: "المستند" },
  { key: "metadata.json", label: "البيانات" },
  { key: "assets.json", label: "الأصول" },
] as const;

export function ConversionDetails({ id }: { id: string }) {
  const { data, isPending, dataUpdatedAt } = useConversionStatus(id);
  const retry = useRetryConversion();
  const pause = usePauseConversion();
  const resume = useResumeConversion();
  const cancel = useCancelConversion();
  const conversion: Conversion | undefined = data?.data;

  const [now, setNow] = useState(0);
  const [baseline, setBaseline] = useState({ progress: -1, at: 0 });

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(timer);
  }, []);

  if (conversion && conversion.progress !== baseline.progress) {
    setBaseline({ progress: conversion.progress, at: dataUpdatedAt });
  }

  if (isPending || !conversion) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          جارٍ تحميل حالة التحويل...
        </CardContent>
      </Card>
    );
  }

  const meta = STATUS_META[conversion.status];
  const done = conversion.status === "completed" || conversion.status === "partial";
  const active = conversion.status === "queued" || conversion.status === "processing";
  const retryable = conversion.status === "failed" || conversion.status === "partial";
  const pausable = conversion.status === "processing";
  const resumable = conversion.status === "paused";
  const cancellable =
    conversion.status === "queued" ||
    conversion.status === "processing" ||
    conversion.status === "paused";
  const stalled = active && baseline.at > 0 && now - baseline.at > 5 * 60_000;
  const busy = retry.isPending || pause.isPending || resume.isPending || cancel.isPending;

  const confirmCancel = () => {
    if (window.confirm("إلغاء التحويل نهائيًا؟ لا يمكن التراجع.")) {
      cancel.mutate(conversion.id);
    }
  };

  return (
    <div className="flex flex-col gap-5">
    <Card className="rounded-2xl bg-white shadow-sm">
      <CardHeader>
        <div className="flex items-start gap-3">
          <span className="rounded-lg bg-muted p-2.5">
            {conversion.status === "completed" ? (
              <CheckCircle2 className="size-5 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <FileText className="size-5 text-muted-foreground" />
            )}
          </span>
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <CardTitle className="truncate text-base">{conversion.source_file}</CardTitle>
            <CardDescription>{meta.hint}</CardDescription>
          </div>
          <StatusBadge status={conversion.status} />
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-2 rounded-lg bg-muted/50 p-3">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">التقدم</span>
            <span className="font-mono text-muted-foreground">{conversion.progress}٪</span>
          </div>
          <Progress value={conversion.progress} />
          <p className="text-xs text-muted-foreground">
            الصفحة {conversion.current_page} من {conversion.total_pages}
            {active && conversion.status === "processing" ? " — التحديث تلقائي" : ""}
          </p>
        </div>

        {conversion.error && (
          <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3">
            <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
            <p className="text-sm text-destructive">{conversion.error.message}</p>
          </div>
        )}

        {stalled && (
          <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
            <AlertCircle className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400" />
            <p className="text-sm text-amber-700 dark:text-amber-300">
              لا تقدم منذ أكثر من 5 دقائق — تحقق من عمل العامل ثم أعد المحاولة.
            </p>
          </div>
        )}

        {(retryable || pausable || resumable || cancellable) && (
          <div className="flex flex-wrap gap-2">
            {retryable && (
              <Button
                variant="outline"
                size="sm"
                disabled={busy}
                onClick={() => retry.mutate(conversion.id)}
              >
                <RotateCcw className="size-3.5" />
                {retry.isPending ? "جارٍ..." : "إعادة المحاولة"}
              </Button>
            )}
            {pausable && (
              <Button
                variant="outline"
                size="sm"
                disabled={busy}
                onClick={() => pause.mutate(conversion.id)}
              >
                <Pause className="size-3.5" />
                {pause.isPending ? "جارٍ..." : "إيقاف مؤقت"}
              </Button>
            )}
            {resumable && (
              <Button
                variant="outline"
                size="sm"
                disabled={busy}
                onClick={() => resume.mutate(conversion.id)}
              >
                <Play className="size-3.5" />
                {resume.isPending ? "جارٍ..." : "استئناف"}
              </Button>
            )}
            {cancellable && (
              <Button
                variant="ghost"
                size="sm"
                disabled={busy}
                onClick={confirmCancel}
                className="text-destructive hover:text-destructive"
              >
                <Ban className="size-3.5" />
                {cancel.isPending ? "جارٍ..." : "إلغاء"}
              </Button>
            )}
          </div>
        )}

        {done && (
          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium">المخرجات</p>
            <div className="flex flex-wrap gap-2">
              <a
                href={`/conversions/${conversion.id}/preview`}
                target="_blank"
                rel="noopener noreferrer"
                className={buttonVariants({ variant: "default", size: "sm" })}
              >
                <ExternalLink className="size-3.5" />
                معاينة
              </a>
              {OUTPUT_FILES.map((file) => (
                <a
                  key={file.key}
                  href={outputUrl(conversion.id, file.key)}
                  download
                  className={buttonVariants({ variant: "outline", size: "sm" })}
                >
                  <Download className="size-3.5" />
                  {file.label}
                </a>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
    <ConversionEvents id={conversion.id} active={active} />
    </div>
  );
}
