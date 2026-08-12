import { readFileSync, readdirSync } from "fs";
import path from "path";

const dir = path.resolve(process.argv[2]);
const files = readdirSync(dir).filter((f) => f.startsWith("part-") && f.endsWith(".md")).sort();

let totalPages = 0;
let failed = 0;
let empty = 0;
const perFile = [];

for (const f of files) {
  const c = readFileSync(path.join(dir, f), "utf8");
  const pages = (c.match(/^## صفحة /gm) || []).length;
  totalPages += pages;
  const fails = (c.match(/^## صفحة \d+\n\n\[تعذر استخراج النص/gm) || []).length;
  failed += fails;
  const empties = (c.match(/^## صفحة \d+\n\n\n$/gm) || []).length;
  empty += empties;
  perFile.push(`${f}: ${pages} صفحة (${fails} فاشلة, ${empties} فارغة)`);
}

console.log(perFile.join("\n"));
console.log(`---`);
console.log(`الملفات: ${files.length}`);
console.log(`إجمالي الصفحات: ${totalPages}`);
console.log(`صفحات فاشلة: ${failed}`);
console.log(`صفحات فارغة: ${empty}`);