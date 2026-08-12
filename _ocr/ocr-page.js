const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { PDFParse } = require("pdf-parse");
const sharp = require("sharp");

const FILE = "D:\\مسابقة معلم مادة\\كيف تتقن النحو.pdf";
const WORK = __dirname;
const TESSERACT = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe";
const TESSDATA = path.join(WORK, "tessdata");

const PAGE = parseInt(process.argv[2] || "401", 10);
const PSM = process.argv[3] || "6";

async function preprocess(buffer) {
  return sharp(buffer).grayscale().normalize().sharpen().png().toBuffer();
}

async function main() {
  const data = fs.readFileSync(FILE);
  const parser = new PDFParse({ data });
  const shot = await parser.getScreenshot({
    partial: [PAGE],
    desiredWidth: 2480,
    imageBuffer: true,
  });
  const page = shot.pages.find((p) => p.pageNumber === PAGE) ?? shot.pages[0];
  if (!page) throw new Error("لا توجد صورة للصفحة");

  const rawPng = path.join(WORK, `p${PAGE}-raw.png`);
  const cleanPng = path.join(WORK, `p${PAGE}-clean.png`);
  const cleanBuf = await preprocess(Buffer.from(page.data));
  fs.writeFileSync(rawPng, Buffer.from(page.data));
  fs.writeFileSync(cleanPng, cleanBuf);

  const started = Date.now();
  execFileSync(TESSERACT, [cleanPng, path.join(WORK, `p${PAGE}`), "-l", "ara_best", "--psm", PSM], {
    env: { ...process.env, TESSDATA_PREFIX: TESSDATA },
  });
  const text = fs.readFileSync(path.join(WORK, `p${PAGE}.txt`), "utf8");
  console.log(`الصفحة ${PAGE} — ${text.length} حرف — ${((Date.now() - started) / 1000).toFixed(1)} ثانية (psm ${PSM})`);
  console.log("----------------------------------------");
  console.log(text.trim());
}

main().catch((e) => {
  console.error("فشل:", e.message);
  process.exit(1);
});