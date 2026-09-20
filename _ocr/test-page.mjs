import { readFileSync, writeFileSync } from "fs";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";

const WASM_URL = "E:/AI-Content/_ocr/node_modules/pdfjs-dist/wasm/";
const pdfPath = process.argv[2];
const pageNum = parseInt(process.argv[3] || "1");
const API_KEY = process.env.GEMINI_API_KEY ?? "YOUR_KEY_HERE";

const buf = readFileSync(pdfPath);
const data = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
const doc = await pdfjsLib.getDocument({ data, wasmUrl: WASM_URL }).promise;
const page = await doc.getPage(pageNum);
const viewport = page.getViewport({ scale: 1.2 });
const width = Math.ceil(viewport.width);
const height = Math.ceil(viewport.height);
const { createCanvas } = await import("@napi-rs/canvas");
const canvas = createCanvas(width, height);
const ctx = canvas.getContext("2d");
await page.render({ canvasContext: ctx, viewport }).promise;
let pngBuffer = canvas.toBuffer("image/png");
const sharp = (await import("sharp")).default;
pngBuffer = await sharp(pngBuffer).grayscale().normalize().sharpen().jpeg({ quality: 90 }).toBuffer();
writeFileSync("E:/AI-Content/_ocr/test_page.jpg", pngBuffer);
const base64 = pngBuffer.toString("base64");
console.log("PNG bytes:", pngBuffer.length, "dims:", width + "x" + height);

const PROMPT = process.env.GEMINI_PROMPT || "انسخ محتوى هذه الصفحة نصًا فقط، لا شيء آخر.";
const body = { contents: [{ parts: [{ text: PROMPT }, { inline_data: { mime_type: "image/jpeg", data: base64 } }] }] };

for (const model of ["gemini-3.1-flash-lite", "gemini-flash-latest", "gemini-3.6-flash"]) {
  const resp = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${API_KEY}`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
  );
  const text = await resp.text();
  console.log("\n== " + model + " HTTP " + resp.status + " ==");
  console.log(text.slice(0, 400));
}
doc.destroy();