# Document Conversion Engine — Project Documentation

> **وثيقة مرجعية أساسية للمشروع**
>
> الغرض من هذه الوثيقة هو تثبيت كل القرارات والمناقشات التي تم الاتفاق عليها حتى الآن، بحيث توضع داخل مشروع الـBackend ويستمر العمل من آخر نقطة بدون فقدان السياق.
>
> **الحالة:** مرحلة التحليل والتصميم — لم يبدأ التنفيذ بعد.

---

## 1. هدف المشروع

### 1.1 الاسم والوصف

**Document Conversion Engine — محرك تحويل المستندات**

المشروع ليس Chatbot (مساعد دردشة)، وليس OCR فقط.

الهدف هو بناء محرك قادر على استقبال مستندات مختلفة، استخراج محتواها، فهم بنيتها، تحويلها إلى **Document Model موحد**، ثم إخراجها بصيغة Markdown مع Metadata غنية.

### 1.2 المسار العام

```text
Document
   ↓
Extract / OCR
   ↓
Structure
   ↓
Document Model
   ↓
Markdown
```

وفي التصميم المتقدم:

```text
PDF
 ↓
Extraction
 ↓
OCR
 ↓
Layout Detection
 ↓
Document Model
 ↓
Hierarchy Detection
 ↓
Semantic Segmentation
 ↓
Lesson / Unit
 ↓
Markdown + Metadata
```

---

# 2. نطاق الإصدار الأول

## 2.1 أنواع الملفات الأساسية

سيتم دعم:

- PDF — أساسي
- DOCX — أساسي
- PNG — أساسي
- JPG / JPEG — أساسي
- WebP — أساسي
- TXT — بسيط

## 2.2 أنواع مؤجلة

لن تدخل النواة في الإصدار الأول:

- PPTX
- XLSX
- EPUB
- HTML

يمكن إضافتها لاحقًا بعد استقرار النواة.

---

# 3. المبادئ المعمارية

## 3.1 Document Model هو قلب النظام

لا نريد بناء محولات منفصلة تنتج Markdown مباشرة:

```text
PDF → Markdown
DOCX → Markdown
Image → Markdown
```

بل نريد:

```text
Input
  ↓
Parser / OCR
  ↓
Document Model
  ↓
Markdown Renderer
  ↓
Output
```

والسبب أن Document Model سيكون طبقة وسيطة مستقلة يمكن أن تخدم عدة مخرجات مستقبلًا:

```text
Document Model
 ├── Markdown
 ├── HTML
 ├── JSON
 └── RAG
```

## 3.2 الفصل عن الأنظمة المستهلكة

المحول لا يعرف:

- EduAssist
- RAG
- نظام الطلاب
- منصة تعليمية بعينها

هو يعرف فقط المفاهيم العامة للمستند:

```text
Document
Unit
Lesson
Section
Block
Asset
Metadata
```

أما المستهلك الخارجي فيستخدم:

```text
Markdown
Metadata
```

بالطريقة المناسبة له.

---

# 4. PDF Processing

## 4.1 PyMuPDF

المحرك الأساسي للتعامل مع PDF هو:

**PyMuPDF**

ويستخدم في:

- قراءة PDF
- استخراج النص
- استخراج الصفحات
- استخراج الصور
- Metadata
- Rendering — تحويل الصفحة إلى صورة

## 4.2 pdfplumber

يستخدم:

**pdfplumber**

عند الحاجة إلى استخراج الجداول.

ليس بديلًا عن PyMuPDF، بل أداة متخصصة تستدعى عندما تحتاج العملية لذلك.

---

# 5. Image Processing

## 5.1 OpenCV

المحرك الأساسي لمعالجة الصور:

**OpenCV**

ويستخدم في:

- Deskew — تصحيح الميل
- إزالة الضوضاء
- تحسين التباين
- Thresholding — المعالجة بالعتبة
- تنظيف الصفحة

## 5.2 Pillow

لعمليات الصور العامة:

- القراءة والحفظ
- التحويل بين الصيغ
- Resize — تغيير الحجم
- PNG / JPEG / WebP

---

# 6. OCR

## 6.1 PaddleOCR

**PaddleOCR** هو Primary OCR — محرك OCR الأساسي.

## 6.2 Gemini Vision

**Gemini Vision** هو Fallback OCR — محرك احتياطي.

لا يستخدم لكل الصفحات.

المسار المقترح:

```text
PaddleOCR
    ↓
Quality Gate
    ↓
جيد ──────────→ قبول
    │
    ↓
ضعيف
    ↓
Gemini
```

## 6.3 Tesseract

غير موجود في المسار الأساسي حاليًا.

يمكن إضافته لاحقًا للـBenchmark أو كـFallback إضافي إذا أثبت فائدة.

## 6.4 EasyOCR

نفس القرار:

لا تتم إضافته حاليًا كاعتماد إضافي بدون حاجة مثبتة.

---

# 7. Quality Gate

يجب أن توجد طبقة جودة مستقلة بعد OCR.

```text
OCR
 ↓
Quality Analyzer
 ↓
Quality Score
 ↓
Accept / Retry / Gemini
```

لا نعتمد فقط على confidence الذي توفره مكتبة OCR.

## 7.1 معايير الجودة المقترحة

سيتم لاحقًا بناء معايير خاصة بالمشروع مثل:

- نسبة الأحرف العربية
- الرموز غير الطبيعية
- طول النص
- الكلمات غير الصالحة
- ترتيب الأسطر
- النص المكرر
- الصفحات الفارغة
- جودة استخراج الجداول

هذه المعايير لم يتم تثبيت تفاصيل خوارزميتها بعد.

---

# 8. Document Model

هذه من أهم أجزاء التصميم، وما زالت تحتاج تفصيلًا نهائيًا قبل التنفيذ.

## 8.1 النموذج الأساسي الأولي

```text
Document
│
├── Metadata
│
├── Pages
│   └── Blocks
│       ├── Heading
│       ├── Paragraph
│       ├── List
│       ├── Table
│       ├── Image
│       ├── Quote
│       └── Code
│
└── Assets
```

## 8.2 النموذج المتقدم بعد إضافة البنية التعليمية

بسبب الحاجة إلى اكتشاف الوحدات والدروس، أصبح الاتجاه الحالي لنموذج أغنى:

```text
Document
│
├── Metadata
│
├── Sections
│   │
│   ├── Unit
│   │   ├── Lesson
│   │   │   ├── Section
│   │   │   │   ├── Heading
│   │   │   │   ├── Paragraph
│   │   │   │   ├── List
│   │   │   │   ├── Table
│   │   │   │   ├── Image
│   │   │   │   ├── Example
│   │   │   │   └── Exercise
│   │   │   │
│   │   │   └── ...
│   │   └── ...
│   │
│   └── ...
│
└── Assets
```

لكن **ليس مطلوبًا اكتشاف كل أنواع الـBlocks في الإصدار الأول**.

نبدأ بالأنواع الأكثر موثوقية:

```text
Heading
Paragraph
List
Table
Image
```

ثم يمكن إضافة:

```text
Example
Exercise
Definition
Note
```

عندما تكون هناك حاجة فعلية لها.

---

# 9. Structure / Layout Detection

## 9.1 اكتشاف العناوين في PDF النصي

لا نعتمد على النص وحده.

PyMuPDF يمكنه إعطاؤنا إشارات مثل:

- حجم الخط
- نوع الخط
- Bold
- موضع النص
- الصفحة
- الإحداثيات
- ترتيب العناصر

مثال:

```text
النص              الحجم      Bold
-----------------------------------
الوحدة الأولى       24        نعم
المبتدأ والخبر      20        نعم
المبتدأ هو...       14        لا
```

هذه الإشارات تساعد في تحديد ما إذا كان العنصر Heading أم Paragraph.

## 9.2 PDF الممسوح ضوئيًا

في PDF الممسوح، OCR يعطي عادة:

```text
text
bounding box
confidence
```

لكن ذلك لا يعني بالضرورة:

> هذا عنوان.

لذلك نحتاج إلى **Layout Analysis — تحليل تخطيط الصفحة**.

يمكن استخدام إشارات التخطيط، ومع الحالات المعقدة يمكن أن تساعد نماذج AI.

---

# 10. Table Detection

لا نعتمد على المسافات فقط لافتراض وجود جدول.

نبحث عن إشارات مثل:

- الخطوط
- الأعمدة
- الصفوف
- المحاذاة
- المربعات
- تكرار X positions

والهدف بناء نموذج:

```text
Table
├── Row
│   ├── Cell
│   ├── Cell
│   └── Cell
├── Row
│   └── ...
```

ثم يقوم Markdown Renderer بتحويله مثلًا إلى:

```markdown
| المصطلح | التعريف |
|---|---|
| المبتدأ | اسم مرفوع... |
| الخبر | ما يتمم معنى... |
```

إذا كان الجدول معقدًا جدًا ولا يمكن استخراجه بثقة، يمكن إرسال الصفحة إلى Gemini.

---

# 11. Hierarchy Detection

لا ينبغي افتراض:

```text
كل Heading = Lesson
```

لأن الكتاب قد يحتوي على مستويات متعددة:

```text
الوحدة الأولى
    المبحث الأول
        الدرس الأول
            تعريف
            أمثلة
            تدريبات
        الدرس الثاني
```

أو:

```text
الدرس الأول
...
تمرين
...
الدرس الثاني
```

لذلك نحتاج إلى **Hierarchy Detection — اكتشاف التسلسل الهرمي**.

الهدف المفاهيمي:

```text
Book
│
├── Unit
│   ├── Lesson
│   │   ├── Section
│   │   ├── Paragraph
│   │   ├── Example
│   │   └── Exercise
│   │
│   └── Lesson
│
└── Unit
```

---

# 12. Semantic Segmentation

هذه من أهم الأفكار التي تمت إضافتها إلى التصميم.

بعد استخراج:

```text
Heading
Paragraph
Table
Image
...
```

نبحث عن الموضوعات والبنية الدلالية للمستند.

مثال:

```text
# الوحدة الأولى: النحو

## الدرس الأول: المبتدأ والخبر

...

## الدرس الثاني: كان وأخواتها

...

## الدرس الثالث: إن وأخواتها

...
```

يمكن عندها إنتاج:

```text
Lesson 1
pages 10-15

Lesson 2
pages 16-21

Lesson 3
pages 22-27
```

ثم إخراج الملفات بناءً على ذلك.

---

# 13. قاعدة عدم الاختراع

إذا لم نستطع معرفة حدود الدرس أو الوحدة بثقة، لا نخترع Metadata.

يمكن إخراج:

```text
segments/
├── segment-001.md
├── segment-002.md
└── ...
```

مع Metadata مثل:

```json
{
  "type": "unknown_section",
  "confidence": 0.61
}
```

القاعدة:

> النظام يكتشف ما يستطيع إثباته، ولا يخترع Metadata.

---

# 14. Lesson / Unit Segmentation

## 14.1 هل يكون كل درس ملفًا؟

الاتجاه الحالي: **نعم، إذا أمكن اكتشاف حدود الدرس بثقة.**

مثلًا:

```text
كتاب النحو.pdf
```

قد ينتج:

```text
output/
├── metadata.json
├── lessons/
│   ├── 001-المبتدأ-والخبر.md
│   ├── 002-كان-وأخواتها.md
│   ├── 003-إن-وأخواتها.md
│   └── 004-المفعول-به.md
└── assets/
```

لكن التصميم الذي نميل إليه حاليًا هو جعل كل درس مجلدًا مستقلًا:

```text
lessons/
└── 001/
    ├── content.md
    ├── metadata.json
    └── assets/
```

وهذا أفضل عندما يكون للدرس صور وملفات مرتبطة به.

---

# 15. Metadata

Metadata يجب أن تكون غنية وليست مجرد عنوان.

مثال تصوري:

```json
{
  "id": "lesson-002",
  "title": "كان وأخواتها",

  "subject": "اللغة العربية",
  "grade": "الثالث الإعدادي",
  "stage": "الإعدادية",

  "unit": {
    "id": "unit-01",
    "title": "النحو"
  },

  "source": {
    "file": "كتاب اللغة العربية.pdf",
    "pages": [16, 17, 18, 19]
  },

  "content": {
    "paragraphs": 24,
    "tables": 2,
    "images": 3
  },

  "extraction": {
    "method": "pymupdf+paddleocr",
    "ocr_pages": [17, 18],
    "quality": 0.94
  }
}
```

## 15.1 Metadata المتوقعة

يمكن أن تشمل:

- id
- title
- subject
- grade
- stage
- unit
- source
- source pages
- content statistics
- extraction method
- OCR pages
- quality score

وسيتم تحديد الـSchema النهائي لاحقًا.

---

# 16. العلاقة مع RAG وEduAssist

Metadata المصممة بهذه الطريقة يمكن استخدامها لاحقًا كـRAG Metadata Filter.

مثال:

```text
grade = "prep_3"
subject = "arabic"
unit = "grammar"
lesson = "kana_and_sisters"
```

لكن Document Conversion Engine نفسه لا يعتمد على EduAssist.

العلاقة:

```text
Document Conversion Engine
        ↓
Markdown + Metadata
        ↓
Consumer
        ↓
RAG / EduAssist / Other Systems
```

هذا يحافظ على استقلال المشروع.

---

# 17. Markdown Renderer

سيكون لدينا **Markdown Renderer — محوّل Markdown خاص بالمشروع**.

ليس مجرد:

```text
text.replace(...)
```

بل مسؤول عن تحويل عناصر Document Model إلى Markdown بشكل منظم.

المخرجات الأساسية:

```text
Heading → #
Paragraph → text
List → -
Table → Markdown table
Image → ![]
Quote → >
```

مع مراعاة المحتوى العربي وRTL — من اليمين إلى اليسار.

---

# 18. Output Structure

الاتجاه الحالي للناتج:

```text
conversion/
│
├── document.md
├── metadata.json
│
├── units/
│   └── 01/
│       ├── metadata.json
│       │
│       └── lessons/
│           ├── 01/
│           │   ├── content.md
│           │   ├── metadata.json
│           │   └── assets/
│           │
│           ├── 02/
│           │   ├── content.md
│           │   ├── metadata.json
│           │   └── assets/
│           │
│           └── 03/
│
└── assets/
```

## 18.1 لماذا نحتفظ بـdocument.md؟

وجود:

```text
document.md
```

الكامل مهم حتى لا نفقد الأصل المنطقي للمستند بعد التقسيم إلى وحدات ودروس.

---

# 19. API Layer

## 19.1 FastAPI

**FastAPI** هو إطار الـAPI الرئيسي.

## 19.2 Pydantic

يستخدم في:

- Request Validation — التحقق من الطلبات
- Response Schemas — نماذج الاستجابة
- Configuration Models — نماذج الإعدادات

## 19.3 Uvicorn

لتشغيل التطبيق.

---

# 20. Long-Running Tasks

لن يتم تحويل كتاب 500 صفحة داخل Request واحد.

المسار:

```text
Client
  ↓
FastAPI
  ↓
Redis Queue
  ↓
Worker
  ↓
Conversion Pipeline
```

الأدوات:

- Redis
- RQ

وتم استبعاد Celery من الإصدار الأول.

---

# 21. Database

الأدوات:

- SQLAlchemy
- PostgreSQL

تستخدم قاعدة البيانات لبيانات مثل:

```text
Conversion
Task
File
Status
Progress
Error
Metadata
```

في التطوير المحلي يمكن استخدام SQLite إذا أردنا، مع عدم ربط منطق التطبيق مباشرة بنوع قاعدة البيانات.

---

# 22. Storage

نحتاج إلى **Storage Abstraction — طبقة تخزين مجردة**.

البداية:

```text
Local Filesystem
```

والتصميم يسمح لاحقًا باستخدام:

```text
S3
MinIO
```

بدون تغيير Pipeline.

---

# 23. Configuration

نستخدم:

**pydantic-settings**

لإدارة الإعدادات مثل:

```text
DATABASE_URL
REDIS_URL
STORAGE_DIR
GEMINI_API_KEYS
MAX_FILE_SIZE
MAX_PAGES
OCR_SETTINGS
```

---

# 24. Retry / Reliability

نستخدم:

**Tenacity**

لإعادة المحاولة في العمليات التي تستحق ذلك، خصوصًا:

- Gemini API
- الشبكة
- الخدمات الخارجية

ولا يتم وضع Retry عشوائي على كل شيء.

---

# 25. Testing

إطار الاختبارات:

**pytest**

الاختبارات ليست للـAPI فقط.

سنختبر:

```text
PDF extraction
OCR
Preprocessing
Document Model
Markdown rendering
Quality scoring
Failed pages
Resume
```

وسيكون الاختبار جزءًا أساسيًا من تطوير Pipeline.

---

# 26. Dependencies — القائمة الحالية

```text
API
├── FastAPI
├── Pydantic
└── Uvicorn

PDF
├── PyMuPDF
└── pdfplumber

Images
├── OpenCV
└── Pillow

OCR
├── PaddleOCR
└── Gemini

Documents
├── python-docx
└── [PPTX لاحقًا]

Infrastructure
├── Redis
├── RQ
├── SQLAlchemy
└── PostgreSQL

Configuration
└── pydantic-settings

Reliability
└── Tenacity

Testing
└── pytest
```

---

# 27. Task Lifecycle

هذا الجزء ما زال يحتاج تصميمًا تفصيليًا قبل التنفيذ.

الحالات الأساسية المتفق عليها:

```text
queued
   ↓
processing
   ↓
completed
```

أو:

```text
queued
   ↓
processing
   ↓
failed
```

ومن المتطلبات المهمة أن يكون النظام قادرًا على استئناف كتاب توقف عند صفحة معينة، مثل:

```text
page 173
```

بدل إعادة المعالجة من البداية.

كما أن تصميم دورة حياة المهمة يجب أن يحدد:

- أين تحفظ الحالة؟
- كيف يحفظ progress؟
- كيف تسجل الأخطاء؟
- كيف يستأنف التحويل؟
- ما الذي يحدث عند إعادة تشغيل Worker؟
- ما الفرق بين retry للمهمة وresume للتحويل؟

**لم يتم تثبيت هذه التفاصيل بعد.**

---

# 28. القرارات التي لم تُحسم نهائيًا

حتى لا نعتبر التصميم مكتملًا قبل أوانه، هناك ثلاث نقاط رئيسية كانت مفتوحة:

## 28.1 Document Model بالتفصيل

لم يتم تحديد الـSchema النهائي لكل:

- Document
- Page
- Block
- Unit
- Lesson
- Section
- Table
- Row
- Cell
- Asset
- Metadata

## 28.2 PDF Structure Detection

لم يتم حسم الخوارزمية النهائية التي تحدد:

- هل النص Heading؟
- ما مستوى الـHeading؟
- هل العنصر Paragraph؟
- هل العناصر جدول؟
- كيف يتم بناء hierarchy؟
- متى نستخدم AI؟

## 28.3 Storage & Task Lifecycle

لم يتم حسم:

```text
queued → processing → completed
                   ↘ failed
```

بالتفصيل، خصوصًا:

- checkpoint
- resume
- retry
- failure recovery
- progress tracking

---

# 29. القرار المعماري الحالي حول التقطيع

تمت مناقشة فكرة تقطيع المستند حسب الموضوع/الدرس، وتم تثبيت الاتجاه التالي:

> **التقطيع إلى Units / Lessons مستحب جدًا، خصوصًا لأن المخرجات قد تستخدم لاحقًا في منصات تعليمية أو RAG.**

لكن:

> **Semantic Segmentation ليست جزءًا ملتصقًا بطبقة استخراج الملفات، بل طبقة مستقلة بعد Document Model.**

المسار:

```text
Input
 ↓
Extraction
 ↓
OCR
 ↓
Layout Detection
 ↓
Document Model
 ↓
Hierarchy Detection
 ↓
Semantic Segmentation
 ↓
Unit / Lesson
 ↓
Markdown + Metadata
```

ولا نستخدم تقطيعًا ساذجًا مثل:

```text
قسّم النص كل X حرف
```

---

# 30. قواعد تصميم مهمة

## Rule 1 — لا نخترع

إذا لم نملك دليلًا كافيًا على بنية أو Metadata:

```text
unknown_section
```

أفضل من معلومة خاطئة.

## Rule 2 — لا نربط الـConverter بالمستهلك

Converter مستقل عن:

- EduAssist
- RAG
- Student System

## Rule 3 — Document Model قبل Markdown

Markdown هو Output، وليس النموذج الداخلي.

## Rule 4 — Quality Gate مستقل

جودة OCR لا تعتمد على confidence وحده.

## Rule 5 — Fallback مشروط

Gemini لا يستخدم لكل الصفحات، بل عند فشل أو ضعف الجودة أو الحالات التي تحتاج معالجة إضافية.

## Rule 6 — Semantic Segmentation طبقة مستقلة

التقسيم إلى Unit / Lesson / Section لا يجب أن يلوث Extraction Layer.

## Rule 7 — الاستئناف جزء من التصميم

المستندات الكبيرة يجب أن تدعم checkpoint/resume بدل إعادة العمل من الصفر.

---

# 31. الحالة الحالية للمشروع

```text
Phase: ANALYZE / DESIGN
```

تم الاتفاق مبدئيًا على:

- هدف المشروع
- أنواع الملفات للإصدار الأول
- محركات PDF
- معالجة الصور
- OCR الأساسي والاحتياطي
- Quality Gate
- FastAPI
- Redis + RQ
- SQLAlchemy + PostgreSQL
- Storage Abstraction
- Configuration
- Retry
- Testing
- Document Model كمحور للنظام
- Markdown Renderer
- Hierarchy Detection كمفهوم
- Semantic Segmentation كمفهوم
- Unit / Lesson output
- Metadata غنية
- استقلال المشروع عن EduAssist

**لم يبدأ التنفيذ البرمجي بعد.**

---

# 32. الخطوة التالية

الخطوة التالية المتفق عليها هي:

## تصميم Document Model بالتفصيل

قبل إنشاء هيكل المجلدات وقبل كتابة الكود، نحدد:

1. كيان `Document`
2. كيان `Page`
3. كيان `Block`
4. أنواع الـBlock
5. `Unit`
6. `Lesson`
7. `Section`
8. `Table / Row / Cell`
9. `Asset`
10. Metadata
11. العلاقات بين هذه الكيانات
12. ما الذي يأتي من Extraction وما الذي ينتج من Structure Detection
13. ما الذي يعتبر مصدر الحقيقة داخل Document Model
14. كيف يحتفظ النموذج بمعلومات المصدر والصفحات والإحداثيات وconfidence

بعد تثبيت ذلك فقط ننتقل إلى:

```text
Document Model
      ↓
Architecture
      ↓
Folder Structure
      ↓
Interfaces
      ↓
Implementation
```

---

# 33. مرجع سريع للمحادثة

الفكرة الأساسية للمشروع في جملة واحدة:

> **محرك مستقل يحول المستندات الخام إلى Document Model منظم، ثم إلى Markdown وMetadata، مع OCR وLayout Detection وSemantic Segmentation، بحيث يمكن تقسيم الكتب إلى Units/Lessons دون ربط المحرك بأي نظام مستهلك مثل EduAssist.**

المبدأ الأهم:

> **استخراج الحقيقة أولًا، فهم البنية ثانيًا، التقسيم الدلالي ثالثًا، والإخراج أخيرًا.**

