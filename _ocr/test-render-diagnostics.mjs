import { createCanvas } from "@napi-rs/canvas";
import { readFileSync, writeFileSync } from "fs";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import sharp from "sharp";

const pdfPath = "E:/AI-Content/المدرسة/1-المدخلات/المراجع-والكتب-الخارجية/الثانوية/الصف-الثالث/اللغة-الإنجليزية/المعاصر-انجليزي-3ث-2027.pdf";
const WASM_URL = "E:/AI-Content/_ocr/node_modules/pdfjs-dist/wasm/";

async function test() {
  console.log("1. Reading PDF file...");
  const buf = readFileSync(pdfPath);
  console.log("File read successfully, size:", buf.length);

  console.log("2. Loading PDF doc with pdfjs...");
  const data = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const doc = await pdfjsLib.getDocument({ data, wasmUrl: WASM_URL }).promise;
  console.log("PDF doc loaded. Total pages:", doc.numPages);

  console.log("3. Fetching page 41...");
  const page = await doc.getPage(41);
  console.log("Page 41 fetched.");

  console.log("4. Rendering viewport (scale 1.2)...");
  const viewport = page.getViewport({ scale: 1.2 });
  const width = Math.ceil(viewport.width);
  const height = Math.ceil(viewport.height);
  console.log(`Viewport dimensions: ${width}x${height}`);

  console.log("5. Creating canvas context...");
  const canvas = createCanvas(width, height);
  const ctx = canvas.getContext("2d");
  console.log("Canvas context created.");

  console.log("6. Rendering page to canvas...");
  await page.render({ canvasContext: ctx, viewport }).promise;
  console.log("Page rendered to canvas successfully.");

  console.log("7. Converting canvas to PNG buffer...");
  let pngBuffer = canvas.toBuffer("image/png");
  console.log("Canvas converted to buffer, length:", pngBuffer.length);

  console.log("8. Processing image with sharp...");
  pngBuffer = await sharp(pngBuffer).grayscale().normalize().sharpen().jpeg({ quality: 90 }).toBuffer();
  console.log("Sharp processing complete, final JPEG size:", pngBuffer.length);

  console.log("9. Destroying doc...");
  doc.destroy();
  console.log("Success! Diagnostic test completed with no hangs.");
}

test().catch(e => console.error("Error in test:", e));
