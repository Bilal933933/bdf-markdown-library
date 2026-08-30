const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs-extra');
const { v4: uuidv4 } = require('uuid');
const ocrService = require('../services/ocrService');

const router = express.Router();
const upload = multer({ dest: 'uploads/' });

// تخزين مؤقت لحالة المهام
const tasks = {};

// ✅ رفع الملف وبدء المعالجة
router.post('/upload', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'لم يتم رفع أي ملف' });
    }

    const taskId = uuidv4();
    const filePath = req.file.path;
    const originalName = req.file.originalname;

    tasks[taskId] = {
      status: 'processing',
      progress: 0,
      result: null,
      error: null,
    };

    // بدء المعالجة في الخلفية باستخدام السكربتات الأصلية للذكاء الاصطناعي
    ocrService.processPDF(filePath, originalName, (progress) => {
      tasks[taskId].progress = progress;
    })
    .then((result) => {
      tasks[taskId].status = 'completed';
      tasks[taskId].result = result;
      tasks[taskId].progress = 100;
    })
    .catch((error) => {
      tasks[taskId].status = 'failed';
      tasks[taskId].error = error.message;
    });

    res.json({ taskId });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ✅ استعلام حالة المهمة
router.get('/status/:taskId', (req, res) => {
  const task = tasks[req.params.taskId];
  if (!task) {
    return res.status(404).json({ error: 'المهمة غير موجودة' });
  }
  res.json({
    status: task.status,
    progress: task.progress,
    result: task.result,
    error: task.error,
  });
});

module.exports = router;
