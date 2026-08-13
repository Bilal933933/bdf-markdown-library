import { readFileSync, writeFileSync, mkdirSync, readdirSync } from "fs";

const [srcDir, outDir, totalPagesStr] = process.argv.slice(2);
const totalPages = totalPagesStr ? parseInt(totalPagesStr) : 553;
const SRC = srcDir || "E:/AI-Content/_ocr/marker_out/nahw_full";
const OUT = outDir || "E:/AI-Content/_ocr/marker_out/nahw_rebuilt";

mkdirSync(OUT, { recursive: true });

const files = readdirSync(SRC).filter((f) => /^part-\d+\.md$/.test(f)).sort();
const all = {};

for (const f of files) {
  const txt = readFileSync(`${SRC}/${f}`, "utf8");
  const pages = txt.split(/^## صفحة /m).slice(1);
  for (const p of pages) {
    const num = parseInt(p.match(/^(\d+)/)?.[1]);
    if (!num) continue;
    const body = p.replace(/^\d+\s*\n?/, "").trim();
    if (!body) continue;
    const failed = body.startsWith("[تعذر");
    const useful = body.replace(/[\x00-\x1F\x7F-\x9F\u200B-\u200F\u202A-\u202E\uFEFF]/g, "").replace(/\s+/g, "").length;
    // نفضّل النسخة الناجحة على الفاشلة، والأطول على الأقصر
    const isGood = !failed && useful >= 20;
    const prev = all[num];
    if (!prev) {
      if (isGood) all[num] = { body, good: true };
    } else if (!prev.good && isGood) {
      all[num] = { body, good: true };
    }
  }
}

const nums = Object.keys(all).map(Number).sort((a, b) => a - b);
const missing = [];
for (let i = 1; i <= totalPages; i++) if (!all[i]) missing.push(i);

// بناء ملفات الأجزاء حسب رقم الصفحة
const numParts = Math.ceil(totalPages / 40);
let built = 0;
for (let part = 1; part <= numParts; part++) {
  const from = (part - 1) * 40 + 1;
  const to = Math.min(part * 40, totalPages);
  const lines = [`# جزء ${part} (صفحات ${from}-${to})`, ""];
  let any = false;
  for (let p = from; p <= to; p++) {
    const rec = all[p];
    if (!rec) continue;
    any = true;
    lines.push(`## صفحة ${p}`, "", rec.body, "");
  }
  if (!any) continue;
  writeFileSync(`${OUT}/part-${String(part).padStart(2, "0")}.md`, lines.join("\n"), "utf8");
  built++;
}

console.log(`صفحات فريدة موجودة: ${nums.length}`);
console.log(`مفقودة: ${missing.length}: ${missing.join(",")}`);
console.log(`أجزاء مبنية: ${built}`);
console.log(`الناتج في ${OUT}`);
