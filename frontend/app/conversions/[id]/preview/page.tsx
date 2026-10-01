"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { MarkdownViewer } from "@/features/conversions/components/MarkdownViewer";
import {
  useConversionStatus,
  useDocumentMarkdown,
} from "@/features/conversions/hooks/useConversions";
import { getErrorMessage } from "@/lib/apiErrors";
import { outputUrl } from "@/lib/apiClient";

/**
 * صفحة معاينة مستقلة لملف document.md بنمط GitHub — تُفتح في تبويب جديد.
 * الجلب عبر TanStack Query فقط، والعرض عبر MarkdownViewer الخالص.
 */
export default function ConversionPreviewPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const { data: conversionData } = useConversionStatus(id);
  const conversion = conversionData?.data;
  const done = conversion?.status === "completed" || conversion?.status === "partial";
  const {
    data: markdown,
    isPending,
    error,
  } = useDocumentMarkdown(id, done === true);

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-4 p-4 md:p-8">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-col gap-1">
          <h1 className="truncate text-2xl font-bold">
            {conversion?.source_file ?? "معاينة المستند"}
          </h1>
          <p className="text-sm text-muted-foreground">معاينة Markdown بنمط GitHub</p>
        </div>
        <div className="flex gap-4">
          <Link className="text-sm underline" href="/">
            رجوع
          </Link>
          <a className="text-sm underline" href={outputUrl(id, "document.md")} download>
            تنزيل Markdown
          </a>
        </div>
      </header>

      {isPending && (
        <Card>
          <CardContent className="p-4 text-muted-foreground">جارٍ تحميل المعاينة...</CardContent>
        </Card>
      )}
      {(error || markdown === undefined) && !isPending && done && (
        <Card>
          <CardContent className="p-4 text-destructive">{getErrorMessage(error)}</CardContent>
        </Card>
      )}
      {!done && (
        <Card>
          <CardContent className="p-4 text-muted-foreground">
            المعاينة متاحة بعد اكتمال التحويل.
          </CardContent>
        </Card>
      )}
      {done && markdown !== undefined && !error && !markdown.trim() && (
        <Card>
          <CardContent className="p-4 text-muted-foreground">الملف فارغ.</CardContent>
        </Card>
      )}
      {done && markdown && markdown.trim() && (
        <MarkdownViewer source={markdown} conversionId={id} />
      )}
    </main>
  );
}
