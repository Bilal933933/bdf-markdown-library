import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import { readFileSync } from "fs";

async function check() {
  try {
    const buf = readFileSync("C:/Users/blals/Downloads/كتاب دراسات الصف الثالث الاعدادى ٢٠٢٧ ترم اول.pdf");
    const data = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
    const doc = await pdfjsLib.getDocument({ data }).promise;
    console.log("Pages:", doc.numPages);
    let text = "";
    for (let i = 1; i <= Math.min(3, doc.numPages); i++) {
      const page = await doc.getPage(i);
      const content = await page.getTextContent();
      text += content.items.map((item) => item.str).join(" ");
    }
    console.log("Text Length:", text.length);
    if (text.length < 1000) console.log("Recommendation: OCR");
    else console.log("Recommendation: Direct Extraction");
    await doc.destroy();
  } catch (e) {
    console.error(e);
  }
}
check();
