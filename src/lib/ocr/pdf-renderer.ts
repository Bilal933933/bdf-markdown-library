import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import sharp from "sharp";
import path from "node:path";
import { fileURLToPath } from "node:url";

// مسار wasm مُشتق نسبيًا من موقع الحزمة المثبَّتة، وليس هاردكودد
// لمسار قرص محلي (كان: "E:/AI-Content/_ocr/node_modules/...").
// هذا يجعل الكود يعمل على أي جهاز/سيرفر دون تعديل.
function resolveWasmDir(): string {
  const require = (globalThis as any).require;
  try {
    // في بيئة CommonJS/Next.js نستخدم require.resolve إن توفر
    const pdfjsEntry = require.resolve("pdfjs-dist/package.json");
    return path.join(path.dirname(pdfjsEntry), "wasm") + path.sep;
  } catch {
    // fallback لبيئة ESM بحتة
    const here = path.dirname(fileURLToPath(import.meta.url));
    return path.join(here, "../../../node_modules/pdfjs-dist/wasm") + path.sep;
  }
}

export interface PdfDocument {
  numPages: number;
  getPageImage(pageNum: number, scale?: number): Promise<Buffer>;
  destroy(): void;
}

/**
 * يفتح مستند PDF من Buffer في الذاكرة (لا نكتب على القرص إلا عند الحاجة الفعلية).
 */
export async function loadPdf(pdfBuffer: Buffer): Promise<PdfDocument> {
  const data = pdfBuffer.buffer.slice(
    pdfBuffer.byteOffset,
    pdfBuffer.byteOffset + pdfBuffer.byteLength
  );

  const doc = await pdfjsLib.getDocument({
    data,
    wasmUrl: resolveWasmDir(),
  }).promise;

  return {
    numPages: doc.numPages,

    async getPageImage(pageNum: number, scale = 1.2): Promise<Buffer> {
      const page = await doc.getPage(pageNum);
      const viewport = page.getViewport({ scale });
      const width = Math.ceil(viewport.width);
      const height = Math.ceil(viewport.height);

      const { createCanvas } = await import("@napi-rs/canvas");
      const canvas = createCanvas(width, height);
      const ctx = canvas.getContext("2d");
      await page.render({ canvasContext: ctx as any, viewport }).promise;

      const rawPng = canvas.toBuffer("image/png");
      const optimized = await sharp(rawPng)
        .grayscale()
        .normalize()
        .sharpen()
        .jpeg({ quality: 90 })
        .toBuffer();

      page.cleanup();
      return optimized;
    },

    destroy() {
      doc.destroy();
    },
  };
}
