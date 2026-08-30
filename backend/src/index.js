require('dotenv').config();
const express = require('express');
const cors = require('cors');
const apiRoutes = require('./routes/api');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

// تقديم ملفات التحميل (ZIP) كملفات ثابتة
app.use('/download', express.static(path.join(__dirname, '../../output')));

app.use('/api', apiRoutes);

app.listen(PORT, () => {
  console.log(`✅ Backend running on http://localhost:${PORT}`);
});
