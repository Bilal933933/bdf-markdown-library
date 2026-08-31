const fs = require('fs-extra');
const path = require('path');
const { spawn } = require('child_process');
const archiver = require('archiver');

async function processPDF(filePath, originalName, onProgress) {
  try {
    const bookName = path.basename(originalName, path.extname(originalName));
    const outputDir = path.join(__dirname, '../../../output', bookName);
    await fs.ensureDir(outputDir);

    onProgress(15);

    const scriptPath = path.join(__dirname, '../../../_ocr/gemini-ocr.mjs');
    const apiKey = process.env.GEMINI_API_KEY;

    if (!apiKey) {
      throw new Error('مفتاح GEMINI_API_KEY غير مُعرّف في إعدادات الخادم (Backend .env)');
    }

    onProgress(30);

    // استخدام spawn لتنفيذ السكربت بأمان تام ومنع أي Command Injection
    await new Promise((resolve, reject) => {
      const child = spawn('node', [scriptPath, filePath, outputDir], {
        env: { ...process.env, GEMINI_API_KEY: apiKey }
      });

      let stderrData = '';

      child.stderr.on('data', (data) => {
        stderrData += data.toString();
      });

      child.on('close', (code) => {
        if (code !== 0) {
          console.error('❌ OCR Process Error:', stderrData);
          return reject(new Error(stderrData || `فشل المعالجة برمز خروج ${code}`));
        }
        resolve(true);
      });

      child.on('error', (err) => {
        reject(err);
      });
    });

    onProgress(80);

    const zipPath = path.join(outputDir, `${bookName}_markdown.zip`);
    await createZipFromDir(outputDir, zipPath);

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

function createZipFromDir(sourceDir, zipPath) {
  return new Promise((resolve, reject) => {
    const output = fs.createWriteStream(zipPath);
    const archive = archiver('zip', { zlib: { level: 9 } });

    output.on('close', resolve);
    archive.on('error', reject);

    archive.pipe(output);
    archive.glob('*.md', { cwd: sourceDir });
    archive.finalize();
  });
}

module.exports = { processPDF };
