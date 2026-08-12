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

  for (let page = 1; page <= pages; page++) {
    try {
      const p = await doc.getPage(page);
      const tc = await p.getTextContent();
      const text = tc.items.map((it) => it.str).join(" ");
      buffer.push({ page, text });
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
  await doc.destroy();
  log("اكتمل الاستخراج");
}

main().catch((e) => {
  console.error("فشل:", e);
  process.exit(1);
});