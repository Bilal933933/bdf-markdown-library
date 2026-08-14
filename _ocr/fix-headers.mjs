import { readFileSync, writeFileSync, readdirSync } from "fs";

const jobs = [
  { dir: "E:/AI-Content/_ocr/marker_out/balagha_rebuilt", title: "كيف تتقن البلاغة" },
  { dir: "E:/AI-Content/_ocr/marker_out/sarf_rebuilt", title: "كيف تتقن الصرف" },
];

for (const { dir, title } of jobs) {
  for (const f of readdirSync(dir).filter((x) => /^part-\d+\.md$/.test(x)).sort()) {
    const p = dir + "/" + f;
    let buf = readFileSync(p);
    if (buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf) buf = buf.subarray(3);
    let txt = buf.toString("utf8");
    txt = txt.replace(/^# (ال)?جزء (\d+) \(صفحات ([\d-]+)\)/, `# ${title} — الجزء $2 (صفحات $3)`);
    if (!txt.startsWith("# ")) {
      console.log("NO HEADER:", f);
      continue;
    }
    writeFileSync(p, txt, "utf8");
    console.log(f, "=>", txt.split("\n")[0]);
  }
}
