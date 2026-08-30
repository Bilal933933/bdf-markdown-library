"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import JSZip from "jszip";
import { saveAs } from "file-saver";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("انتظر رفع الملف...");
  const [resultFiles, setResultFiles] = useState<{ name: string; content: string }[]>([]);
  const [isComplete, setIsComplete] = useState(false);

  // منطقة السحب والإفلات
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const selected = acceptedFiles[0];
      if (selected.type === "application/pdf") {
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

  // محاكاة عملية التحويل وإنشاء ملفات Markdown
  const handleConvert = async () => {
    if (!file) {
      alert("الرجاء رفع ملف PDF أولاً.");
      return;
    }

    setIsProcessing(true);
    setIsComplete(false);
    setResultFiles([]);
    setProgress(0);

    const baseName = file.name.replace(/\.pdf$/i, "");
    const totalPages = 400;
    let currentPage = 0;

    // محاكاة التقدم
    await new Promise<void>((resolve) => {
      const interval = setInterval(() => {
        currentPage += Math.floor(Math.random() * 15) + 5;
        if (currentPage > totalPages) currentPage = totalPages;

        const percent = Math.round((currentPage / totalPages) * 100);
        setProgress(percent);
        setStatusText(`جاري معالجة الصفحة ${currentPage} من ${totalPages}...`);

        if (currentPage >= totalPages) {
          clearInterval(interval);
          resolve();
        }
      }, 200);
    });

    setStatusText("إنشاء ملفات Markdown...");

    // ملفات تجريبية (لنموذج العرض)
    const mockFiles = [
      {
        name: `${baseName}_الجزء_1.md`,
        content: `# ${baseName} - الجزء الأول\n\n## صفحة 1\nهذا نص تجريبي للصفحة الأولى.\n\n## صفحة 2\nنص تجريبي للصفحة الثانية.\n\n*تم الإنشاء بواسطة أداة التحويل التجريبية.*`,
      },
      {
        name: `${baseName}_الجزء_2.md`,
        content: `# ${baseName} - الجزء الثاني\n\n## صفحة 150\nنص الصفحة 150.\n\n## صفحة 151\nنص الصفحة 151.\n\n*محتوى وهمي للعرض.*`,
      },
      {
        name: `${baseName}_الجزء_3.md`,
        content: `# ${baseName} - الجزء الثالث\n\n## صفحة 300\nنص الصفحة 300.\n\n## صفحة 350\nنص الصفحة 350.\n\n**اكتمل التحويل بنجاح (محاكاة).**`,
      },
    ];

    setResultFiles(mockFiles);
    setProgress(100);
    setStatusText("تم التحويل بنجاح! 🎉");
    setIsComplete(true);
    setIsProcessing(false);
  };

  const downloadSingleFile = (content: string, filename: string) => {
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadAllAsZip = async () => {
    if (resultFiles.length === 0) return;
    const zip = new JSZip();
    resultFiles.forEach((f) => zip.file(f.name, f.content));
    const zipBlob = await zip.generateAsync({ type: "blob" });
    saveAs(zipBlob, `${file?.name.replace(/\.pdf$/i, "") || "book"}_markdown.zip`);
  };

  const resetAll = () => {
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
          <CardTitle className="text-3xl font-bold bg-gradient-to-l from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            📚 محوِّل الكتب إلى Markdown
          </CardTitle>
          <p className="text-muted-foreground text-sm mt-1">
            ارفع كتابك بصيغة PDF، وسنحوله إلى ملفات نصية منظمة
          </p>
        </CardHeader>

        <CardContent className="p-6 space-y-6">
          {/* منطقة الرفع */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
              isDragActive
                ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
                : "border-gray-300 dark:border-gray-700 hover:border-blue-400"
            } ${isProcessing ? "opacity-50 pointer-events-none" : ""}`}
          >
            <Input {...getInputProps()} className="hidden" />
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
                  يدعم ملفات PDF فقط
                </p>
              </div>
            )}
          </div>

          {/* شريط التقدم */}
          {file && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="font-medium">{statusText}</span>
                <span>{progress}%</span>
              </div>
              <Progress value={progress} />
            </div>
          )}

          {/* الأزرار */}
          {file && !isComplete && (
            <div className="flex gap-3">
              <Button
                onClick={handleConvert}
                disabled={isProcessing}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
              >
                {isProcessing ? "جاري التحويل..." : "🚀 بدء التحويل"}
              </Button>
              <Button variant="outline" onClick={resetAll} disabled={isProcessing}>
                إلغاء
              </Button>
            </div>
          )}

          {/* النتائج */}
          {isComplete && resultFiles.length > 0 && (
            <div className="border rounded-xl p-4 space-y-4 bg-slate-50 dark:bg-slate-900/50">
              <div className="flex justify-between items-center">
                <h3 className="font-semibold text-lg">✅ النتائج</h3>
                <Button onClick={downloadAllAsZip} variant="default" size="sm">
                  📦 تحميل الكل كـ ZIP
                </Button>
              </div>
              <div className="grid gap-2">
                {resultFiles.map((f, idx) => (
                  <div
                    key={idx}
                    className="flex justify-between items-center p-2 rounded-lg bg-white dark:bg-slate-800 shadow-sm border"
                  >
                    <span className="font-mono text-sm flex items-center gap-2">
                      <span>📄</span> {f.name}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => downloadSingleFile(f.content, f.name)}
                    >
                      ⬇️ تحميل
                    </Button>
                  </div>
                ))}
              </div>
              <Button variant="outline" onClick={resetAll} className="w-full">
                تحويل كتاب آخر
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
