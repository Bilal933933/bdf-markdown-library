export interface PageResult {
  pageNumber: number;
  text: string;
  failed: boolean;
}

export interface PartFile {
  /** اسم الملف، مثل part-01.md */
  fileName: string;
  content: string;
}

/**
 * يجمّع نتائج صفحات مفردة في ملفات part-XX.md، بمعدل `pagesPerPart` صفحة لكل جزء،
 * تمامًا كما يفعل gemini-ocr.mjs الأصلي، لكن في الذاكرة بدل القراءة/الكتابة
 * المتكررة على القرص لكل صفحة.
 */
export function buildParts(
  pages: PageResult[],
  bookName: string,
  totalPages: number,
  pagesPerPart: number
): PartFile[] {
  const byPart = new Map<number, PageResult[]>();

  for (const page of pages) {
    const partNum = Math.floor((page.pageNumber - 1) / pagesPerPart) + 1;
    const list = byPart.get(partNum) ?? [];
    list.push(page);
    byPart.set(partNum, list);
  }

  const parts: PartFile[] = [];
  const partNumbers = Array.from(byPart.keys()).sort((a, b) => a - b);

  for (const partNum of partNumbers) {
    const from = (partNum - 1) * pagesPerPart + 1;
    const to = Math.min(partNum * pagesPerPart, totalPages);
    const pagesInPart = (byPart.get(partNum) ?? []).sort(
      (a, b) => a.pageNumber - b.pageNumber
    );

    const lines = [
      `# ${bookName} — الجزء ${partNum} (صفحات ${from}-${to})`,
      "",
    ];

    for (const page of pagesInPart) {
      lines.push(`## صفحة ${page.pageNumber}`, "", page.text, "");
    }

    parts.push({
      fileName: `part-${String(partNum).padStart(2, "0")}.md`,
      content: lines.join("\n"),
    });
  }

  return parts;
}

/**
 * يدمج نتيجة صفحة فاشلة سابقًا (مثلاً من محاولة إعادة معالجة) مع الأجزاء
 * الحالية، ويفضّل دائمًا النص الناجح على نص الفشل عند التعارض.
 */
export function mergePageResult(
  existing: PageResult | undefined,
  incoming: PageResult
): PageResult {
  if (!existing) return incoming;
  if (existing.failed && !incoming.failed) return incoming;
  if (!existing.failed && incoming.failed) return existing;
  // كلاهما ناجح أو كلاهما فاشل: نفضّل النص الأطول (أرجح أن يكون أدق)
  return incoming.text.length > existing.text.length ? incoming : existing;
}
