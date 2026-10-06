import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import path from "path";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";

const BOOK_NAME = process.argv[2] || "Arabic_prim6_TR2";
const FILE = process.argv[3] || "C:/Users/blals/Downloads/Arabic_prim6_TR2.pdf";
const TOTAL = parseInt(process.argv[4] || "0", 10);

const WORK = import.meta.dirname;
const BOOK_DIR = path.join(path.dirname(WORK), BOOK_NAME);
const CHUNK = 40;

function log(msg) {
  console.log(`[${new Date().toISOString()}] ${msg}`);
}

// بوابة جودة الطبقة النصية — تطابق backend/quality/analyzer.py وعتبات AGENTS.md §3ب-ب.
// الهدف: رفض النص الطويل المشوه (ToUnicode مكسور) مبكرًا ليعالجه مسار الصور.
// الصفحات القصيرة (<80) تُترك كما هي — fix-pages يميز الفني من المحطم لاحقًا.
const CONTROL_RE = /[\u0000-\u001F\u007F-\u009F]/g;
const STRIP_RE = /[\u0000-\u001F\u007F-\u009F\u200B-\u200F\u202A-\u202E\uFEFF]/g;

function isArabicChar(ch) {
  const c = ch.codePointAt(0);
  return (c >= 0x0600 && c <= 0x06ff) || (c >= 0x0750 && c <= 0x077f) || (c >= 0xfb50 && c <= 0xfdff) || (c >= 0xfe70 && c <= 0xfeff);
}

function judgeTextLayer(text) {
  const controls = (text.match(CONTROL_RE) || []).length;
  const useful = text.replace(STRIP_RE, "").replace(/\s+/g, "").length;
  // قصيرة: ليست حكمًا — تُقبل هنا ويفصل فيها fix-pages (فني أم محطم).
  if (useful < 80) return { verdict: "short", useful, controls, reasons: [] };
  const reasons = [];
  // فئة D: أحرف تحكم كثيرة.
  if (controls / (useful + 1) > 0.3) reasons.push("control_chars");
  // نسبة عربية منخفضة رغم طول النص — علامة ترميز مكسور.
  const letters = [...text].filter((ch) => /[A-Za-z\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]/.test(ch));
  if (letters.length >= 20) {
    const ratio = letters.filter(isArabicChar).length / letters.length;
    if (ratio < 0.5) reasons.push("low_arabic_ratio");
  }
  // تفتت: كلمات من حرف أو حرفين — ناتج CMap مكسور.
  const lexemes = text.split(/\s+/).map((w) => w.replace(/[ً-ٰٟ]/g, "").replace(/[^A-Za-z\u0600-\u06FF]/g, "")).filter(Boolean);
  if (lexemes.length >= 10) {
    const frag = lexemes.filter((w) => w.length <= 2).length / lexemes.length;
    if (frag > 0.5) reasons.push("fragmented_text");
  }
  // خلط حروف+أرقام داخل نفس الكلمة (حُظَر٤ش) — ToUnicode مكسور.
  // السليم أرقامه مستقلة (mixRatio=0.00) والمشوه 0.28-0.45 — العتبة 0.10 آمنة.
  const lex = text.split(/\s+/).map((w) => w.replace(/[ً-ٰٟ]/g, "")).filter((w) => /[A-Za-z\u0600-\u06FF]/.test(w));
  if (lex.length >= 10) {
    const mixed = lex.filter((w) => /[0-9\u0660-\u0669]/.test(w)).length / lex.length;
    if (mixed > 0.1) reasons.push("mixed_alnum");
  }
  if (reasons.length > 0) return { verdict: "distorted", useful, controls, reasons };
  return { verdict: "accept", useful, controls, reasons: [] };
}

function writePart(partIndex, buffer) {
  const idx = String(partIndex).padStart(2, "0");
  const nums = buffer.map((p) => p.page);
  const header = `# ${BOOK_NAME} — الجزء ${partIndex} (صفحات ${Math.min(...nums)}-${Math.max(...nums)})\n\n`;
  const body = buffer.map((p) => `## صفحة ${p.page}\n\n${p.text.trim()}`).join("\n\n");
  writeFileSync(path.join(BOOK_DIR, `part-${idx}.md`), header + body + "\n");
  log(`كتب part-${idx}.md (${buffer.length} صفحة)`);
}

async function main() {
  mkdirSync(BOOK_DIR, { recursive: true });
  const buf = readFileSync(FILE);
  const data = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const doc = await pdfjsLib.getDocument({ data }).promise;
  const pages = TOTAL || doc.numPages;
  log(`البدء: ${pages} صفحة`);

  let partIndex = 1;
  let buffer = [];
  let distorted = 0;

  for (let page = 1; page <= pages; page++) {
    try {
      const p = await doc.getPage(page);
      const tc = await p.getTextContent();
      const text = tc.items.map((it) => it.str).join(" ");
      const j = judgeTextLayer(text);
      if (j.verdict === "distorted") {
        distorted++;
        log(`صفحة ${page}: طبقة مشوهة (${j.reasons.join(",")}) → علامة OCR`);
        buffer.push({ page, text: `[تعذر استخراج النص من الصفحة ${page} — طبقة نصية مشوهة]` });
      } else {
        buffer.push({ page, text });
      }
    } catch (e) {
      log(`خطأ في الصفحة ${page}: ${e.message}`);
      buffer.push({ page, text: `[تعذر استخراج النص من الصفحة ${page}]` });
    }

    if (buffer.length >= CHUNK) {
      writePart(partIndex, buffer);
      buffer = [];
      partIndex += 1;
    }
    if (page % 25 === 0 || page === pages) log(`تقدم: ${page}/${pages}`);
  }
  if (buffer.length) writePart(partIndex, buffer);
  await doc.destroy?.();
  log(`اكتمل الاستخراج — صفحات مشوهة حُوّلت لـOCR: ${distorted}`);
}

main().catch((e) => {
  console.error("فشل:", e);
  process.exit(1);
});