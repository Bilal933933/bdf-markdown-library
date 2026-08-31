"use client";

import { useState, useCallback, useRef } from "react";
import { useDropzone } from "react-dropzone";
import JSZip from "jszip";
import { saveAs } from "file-saver";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

interface PollResult {
  status: "processing" | "completed" | "failed";
  progress: number;
  result?: {
    bookName: string;
    totalPages: number;
    files: { fileName: string; content: string }[];
  };
  error?: string;
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("انتظر رفع الملف...");
  const [resultFiles, setResultFiles] = useState<{ fileName: string; content: string }[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const selected = acceptedFiles[0];
      if (selected.type === "application/pdf") {
        if (intervalRef.current) clearInterval(intervalRef.current);
        setFile(selected);
        setResultFiles([]);
        setIsComplete(false);
        setProgress(0);
        setStatusText(`تم رفع: ${selected.name}`);
      } else {
        alert("يرجى رفع ملف PDF فقط.");
      }
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    disabled: isProcessing,
  });

  // دالة مساعدة لفك شكل الاستجابة الموحد { success, data/error }
  function unwrap<T>(json: any): T {
    if (!json.success) throw new Error(json.error?.message || "خطأ غير معروف");
    return json.data as T;
  }

  const handleConvert = async () => {
    if (!file) return;

    setIsProcessing(true);
    setIsComplete(false);
    setResultFiles([]);
    setProgress(0);
    setStatusText("جاري رفع الملف...");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("/api/convert", { method: "POST", body: formData });
      const json = await res.json();
      const data = unwrap<{ taskId: string }>(json);

      const taskId: string = data.taskId;
      setStatusText("تم الرفع، بدأت المعالجة في الخلفية...");

      intervalRef.current = setInterval(async () => {
        try {
          const pollRes = await fetch(`/api/status/${taskId}`);
          const pollJson = await pollRes.json();
          const pollData: PollResult = unwrap<PollResult>(pollJson);

          setProgress(pollData.progress);
          if (pollData.status === "processing") {
            setStatusText(`جاري المعالجة: ${pollData.progress}%`);
          } else if (pollData.status === "completed") {
            if (intervalRef.current) clearInterval(intervalRef.current);
            setResultFiles(pollData.result?.files ?? []);
            setProgress(100);
            setStatusText("✅ اكتمل التحويل بنجاح!");
            setIsComplete(true);
            setIsProcessing(false);
          } else if (pollData.status === "failed") {
            if (intervalRef.current) clearInterval(intervalRef.current);
            setStatusText(`❌ فشل: ${pollData.error}`);
            setIsProcessing(false);
          }
        } catch (e) {
          console.error("poll error", e);
        }
      }, 2500);
    } catch (err: any) {
      setStatusText(`❌ ${err.message || "خطأ غير متوقع"}`);
      setIsProcessing(false);
    }
  };

  const downloadSingle = (content: string, filename: string) => {
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    saveAs(blob, filename);
  };

  const downloadAllAsZip = async () => {
    if (resultFiles.length === 0) return;
    const zip = new JSZip();
    resultFiles.forEach((f) => zip.file(f.fileName, f.content));
    const blob = await zip.generateAsync({ type: "blob", compression: "DEFLATE", compressionOptions: { level: 6 } });
    saveAs(blob, `${file?.name.replace(/\.pdf$/i, "") || "book"}_markdown.zip`);
  };

  const resetAll = () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    setFile(null);
    setResultFiles([]);
    setProgress(0);
    setStatusText("انتظر رفع الملف...");
    setIsComplete(false);
    setIsProcessing(false);
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 p-4 md:p-8 flex items-center justify-center">
      <Card className="w-full max-w-3xl shadow-xl border-0">
        <CardHeader className="text-center border-b pb-4">
          <CardTitle className="text-3xl font-bold bg-gradient-to-l from-purple-600 to-indigo-600 bg-clip-text text-transparent">
            🤖 محوِّل الكتب بالذكاء الاصطناعي
          </CardTitle>
          <p className="text-muted-foreground text-sm mt-1">ارفع PDF وسيُحوّل عبر Gemini Vision ثم يُقسّم إلى part-XX.md</p>
        </CardHeader>

        <CardContent className="p-6 space-y-6">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
              isDragActive ? "border-purple-500 bg-purple-50 dark:bg-purple-950/30" : "border-gray-300 dark:border-gray-700 hover:border-purple-400"
            } ${isProcessing ? "opacity-50 pointer-events-none" : ""}`}
          >
            <input {...getInputProps()} />
            {file ? (
              <div className="flex flex-col items-center gap-2">
                <span className="text-2xl">📄</span>
                <p className="font-medium">{file.name}</p>
                <Badge variant="outline" className="text-xs">{(file.size / (1024 * 1024)).toFixed(2)} MB</Badge>
                <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); resetAll(); }} className="text-red-500">إزالة الملف</Button>
              </div>
            ) : (
              <div>
                <span className="text-5xl block mb-3">📤</span>
                <p className="text-lg font-medium">{isDragActive ? "أفلت الملف هنا" : "اسحب ملف PDF هنا أو اضغط للرفع"}</p>
                <p className="text-sm text-muted-foreground mt-1">يدعم كتب النحو والصرف والبلاغة</p>
              </div>
            )}
          </div>

          {file && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="font-medium">{statusText}</span>
                <span>{progress}%</span>
              </div>
              <Progress value={progress} />
              <p className="text-xs text-muted-foreground">يتم الاستطلاع كل 2.5 ثانية عبر /api/status — لا تغلق الصفحة أثناء المعالجة</p>
            </div>
          )}

          {file && !isComplete && (
            <div className="flex gap-3">
              <Button onClick={handleConvert} disabled={isProcessing} className="flex-1 bg-purple-600 hover:bg-purple-700 text-white">
                {isProcessing ? "جاري المعالجة..." : "🚀 بدء التحويل"}
              </Button>
              <Button variant="outline" onClick={resetAll} disabled={isProcessing}>إلغاء</Button>
            </div>
          )}

          {isComplete && resultFiles.length > 0 && (
            <div className="border rounded-xl p-4 space-y-4 bg-slate-50 dark:bg-slate-900/50">
              <div className="flex justify-between items-center">
                <h3 className="font-semibold">✅ النتائج ({resultFiles.length} أجزاء)</h3>
                <Button onClick={downloadAllAsZip} size="sm">📦 تحميل الكل ZIP</Button>
              </div>
              <div className="grid gap-2 max-h-64 overflow-y-auto">
                {resultFiles.map((f) => (
                  <div key={f.fileName} className="flex justify-between items-center p-2 rounded-lg bg-white dark:bg-slate-800 shadow-sm border">
                    <span className="font-mono text-sm">📄 {f.fileName}</span>
                    <Button variant="outline" size="sm" onClick={() => downloadSingle(f.content, f.fileName)}>⬇️ تحميل</Button>
                  </div>
                ))}
              </div>
              <Button variant="outline" onClick={resetAll} className="w-full">تحويل كتاب آخر</Button>
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
