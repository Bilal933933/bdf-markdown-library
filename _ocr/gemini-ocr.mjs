import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import sharp from "sharp";

const WASM_URL = new URL("pdfjs-dist/wasm/", import.meta.url).href;

const args = process.argv.slice(2);
const [pdfPath, outDir, startStr, endStr] = args;
const API_KEY = process.env.GEMINI_API_KEY || "AIzaSyBZuaIlJbGexbrybmS-BziHUHrLnaY3Wbc";
const MODEL = process.env.GEMINI_MODEL || "gemini-3-flash-preview";
const FALLBACK_MODELS = (process.env.GEMINI_FALLBACK || "gemini-3.1-flash-lite,gemini-3.1-flash-lite-preview,gemini-3.5-flash-lite,gemini-flash-latest,gemini-3.6-flash")
  .split(",")
  .map((s) => s.trim());

if (!pdfPath || !outDir) {
  console.error("الاستخدام: node gemini-ocr.mjs <pdf> <outDir> [startPage] [endPage]");
  process.exit(1);
}
mkdirSync(outDir, { recursive: true });

const buf = readFileSync(pdfPath);
const data = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
const doc = await pdfjsLib.getDocument({ data, wasmUrl: WASM_URL }).promise;
const numPages = doc.numPages;
const start = startStr ? parseInt(startStr) : 1;
const end = endStr ? parseInt(endStr) : numPages;

const PROMPT = process.env.GEMINI_PROMPT || "انسخ محتوى هذه الصفحة نصًا فقط، لا شيء آخر.";

async function ocrPage(pageNum) {
  const page = await doc.getPage(pageNum);
  const viewport = page.getViewport({ scale: 1.2 });
  const width = Math.ceil(viewport.width);
  const height = Math.ceil(viewport.height);

  const { createCanvas } = await import("@napi-rs/canvas");
  const canvas = createCanvas(width, height);
  const ctx = canvas.getContext("2d");
  await page.render({ canvasContext: ctx, viewport }).promise;

  let pngBuffer = canvas.toBuffer("image/png");
  pngBuffer = await sharp(pngBuffer).grayscale().normalize().sharpen().jpeg({ quality: 90 }).toBuffer();
  const base64 = pngBuffer.toString("base64");
  page.cleanup();

  const body = {
    contents: [
      {
        parts: [
          { text: PROMPT },
          { inline_data: { mime_type: "image/jpeg", data: base64 } },
        ],
      },
    ],
  };

  const BODY_JSON = JSON.stringify(body);

  async function attempt(model) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 90000);
    try {
      const resp = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${API_KEY}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: BODY_JSON,
          signal: ctrl.signal,
        }
      );
      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(`HTTP ${resp.status}: ${errText.slice(0, 200)}`);
      }
      const json = await resp.json();
      return json?.candidates?.[0]?.content?.parts?.map((p) => p.text || "").join("") || "";
    } finally {
      clearTimeout(timer);
    }
  }

  const uniqueModels = [MODEL, ...FALLBACK_MODELS.filter((m) => m !== MODEL)];

  // محاولة على كل النماذج، مع انتظار قصير عند 429/503 ثم إعادة المحاولة
  const maxTries = 12; // لكل صفحة: ~دقائق من الصبر على استنفاد الحصص
  for (let t = 0; t < maxTries; t++) {
    let allQuota = true;
    for (const model of uniqueModels) {
      let finished = false;
      let text = null;
      const result = await Promise.race([
        attempt(model)
          .then((v) => {
            finished = true;
            text = v;
            return "OK";
          })
          .catch((e) => {
            finished = true;
            text = e.message;
            return e.message.includes("429") || e.message.includes("503") ? "QUOTA" : "ERR";
          }),
        new Promise((resolve) =>
          setTimeout(() => resolve("TIMEOUT"), 50000)
        ),
      ]);
      if (result === "OK" && text && text.trim()) return text.trim();
      if (result !== "QUOTA") allQuota = false;
    }
    if (!allQuota) break; // وجدنا خطأ حقيقيًا غير استنفاد الحصص → لا نعيد المحاولة
    // كل النماذج استنفدت حصصها → انتظر 60 ثانية وأعد
    process.stdout.write(`⟳ كل النماذج استنفدت الحصة، انتظار 60 ثانية (محاولة ${t + 1}/${maxTries}) ... `);
    await new Promise((r) => setTimeout(r, 60000));
  }
  throw new Error("فشلت الصفحة عبر جميع النماذج أو تجاوزت المهلة");
}

let startPage = start;
if (existsSync(`${outDir}/progress.json`) && !process.env.NO_RESUME) {
  const prog = JSON.parse(readFileSync(`${outDir}/progress.json`, "utf8"));
  if (prog.lastPage) startPage = prog.lastPage + 1;
}

let currentPart = null;
let partBuf = [];
let lastPage = startPage - 1;

function loadPartSections(partFile) {
  const sections = {};
  if (existsSync(partFile)) {
    const content = readFileSync(partFile, "utf8");
    const blocks = content.split(/^## صفحة /m);
    for (let i = 1; i < blocks.length; i++) {
      const m = blocks[i].match(/^(\d+)\n\n([\s\S]*)$/);
      if (m) sections[parseInt(m[1])] = m[2].replace(/\n$/, "");
    }
  }
  return sections;
}

function flushPart() {
  if (currentPart === null) return;
  const partFile = `${outDir}/part-${String(currentPart).padStart(2, "0")}.md`;
  const sections = loadPartSections(partFile);
  let i = 1;
  while (i < partBuf.length) {
    const line = partBuf[i];
    if (line && line.startsWith("## صفحة ")) {
      const pnum = parseInt(line.replace("## صفحة ", ""));
      const text = partBuf[i + 2] ?? "";
      sections[pnum] = text;
      i += 4;
    } else i++;
  }
  const header = partBuf[0] ?? `# جزء ${currentPart}`;
  const lines = [header, ""];
  const pages = Object.keys(sections).map(Number).sort((a, b) => a - b);
  for (const p of pages) {
    lines.push(`## صفحة ${p}`, "", sections[p], "");
  }
  writeFileSync(partFile, lines.join("\n"), "utf8");
  console.log(`✔ كتبت ${partFile}`);
}

for (let p = startPage; p <= end; p++) {
  const part = Math.floor((p - 1) / 40) + 1;
  if (part !== currentPart) {
    flushPart();
    currentPart = part;
    partBuf = [`# جزء ${part} (صفحات ${(part - 1) * 40 + 1}-${Math.min(part * 40, numPages)})`, ""];
  }
  process.stdout.write(`صفحة ${p}/${end} ... `);
  let text = "";
  try {
    text = await ocrPage(p);
    console.log(`OK (${text.length} حرف)`);
  } catch (e) {
    console.log("فشل نهائي:", e.message.slice(0, 120));
    text = `[تعذر استخراج النص من الصفحة ${p}]`;
  }
  partBuf.push(`## صفحة ${p}`, "", text, "");
  lastPage = p;
  writeFileSync(`${outDir}/progress.json`, JSON.stringify({ lastPage, numPages }, null, 2), "utf8");
  await new Promise((r) => setTimeout(r, 600));
}
flushPart();

console.log(`\nالناتج في ${outDir}`);
doc.destroy();