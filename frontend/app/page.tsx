"use client";

import { useState } from "react";
import { BookOpenText, MousePointerClick } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ApiKeyBar } from "@/features/conversions/components/ApiKeyBar";
import { ConversionDetails, ConversionsList } from "@/features/conversions/components/ConversionsList";
import { UploadCard } from "@/features/conversions/components/UploadCard";

function EmptyDetails() {
  return (
    <Card className="min-h-[560px] rounded-2xl bg-white shadow-sm">
      <CardContent className="flex min-h-[560px] flex-col items-center justify-center gap-3 p-10 text-center">
        <div className="relative mb-2">
          <BookOpenText className="size-24 text-slate-700" strokeWidth={1.2} />
          <MousePointerClick className="absolute -bottom-2 -right-2 size-10 rounded-full bg-white text-slate-500" />
        </div>
        <p className="text-lg font-bold">اختر تحويلًا لعرض حالته</p>
        <p className="max-w-sm text-sm text-muted-foreground">
          ستظهر هنا تفاصيل الملف المحدد، شريط التقدم، وأزرار المعاينة والتنزيل.
        </p>
        <div className="mt-6 flex w-full max-w-xs flex-col gap-2">
          <div className="h-2 w-full rounded-full bg-slate-200" />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>خامل</span>
            <span>شريط التقدم</span>
          </div>
        </div>
        <div className="mt-2 flex gap-2">
          <Button disabled variant="outline" className="rounded-lg px-8">
            معاينة
          </Button>
          <Button disabled className="rounded-lg bg-slate-200 px-8 text-slate-500">
            تحميل
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function Home() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-5 p-4 md:p-8">
      <header className="flex flex-col items-center gap-1 text-center">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight md:text-3xl">محرك تحويل المستندات</h1>
          <span className="rounded-xl bg-amber-100 p-2 shadow-sm">
            <BookOpenText className="size-7 text-amber-600" />
          </span>
        </div>
        <p className="text-sm text-muted-foreground">
          ارفع كتابًا وتابع حالته لحظة بلحظة، ثم عاين المخرجات أو نزّلها.
        </p>
      </header>

      <ApiKeyBar />

      <div className="grid items-start gap-5 lg:grid-cols-3">
        <div className="flex flex-col gap-5 lg:col-span-1">
          <UploadCard />
          <ConversionsList onSelect={setSelectedId} selectedId={selectedId} />
        </div>
        <div className="lg:col-span-2">
          {selectedId ? (
            <ConversionDetails key={selectedId} id={selectedId} />
          ) : (
            <EmptyDetails />
          )}
        </div>
      </div>

      <footer className="text-center text-xs text-muted-foreground">
        التحويل يعمل على الخادم — يمكنك إغلاق الصفحة والعودة لاحقًا دون توقف.
      </footer>
    </main>
  );
}
