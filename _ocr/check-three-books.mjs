import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import { readFileSync, existsSync } from "fs";

const books = [
  {
    name: "الرياضيات",
    path: "C:/Users/blals/Downloads/كتاب 3اعدادى مدرسة منهج جديد ترم أول.pdf"
  },
  {
    name: "اللغة الإنجليزية",
    path: "C:/Users/blals/Downloads/تحميل كتاب بروفيشنال في تأسيس ومهارات اللغة الانجليزية للمرحلة الاعدادية PDF.PDF"
  },
  {
    name: "العلوم",
    path: "C:/Users/blals/Downloads/علوم ثالثة اعدادى ٢٠٢٧ ترم اول.pdf"
  }
];

async function checkBooks() {
  for (const book of books) {
    console.log(`\n=== فحص كتاب: ${book.name} ===`);
    if (!existsSync(book.path)) {
      console.log(`❌ الملف غير موجود في المسار: ${book.path}`);
      continue;
    }
    try {
      const buf = readFileSync(book.path);
      const data = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
      const doc = await pdfjsLib.getDocument({ data }).promise;
      console.log(`✅ عدد الصفحات: ${doc.numPages}`);
      
      let text = "";
      for (let i = 1; i <= Math.min(3, doc.numPages); i++) {
        const page = await doc.getPage(i);
        const content = await page.getTextContent();
        text += content.items.map((item) => item.str).join(" ");
      }
      console.log(`طول النص في أول 3 صفحات: ${text.length} حرف`);
      if (text.length < 1000) {
        console.log("النتيجة الموصى بها: معالجة ذكية OCR (ممسوح ضوئياً)");
      } else {
        console.log("النتيجة الموصى بها: استخراج مباشر فوري (يحتوي طبقة نصية)");
      }
      await doc.destroy();
    } catch (e) {
      console.error(`❌ خطأ أثناء فحص الملف: ${e.message}`);
    }
  }
}

checkBooks();
