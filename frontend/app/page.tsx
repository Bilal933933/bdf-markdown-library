import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-3xl font-bold">محرك تحويل المستندات</h1>
      <p className="text-muted-foreground">
        ارفع كتابا (PDF/DOCX/TXT/صور) واحصل على Markdown منظم بالوحدات والدروس.
      </p>
      <Button disabled>الرفع قريبا</Button>
    </main>
  );
}
