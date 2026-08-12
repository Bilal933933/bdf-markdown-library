import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import path from "path";
import { execFileSync } from "child_process";
import sharp from "sharp";
import { createCanvas } from "@napi-rs/canvas";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";

const BOOK_NAME = process.argv[2] || "كيف تتقن البلاغة";
const FILE = process.argv[3] || "D:/مسابقة معلم مادة/كيف_تتقن_البلاغة.pdf";
const TOTAL = parseInt(process.argv[4] || "528", 10);

const WORK = import.meta.dirname;
const TESSERACT = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe";
const TESSDATA = path.join(WORK, "tessdata");
const BOOK_DIR = path.join(path.dirname(WORK), BOOK_NAME);
const PROGRESS = path.join(WORK, `ocr-progress-jpx-${BOOK_NAME}.json`);
const CHUNK = 40;
const DESIRED_WIDTH = 2480;
const WASM_URL = path.join(WORK, "node_modules", "pdfjs-dist", "wasm").replace(/\\/g, "/") + "/";

function log(msg) {
  console.log(`[${new Date().toISOString()}] ${msg}`);
}

function getStartState() {
  if (existsSync(PROGRESS)) {
    const s = JSON.parse(readFileSync(PROGRESS, "utf8"));
    log(`استئناف من الصفحة ${s.lastPage} (الملف التالي part-${String(s.partIndex).padStart(2, "0")})`);
    return s;
  }
  return { lastPage: 0, partIndex: 1, buffer: [] };
}

function saveState(state) {
  writeFileSync(PROGRESS, JSON.stringify(state));
}

function pageRange(buffer) {
  const nums = buffer.map((p) => p.page);
  return `${Math.min(...nums)}-${Math.max(...nums)}`;
}

function writePart(state) {
  const idx = String(state.partIndex).padStart(2, "0");
  const range = pageRange(state.buffer);
  const header = `# ${BOOK_NAME} — الجزء ${state.partIndex} (صفحات ${range})\n\n`;
  const body = state.buffer.map((p) => `## صفحة ${p.page}\n\n${p.text.trim()}`).join("\n\n");
  const file = path.join(BOOK_DIR, `part-${idx}.md`);
  writeFileSync(file, header + body + "\n");
  log(`كتب ${file} (${state.buffer.length} صفحة: ${range})`);
  state.buffer = [];
  state.partIndex += 1;
}

async function renderPage(doc, pageNum) {
  const page = await doc.getPage(pageNum);
  const base = page.getViewport({ scale: 1 });
  const scale = DESIRED_WIDTH / base.width;
  const viewport = page.getViewport({ scale });
  const canvas = createCanvas(Math.ceil(viewport.width), Math.ceil(viewport.height));
  const ctx = canvas.getContext("2d");
  await page.render({ canvasContext: ctx, viewport }).promise;
  const png = canvas.toBuffer("image/png");
  page.cleanup();
  return png;
}

async function preprocess(buffer) {
  return sharp(buffer).grayscale().normalize().sharpen().png().toBuffer();
}

async function main() {
  mkdirSync(BOOK_DIR, { recursive: true });
  const buf = readFileSync(FILE);
  const data = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const doc = await pdfjsLib.getDocument({ data, wasmUrl: WASM_URL }).promise;
  const state = getStartState();
  const tmpClean = path.join(WORK, "tmp-jpx-clean.png");
  const tmpOut = path.join(WORK, "tmp-jpx");

  for (let page = state.lastPage + 1; page <= TOTAL; page++) {
    try {
      const raw = await renderPage(doc, page);
      writeFileSync(tmpClean, await preprocess(raw));
      execFileSync(
        TESSERACT,
        [tmpClean, tmpOut, "-l", "ara_best", "--psm", "6"],
        { env: { ...process.env, TESSDATA_PREFIX: TESSDATA } }
      );
      const text = readFileSync(tmpOut + ".txt", "utf8");
      state.buffer.push({ page, text });
    } catch (e) {
      log(`خطأ في الصفحة ${page}: ${e.message}`);
      state.buffer.push({ page, text: `[تعذر استخراج النص من الصفحة ${page}]` });
    }

    if (state.buffer.length >= CHUNK) writePart(state);
    state.lastPage = page;
    saveState(state);
    if (page % 25 === 0 || page === TOTAL) log(`تقدم: ${page}/${TOTAL}`);
  }
  if (state.buffer.length) writePart(state);
  await doc.destroy();
  saveState(state);
  log("اكتمل استخراج جميع الصفحات");
}

main().catch((e) => {
  console.error("فشل:", e);
  process.exit(1);
});