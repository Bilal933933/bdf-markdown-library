"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { startConversion, getConversionStatus } from "@/services/conversionService";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("انتظر رفع الملف...");
  const [downloadLink, setDownloadLink] = useState<string | null>(null);
  const [fileNameResult, setFileNameResult] = useState<string>("");
  const [isComplete, setIsComplete] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const selected = acceptedFiles[0];
      if (selected.type === "application/pdf") {
        setFile(selected);
        setDownloadLink(null);
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

  const handleConvert = async () => {
    if (!file) return;

    setIsProcessing(true);
    setIsComplete(false);
    setProgress(0);
    setStatusText("جاري رفع الملف إلى خادم الذكاء الاصطناعي...");

    try {
      const taskId = await startConversion(file);
      setStatusText("تم الرفع، بدء معالجة Gemini Vision OCR...");

      const interval = setInterval(async () => {
        try {
          const status = await getConversionStatus(taskId);
          setProgress(status.progress);
          setStatusText(`جاري استخراج وتحويل الكتاب: ${status.progress}%`);

          if (status.status === 'completed') {
            clearInterval(interval);
            setIsComplete(true);
            setIsProcessing(false);
            setStatusText('✅ اكتمل تحويل الكتاب بالذكاء الاصطناعي بنجاح! 🎉');
            if (status.result) {
              const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';
              setDownloadLink(`${backendUrl}${status.result.downloadUrl}`);
              setFileNameResult(status.result.fileName);
            }
          }

          if (status.status === 'failed') {
            clearInterval(interval);
            setIsProcessing(false);
            setStatusText(`❌ فشل التحويل: ${status.error || 'خطأ غير معروف'}`);
          }
        } catch (pollErr) {
          console.error("Polling error:", pollErr);
        }
      }, 3000);

    } catch (error: any) {
      console.error(error);
      setStatusText(`❌ حدث خطأ: ${error.message || 'تعذر الاتصال بالخادم'}`);
      setIsProcessing(false);
    }
  };

  const resetAll = () => {
    setFile(null);
    setDownloadLink(null);
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
            🤖 محوِّل الكتب بالذكاء الاصطناعي (Gemini Vision)
          </CardTitle>
          <p className="text-muted-foreground text-sm mt-1">
            ارفع كتابك PDF، وسيقوم النظام باستخراج النصوص بدقة متناهية عبر نموذج رؤية Gemini
          </p>
        </CardHeader>

        <CardContent className="p-6 space-y-6">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
              isDragActive
                ? "border-purple-500 bg-purple-50 dark:bg-purple-950/30"
                : "border-gray-300 dark:border-gray-700 hover:border-purple-400"
            } ${isProcessing ? "opacity-50 pointer-events-none" : ""}`}
          >
            <input {...getInputProps()} />
            {file ? (
              <div className="flex flex-col items-center gap-2">
                <span className="text-2xl">📄</span>
                <p className="font-medium">{file.name}</p>
                <Badge variant="outline" className="text-xs">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB
                </Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    resetAll();
                  }}
                  className="text-red-500"
                >
                  إزالة الملف
                </Button>
              </div>
            ) : (
              <div>
                <span className="text-5xl block mb-3">📤</span>
                <p className="text-lg font-medium">
                  {isDragActive ? "أفلت الملف هنا" : "اسحب ملف PDF هنا أو اضغط للرفع"}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  يدعم كتب النحو، الصرف، البلاغة والمراجع العربية
                </p>
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
            </div>
          )}

          {file && !isComplete && (
            <div className="flex gap-3">
              <Button
                onClick={handleConvert}
                disabled={isProcessing}
                className="flex-1 bg-purple-600 hover:bg-purple-700 text-white"
              >
                {isProcessing ? "جاري المعالجة بالذكاء الاصطناعي..." : "🚀 بدء التحويل الفعلي"}
              </Button>
              <Button variant="outline" onClick={resetAll} disabled={isProcessing}>
                إلغاء
              </Button>
            </div>
          )}

          {isComplete && downloadLink && (
            <div className="border rounded-xl p-6 space-y-4 bg-slate-50 dark:bg-slate-900/50 text-center">
              <h3 className="font-semibold text-lg text-emerald-600">✅ تم تحويل الكتاب واستخراج الأجزاء بنجاح!</h3>
              <p className="text-sm text-muted-foreground">تم توليد ملفات Markdown مشكّلة ونظيفة بالكامل.</p>
              <div className="pt-2">
                <a href={downloadLink} download={fileNameResult} target="_blank" rel="noopener noreferrer">
                  <Button className="bg-emerald-600 hover:bg-emerald-700 text-white w-full py-6 text-base shadow-lg">
                    📦 تحميل ملفات Markdown (ZIP)
                  </Button>
                </a>
              </div>
              <Button variant="outline" onClick={resetAll} className="w-full mt-2">
                تحويل كتاب آخر
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
