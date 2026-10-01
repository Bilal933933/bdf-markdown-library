"use client";

import { useRef, useState } from "react";
import { CloudUpload, FileText, Loader2, Upload, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useUploadConversion } from "../hooks/useConversions";

const ACCEPTED = ".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp";

export function UploadCard() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState("");
  const upload = useUploadConversion();

  const submit = () => {
    const file = fileRef.current?.files?.[0];
    if (file) upload.mutate(file);
  };

  const clear = () => {
    if (fileRef.current) fileRef.current.value = "";
    setFileName("");
  };

  return (
    <Card className="rounded-2xl bg-white shadow-sm">
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <CardTitle className="flex items-center gap-2 text-lg">
            رفع كتاب جديد
            <Upload className="size-5 text-muted-foreground" />
          </CardTitle>
          <CardDescription>تنسيقات المدخلات: PDF ,DOCX ,TXT ,صور</CardDescription>
        </div>
        <CloudUpload className="size-10 shrink-0 text-muted-foreground" strokeWidth={1.5} />
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Input
          ref={fileRef}
          type="file"
          accept={ACCEPTED}
          onChange={(event) => setFileName(event.target.files?.[0]?.name ?? "")}
          className="h-11 cursor-pointer rounded-xl border-dashed bg-[#fafbfc] text-center"
        />
        {fileName && (
          <div className="flex items-center gap-2 rounded-lg bg-muted/60 px-3 py-2 text-sm">
            <FileText className="size-4 shrink-0 text-muted-foreground" />
            <span className="min-w-0 flex-1 truncate">{fileName}</span>
            <button
              onClick={clear}
              aria-label="إزالة الملف"
              className="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <X className="size-4" />
            </button>
          </div>
        )}
        <Button
          onClick={submit}
          disabled={!fileName || upload.isPending}
          className="h-10 w-full rounded-xl bg-[#1e4da1] text-white hover:bg-[#163a7d]"
        >
          {upload.isPending && <Loader2 className="size-4 animate-spin" />}
          {upload.isPending ? "جارٍ الرفع..." : "رفع وتحويل"}
        </Button>
      </CardContent>
    </Card>
  );
}
