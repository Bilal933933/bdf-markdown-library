import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import path from "path";
import { execFileSync } from "child_process";
import sharp from "sharp";
import { createCanvas } from "@napi-rs/canvas";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";

const BOOK_NAME = process.argv[2] || "Arabic_prim6_TR2";
const FILE = process.argv[3] || "C:/Users/blals/Downloads/Arabic_prim6_TR2.pdf";
const TOTAL = parseInt(process.argv[4] || "144", 10);

const WORK = import.meta.dirname;
const TESSERACT = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe";
const TESSDATA = path.join(WORK, "tessdata");
const BOOK_DIR = path.join(path.dirname(WORK), BOOK_NAME);
const WASM_URL = path.join(WORK, "node_modules", "pdfjs-dist", "wasm").replace(/\\/g, "/") + "/";
const CHUNK = 40;

const CONTROL_RE = /[\u0000-\u001F\u007F-\u009F]/;

function log(msg) {
  console.log(`[${new Date().toISOString()}] ${msg}`);
}

function parseExisting(parts) {
  const map = new Map();
  for (const part of parts) {
    const re = /## صفحة (\d+)\n\n([\s\S]*?)(?=\n## صفحة \d+|\n$|$)/g;
    let m;
    while ((m = re.exec(part)) !== null) {
      map.set(parseInt(m[1], 10), m[2]);
    }
  }
  return map;
}

async function ocrPage(doc, pageNum) {
  const page = await doc.getPage(pageNum);
  const base = page.getViewport({ scale: 1 });
  const scale = 2500 / base.width;
  const vp = page.getViewport({ scale });
  const canvas = createCanvas(Math.ceil(vp.width), Math.ceil(vp.height));
  const ctx = canvas.getContext("2d");
  await page.render({ canvasContext: ctx, viewport: vp }).promise;
  const png = canvas.toBuffer("image/png");
  page.cleanup();
  const clean = await sharp(png).grayscale().normalize().sharpen().png().toBuffer();
  const tmpCl = path.join(WORK, "tmp-fix-clean.png");
  const tmpOut = path.join(WORK, "tmp-fix-out");
  writeFileSync(tmpCl, clean);
  execFileSync(TESSERACT, [tmpCl, tmpOut, "-l", "ara_best", "--psm", "6"], {
    env: { ...process.env, TESSDATA_PREFIX: TESSDATA },
  });
  return readFileSync(tmpOut + ".txt", "utf8").trim();
}

async function main() {
  const parts = [];
  for (let i = 1; existsSync(path.join(BOOK_DIR, `part-${String(i).padStart(2, "0")}.md`)); i++) {
    parts.push(readFileSync(path.join(BOOK_DIR, `part-${String(i).padStart(2, "0")}.md`), "utf8"));
  }
  const pagesMap = parseExisting(parts);

  const buf = readFileSync(FILE);
  const data = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const doc = await pdfjsLib.getDocument({ data, wasmUrl: WASM_URL }).promise;

  const usefulLen = (t) =>
    t
      .replace(/[\u0000-\u001F\u007F-\u009F\u200B-\u200F\u202A-\u202E\uFEFF]/g, "")
      .replace(/\s+/g, "").length;

  let fixed = 0;
  for (let p = 1; p <= TOTAL; p++) {
    const curText = pagesMap.get(p) || "";
    if (CONTROL_RE.test(curText)) {
      const cleanText = curText.replace(/[\u0000-\u001F\u007F-\u009F]/g, "");
      pagesMap.set(p, cleanText);
    }
    if (usefulLen(pagesMap.get(p) || "") < 80 || p === 1) {
      try {
        const ocr = await ocrPage(doc, p);
        pagesMap.set(p, ocr);
        fixed++;
        log(`صفحة ${p}: نصها مفيد <80 → أُعيدت بالـOCR (${ocr.length} حرف)`);
      } catch (e) {
        log(`فشل OCR للصفحة ${p}: ${e.message}`);
      }
    }
  }
  await doc.destroy();
  log(`تم تصحيح ${fixed} صفحة بالـOCR وتنظيف الباقي من أحرف التحكم`);

  // إعادة بناء الملفات
  const nums = [...pagesMap.keys()].sort((a, b) => a - b);
  let partIndex = 1;
  for (let i = 0; i < nums.length; i += CHUNK) {
    const chunk = nums.slice(i, i + CHUNK);
    const idx = String(partIndex).padStart(2, "0");
    const header = `# ${BOOK_NAME} — الجزء ${partIndex} (صفحات ${chunk[0]}-${chunk[chunk.length - 1]})\n\n`;
    const body = chunk.map((p) => `## صفحة ${p}\n\n${pagesMap.get(p).trim()}`).join("\n\n");
    writeFileSync(path.join(BOOK_DIR, `part-${idx}.md`), header + body + "\n");
    partIndex += 1;
  }
  log("أُعيد بناء الملفات");
}

main().catch((e) => {
  console.error("فشل:", e);
  process.exit(1);
});