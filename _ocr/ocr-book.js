const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { PDFParse } = require("pdf-parse");
const sharp = require("sharp");

const BOOK_NAME = process.argv[2] || "كيف تتقن النحو";
const FILE = process.argv[3] || "D:\\مسابقة معلم مادة\\كيف تتقن النحو.pdf";
const TOTAL = parseInt(process.argv[4] || "553", 10);
const BOOK_DIR = path.join(path.dirname(__dirname), BOOK_NAME);
const WORK = __dirname;
const TESSERACT = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe";
const TESSDATA = path.join(WORK, "tessdata");
const PROGRESS = path.join(WORK, `ocr-progress-${BOOK_NAME}.json`);
const CHUNK = 40;

function log(msg) {
  console.log(`[${new Date().toISOString()}] ${msg}`);
}

function getStartState() {
  if (fs.existsSync(PROGRESS)) {
    const s = JSON.parse(fs.readFileSync(PROGRESS, "utf8"));
    log(`استئناف من الصفحة ${s.lastPage} (الملف التالي part-${String(s.partIndex).padStart(2, "0")})`);
    return s;
  }
  return { lastPage: 0, partIndex: 1, buffer: [] };
}

function saveState(state) {
  fs.writeFileSync(PROGRESS, JSON.stringify(state));
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
  fs.writeFileSync(file, header + body + "\n");
  log(`كتب ${file} (${state.buffer.length} صفحة: ${range})`);
  state.buffer = [];
  state.partIndex += 1;
}

async function preprocess(buffer) {
  return sharp(buffer).grayscale().normalize().sharpen().png().toBuffer();
}

async function main() {
  fs.mkdirSync(BOOK_DIR, { recursive: true });
  const data = fs.readFileSync(FILE);
  const parser = new PDFParse({ data });
  const state = getStartState();
  const tmpPng = path.join(WORK, "tmp-page.png");
  const tmpClean = path.join(WORK, "tmp-page-clean.png");
  const tmpOut = path.join(WORK, "tmp-page");

  for (let page = state.lastPage + 1; page <= TOTAL; page++) {
    try {
      const shot = await parser.getScreenshot({
        partial: [page],
        desiredWidth: 2480,
        imageBuffer: true,
      });
      const entry = shot.pages.find((p) => p.pageNumber === page) || shot.pages[0];
      if (!entry) throw new Error("لا توجد صورة للصفحة");
      fs.writeFileSync(tmpPng, Buffer.from(entry.data));
      fs.writeFileSync(tmpClean, await preprocess(Buffer.from(entry.data)));
      execFileSync(
        TESSERACT,
        [tmpClean, tmpOut, "-l", "ara_best", "--psm", "6"],
        { env: { ...process.env, TESSDATA_PREFIX: TESSDATA } }
      );
      const text = fs.readFileSync(tmpOut + ".txt", "utf8");
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
  saveState(state);
  log("اكتمل استخراج جميع الصفحات");
}

main().catch((e) => {
  console.error("فشل:", e);
  process.exit(1);
});