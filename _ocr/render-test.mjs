import { createCanvas } from "@napi-rs/canvas";
import { readFileSync } from "fs";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";

const buf = readFileSync("D:/مسابقة معلم مادة/كيف تتقن الصرف.pdf");
const data = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);

const WASM_URL = "E:/AI-Content/_ocr/node_modules/pdfjs-dist/wasm/";
const doc = await pdfjsLib.getDocument({ data, wasmUrl: WASM_URL }).promise;
const page = await doc.getPage(310);
const viewport = page.getViewport({ scale: 2 });
const canvas = createCanvas(Math.ceil(viewport.width), Math.ceil(viewport.height));
const ctx = canvas.getContext("2d");
await page.render({ canvasContext: ctx, viewport }).promise;

const img = ctx.getImageData(0, 0, viewport.width, viewport.height);
let nonWhite = 0;
for (let i = 0; i < img.data.length; i += 4) {
  if (img.data[i] < 245 || img.data[i + 1] < 245 || img.data[i + 2] < 245) nonWhite++;
}
const total = img.data.length / 4;
console.log("dims:", viewport.width, "x", viewport.height);
console.log("pixels:", total, "| non-white:", nonWhite, "| ratio:", (nonWhite / total).toFixed(4));
doc.destroy();