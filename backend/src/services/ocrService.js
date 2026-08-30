const fs = require('fs-extra');
const path = require('path');
const { exec } = require('child_process');
const archiver = require('archiver');

async function processPDF(filePath, originalName, onProgress) {
  try {
    const bookName = path.basename(originalName, path.extname(originalName));
    const outputDir = path.join(__dirname, '../../../output', bookName);
    await fs.ensureDir(outputDir);

    onProgress(15);

    // مسار سكربت gemini-ocr.mjs الموجود في المستودع الرئيسي
    const scriptPath = path.join(__dirname, '../../../_ocr/gemini-ocr.mjs');
    const apiKey = process.env.GEMINI_API_KEY;

    if (!apiKey) {
      throw new Error('مفتاح GEMINI_API_KEY غير مُعرّف في إعدادات الخادم (Backend .env)');
    }

    onProgress(30);

    // تشغيل سكربت OCR الأصلي عبر سطر الأوامر مع تمرير مفتاح الـ API
    const command = `node "${scriptPath}" "${filePath}" "${outputDir}"`;

    await new Promise((resolve, reject) => {
      exec(command, { env: { ...process.env, GEMINI_API_KEY: apiKey } }, (error, stdout, stderr) => {
        if (error) {
          console.error('❌ OCR Script Error:', stderr || error.message);
          return reject(new Error(stderr || error.message));
        }
        resolve(stdout);
      });
    });

    onProgress(80);

    // ضغط مجلد النتائج (`part-XX.md`) في ملف ZIP واحد
    const zipPath = path.join(outputDir, `${bookName}_markdown.zip`);
    await createZipFromDir(outputDir, zipPath);

    // تنظيف الملف المؤقت المرفوع
    if (await fs.pathExists(filePath)) {
      await fs.remove(filePath);
    }

    onProgress(100);

    return {
      downloadUrl: `/download/${bookName}/${bookName}_markdown.zip`,
      fileName: `${bookName}_markdown.zip`,
    };

  } catch (error) {
    console.error('❌ Process PDF Error:', error);
    throw error;
  }
}

// دالة مساعدة لضغط المجلد بالكامل في ZIP
function createZipFromDir(sourceDir, zipPath) {
  return new Promise((resolve, reject) => {
    const output = fs.createWriteStream(zipPath);
    const archive = archiver('zip', { zlib: { level: 9 } });

    output.on('close', resolve);
    archive.on('error', reject);

    archive.pipe(output);
    // إضافة جميع ملفات .md الناتجة
    archive.glob('*.md', { cwd: sourceDir });
    archive.finalize();
  });
}

module.exports = { processPDF };
