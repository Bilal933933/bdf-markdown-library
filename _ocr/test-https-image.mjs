import { createCanvas } from "@napi-rs/canvas";
import { readFileSync } from "fs";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import sharp from "sharp";
import https from "https";

const pdfPath = "E:/AI-Content/المدرسة/1-المدخلات/المراجع-والكتب-الخارجية/الثانوية/الصف-الثالث/اللغة-الإنجليزية/المعاصر-انجليزي-3ث-2027.pdf";
const WASM_URL = "E:/AI-Content/_ocr/node_modules/pdfjs-dist/wasm/";
const key = process.env.GEMINI_API_KEY ?? "YOUR_KEY_HERE";
const model = "gemini-3.1-flash-lite";

async function testHttpsImage() {
  console.log("1. Rendering page 41 to get image data...");
  const buf = readFileSync(pdfPath);
  const data = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const doc = await pdfjsLib.getDocument({ data, wasmUrl: WASM_URL }).promise;
  const page = await doc.getPage(41);
  const viewport = page.getViewport({ scale: 1.2 });
  const canvas = createCanvas(Math.ceil(viewport.width), Math.ceil(viewport.height));
  const ctx = canvas.getContext("2d");
  await page.render({ canvasContext: ctx, viewport }).promise;
  let pngBuffer = canvas.toBuffer("image/png");
  pngBuffer = await sharp(pngBuffer).grayscale().normalize().sharpen().jpeg({ quality: 90 }).toBuffer();
  const base64 = pngBuffer.toString("base64");
  doc.destroy();
  console.log("Image rendered. Base64 length:", base64.length);

  const body = JSON.stringify({
    contents: [
      {
        parts: [
          { text: "انسخ محتوى هذه الصفحة نصًا فقط، لا شيء آخر." },
          { inline_data: { mime_type: "image/jpeg", data: base64 } }
        ]
      }
    ]
  });

  console.log("2. Sending image data via native https module...");
  const start = Date.now();

  const options = {
    hostname: 'generativelanguage.googleapis.com',
    port: 443,
    path: `/v1beta/models/${model}:generateContent?key=${key}`,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(body)
    }
  };

  const req = https.request(options, (res) => {
    console.log("3. Response status:", res.statusCode);
    let resData = '';
    res.on('data', (chunk) => { resData += chunk; });
    res.on('end', () => {
      try {
        const json = JSON.parse(resData);
        const text = json?.candidates?.[0]?.content?.parts?.[0]?.text;
        console.log("4. Successfully got OCR text! Length:", text?.length);
        console.log(`Duration: ${Date.now() - start}ms`);
      } catch (e) {
        console.error("Failed to parse response:", e);
      }
    });
  });

  req.on('error', (e) => {
    console.error("HTTPS request failed:", e);
  });

  req.write(body);
  req.end();
}

testHttpsImage();
