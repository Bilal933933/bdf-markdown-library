const express = require('express');
const multer = require('multer');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');

const app = express();
const port = 3001;

app.use(cors());
app.use(express.json());
app.use(express.static(__dirname));

const uploadDir = path.join(__dirname, '_ocr', 'uploads');
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir, { recursive: true });
}

const upload = multer({ dest: uploadDir });

app.post('/api/convert', upload.single('pdf'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'لم يتم رفع أي ملف PDF.' });
        }

        const apiKey = req.body.apiKey;
        if (!apiKey) {
            if (fs.existsSync(req.file.path)) fs.unlinkSync(req.file.path);
            return res.status(400).json({ error: 'مفتاح Gemini API Key مطلوب.' });
        }

        const filePath = req.file.path;
        const originalName = Buffer.from(req.file.originalname, 'latin1').toString('utf8');
        const baseName = path.basename(originalName, path.extname(originalName));
        
        // مجلد الناتج الخاص بالكتاب
        const outputDir = path.join(__dirname, baseName);
        if (!fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir, { recursive: true });
        }

        // تشغيل سكربت gemini-ocr.mjs الأصلي للكتب الممسوحة بدقة عالية
        const scriptPath = path.join(__dirname, '_ocr', 'gemini-ocr.mjs');
        // نطاق صفحات تجريبي أول 15 صفحة (يمكن زيادته أو تركه لمعالجة كاملة حسب الحاجة)
        const command = `node "${scriptPath}" "${filePath}" "${outputDir}" 1 15`;

        console.log(`بدء معالجة الذكاء الاصطناعي للكتاب: ${baseName}`);

        exec(command, { env: { ...process.env, GEMINI_API_KEY: apiKey } }, (error, stdout, stderr) => {
            if (fs.existsSync(filePath)) {
                fs.unlinkSync(filePath);
            }

            if (error) {
                console.error("خطأ في Gemini OCR:", stderr || error.message);
                return res.status(500).json({ error: 'فشل معالجة الذكاء الاصطناعي: ' + (stderr || error.message) });
            }

            // إعادة بناء وتجميع الأجزاء عبر rebuild-parts.mjs إن وجد
            const rebuildScript = path.join(__dirname, '_ocr', 'rebuild-parts.mjs');
            const rebuildCommand = fs.existsSync(rebuildScript) 
                ? `node "${rebuildScript}" "${outputDir}" "${outputDir}"`
                : null;

            const finalizeResults = () => {
                let resultFiles = [];
                try {
                    if (fs.existsSync(outputDir)) {
                        const files = fs.readdirSync(outputDir).filter(f => f.endsWith('.md'));
                        files.forEach(file => {
                            const content = fs.readFileSync(path.join(outputDir, file), 'utf8');
                            resultFiles.push({
                                name: file,
                                content: content
                            });
                        });
                    }
                } catch (e) {
                    console.error("خطأ في قراءة الأجزاء:", e);
                }

                res.json({
                    success: true,
                    bookName: baseName,
                    files: resultFiles
                });
            };

            if (rebuildCommand) {
                exec(rebuildCommand, () => finalizeResults());
            } else {
                finalizeResults();
            }
        });

    }	 catch (error) {
        console.error("خطأ عام:", error);
        res.status(500).json({ error: error.message });
    }
});

app.listen(port, () => {
    console.log(`خادم الذكاء الاصطناعي يعمل على http://localhost:${port}`);
});
