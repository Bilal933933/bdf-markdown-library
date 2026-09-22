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

## 6.5 عقد OCR V1 (مثبت)

- الموقع: `app/domains/conversion/ocr/` (بروتوكول `OCRProvider` + مزودان + اختيار).
- `OCRResult`: `{text, confidence?, method}` — نص فقط في V1 (الصناديق لربط العامل لاحقًا).
- الاختيار `ocr_page_text(image, mime, page_number, settings)`: Paddle أولًا (إن ثُبّت) ← قبول عبر `analyze_page` (صفحة بفقرة واحدة) ← وإلا Gemini.
- Gemini: REST مباشر (`httpx`) بنفس اتفاق `_ocr` (مفاتيح `GEMINI_KEYS`/`GEMINI_API_KEY`، دوران النماذج عند 429/503، `PROMPT` قصير، `RECITATION` ← خطأ لا نص).
- Tenacity لأخطاء الشبكة فقط (مهلة/اتصال) — الحصص تُدوَّر لا تُعاد.
- المفاتيح في `backend/.env` المحلي فقط (لا تُدفع أبدًا)؛ الاختبارات بـmocks بلا شبكة.
- paddleocr ليس تبعية معلنة بعد (أوزانه ضخمة — يُثبت مع مرحلة الأوزان)؛ `PaddleProvider` يعمل عند توفره.
- نتيجة التحقق الحي (Windows): الحزمة والنماذج العربية تنزل وتعمل حتى الاستدلال، ثم ينهار `paddlepaddle` داخل oneDNN (`ConvertPirAttribute2RuntimeAttribute` — عدم توافق البناء). القرار: Gemini هو OCR العامل هنا؛ Paddle لبيئة Linux/Docker لاحقًا.
- ربط العامل (تصيير الصفحة + صناديق الكتل) تم للنص (V1)؛ صناديق OCR الدقيقة مؤجلة.

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

## 7.2 عقد الـAnalyzer (V1 — مثبت)

- الموقع: `app/domains/conversion/quality/analyzer.py` (دالة صرفة، بلا IO).
- مستوى العمل: `Page` فقط (هي وحدة الـresume والجودة حسب `document-model.md` §1.2).
- الدوال:
  - `analyze_page(page) -> QualityResult` — درجة وقرار وأسباب.
  - `QualityResult`: `{score: 0-1, decision: accept|retry|gemini, reasons: str[]}`.
  - `QualityDecision`: `ACCEPT | RETRY | GEMINI`.
- الحساب (V1، العتبات قابلة للضبط):
  - نص مفيد `l < 20` حرفًا ← `score=0` وقرار `retry` (فارغة أو قصيرة جدًا).
  - جزاء أحرف التحكم/الاستبدال (نسبة لطول النص، سقف 0.6).
  - جزاء انخفاض العربية عن 0.5 (سقف 0.4) — يُحسب خارج كتل `code`.
  - جزاء التكرار (كلمات فريدة/كلية < 0.6 مع 10+ كلمات، سقف 0.5).
  - القرار: `score ≥ 0.75` قبول، `≥ 0.45` إعادة، وإلا `gemini`.
- المؤجل: قاموس الكلمات غير الصالحة، ترتيب الأسطر، جودة الجداول (تُضاف عند حاجة فعلية).

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

## 11.1 عقد الـHierarchy (V1 — مثبت)

- الموقع: `app/domains/conversion/pipeline/hierarchy.py` (دالة صرفة، بلا IO).
- الدالة: `normalize_heading_levels(doc) -> Document` — نسخة جديدة، المدخل لا يُمس.
- القاعدة: `new = min(level, prev+1)` بترتيب المستند (`prev` يبدأ 0، فأول عنوان يصبح 1).
- الغرض: إصلاح قفزات `level` من الكشف المحلي لكل صفحة (مثل `1 ← 3`).
- سقف 6 محفوظ تلقائيًا (المدخل محقق أصلًا 1-6).
- المؤجل: بناء `Unit/Lesson` (طبقة Segmentation لاحقًا).

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

## 12.1 عقد الـSegmentation (V1 — مثبت)

- الموقع: `app/domains/conversion/pipeline/segment.py` (دالة صرفة، بلا IO).
- الدالة: `segment_document(doc) -> Document` — نسخة جديدة بـ`units` مملوءة، المدخل لا يُمس.
- القواعد (على مستويات مُطبّعة من `hierarchy`):
  - عنوان 1 ← `Unit` (مؤكد، العنوان نصه، ثقة 1.0)؛ عنوان 2 ← `Lesson`؛ عنوان 3+ ← `Section`.
  - الكتل تلحق بالقسم الحالي (أو قسم مجهول بلقطة فارغة إن سبقت أي عنوان فرعي).
  - محتوى قبل أول عنوان ← `Unit` بحالة `unknown_section` (تطبيق Rule 1).
  - بلا عناوين إطلاقًا ← وحدة/درس/قسم واحد مجهول يحوي كل الكتل.
  - `page_range` مشتق من `source.pages` للكتل المرجعية (أدنى/أقصى)؛ لا صفحات ← `None`.
  - `block_refs` مراجع لمعرفات حقيقية فقط — لا نسخ نصوص.
- غير موصول بالعامل بعد (مخرجات الوحدات/الدروس §18 شريحة لاحقة).

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
Code → ```
```

مع مراعاة المحتوى العربي وRTL — من اليمين إلى اليسار.

## 17.1 عقد الـRenderer (V1 — مثبت)

- الموقع: `app/domains/conversion/rendering/markdown.py` (دالة صرفة، بلا IO).
- الدوال:
  - `render_block(block, assets_by_id) -> str` — تحويل Block واحد.
  - `render_document(doc, assets_by_id=None) -> str` — الصفحات مرتبة برقمها، والـBlocks مرتبة بـ`order`، وتُفصل الكتل بسطر فارغ.
  - `collect_stats(doc) -> ContentStats` — إحصاء مشتق عند الإخراج (لا يُخزن يدويًا).
- القواعد:
  - `heading`: `"#" * level + " " + text` (مستوى 1-6 من النموذج).
  - `paragraph`: النص كما هو.
  - `list`: غير مرتبة `- ` ومرتبة `1. ` بترقيم مستمر لكل مستوى، والإزاحة `"  " * level`.
  - `table`: الصف الأول ترويسة دائمًا (Markdown يتطلبها)؛ `|` تُهرب كـ`\|`؛ إن وجد `fallback_image` أُلحق سطر `![](key)` بعده.
  - `image`: `![alt](storage_key أو asset_id)` مع سطر `*caption*` إن وجد؛ لا base64 أبدًا.
  - `quote`: كل سطر يبدأ بـ`> ` مع سطر `— attribution` إن وجد.
  - `code`: كتلة مسيجة ```` ``` ```` مع اللغة إن وجدت.
  - لا اختراع: نص فارغ أو جدول بلا صفوف يُسقط بصمت؛ لا عناوين مولدة.

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

## 18.2 عقد مخرجات الوحدات (V1 — مثبت)

- الباني: `build_unit_outputs(doc, assets_by_id=None) -> dict[key, bytes]` في `rendering/units.py` (صرف، والـWorker يحفظ).
- المفاتيح تحت `{id}/output/`: `units/{UU}/metadata.json` (تفريغ `Unit`)، ولكل درس له مراجع: `units/{UU}/lessons/{LL}/content.md` + `metadata.json` (تفريغ `Lesson`).
- الترقيم `02d` حسب الترتيب؛ `content.md` = كتل الدرس بترتيب المستند عبر `render_block`.
- درس بلا مراجع يُسقط (لا ملف فارغ)؛ وحدة بلا دروس تُخرج `metadata.json` فقط.
- `assets/` لكل درس مؤجلة (الصور تُشار بمسار التخزين كما في `document.md`).
- الصور V1: كتلة `image` لكل صورة مدمجة (`asset_id` حتمي `pN-imgI` + `bbox`) بطريقة `pymupdf`؛ العامل يحفظ البايتات في `output/assets/` ويثبت سجل `Asset` (الأبعاد والmime والصفحات) في `output/assets.json`؛ المراجع في Markdown تعمل عبر مسار التنزيل.
- قيد صادق: صور صفحات OCR تُسقط (لا قصّ من التصيير بعد) — نصها يُستخرج وصورها لا.
- العامل يستدعي `segment_document` قبل البناء، فيُخرج أي تحويل ناجح له عناوين مخرجات الدروس تلقائيًا.

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

## 19.4 Conversions endpoints (V1 — مثبت)

- `POST /api/v1/conversions` (ملف واحد `multipart`) ← `202` + `Conversion` (مغلّف نجاح).
- `GET /api/v1/conversions/{id}` ← `200` + `Conversion`، أو `404` (`NOT_FOUND`).
- نطاق V1: ملفات PDF وDOCX وTXT وصور PNG/JPG/WebP (امتداد + بصمة) — WebP تُطبّع PNG عبر Pillow عند المعالجة.
- DOCX/TXT/الصورة صفحة منطقية واحدة (`total_pages=1`)؛ الصورة تدخل مسار OCR مباشرة (بلا طبقة نصية).
- DOCX/TXT صفحة منطقية واحدة (`total_pages=1`)؛ الاستخراج في `extract/`:
  - DOCX: `Heading N` ← عنوان، `List Bullet/Number` ← قائمة، الجداول ← `Table`، الباقي فقرات (`method=docx`).
  - TXT: فقرات مقسمة على الأسطر الفارغة (`utf-8-sig` ثم `cp1256`) (`method=text`).
- العامل يفرّع على الامتداد: PDF المسار الحالي، وغيره بناء الكتل مباشرة ثم نفس البوابة والتجميع.
- الحدود من الإعدادات: `max_file_size` (افتراضي 100MB) و`max_pages` (افتراضي 2000) — التجاوز `422` (`VALIDATION_ERROR`).
- التدفق: فحص الحجم ← عدّ الصفحات (`PyMuPDF`) ← حفظ `{id}/input.pdf` في `Storage` ← صف `conversions` + صفوف `page_checkpoints` (`PENDING`) ← الحالة `queued`.
- الاستجابة هي نموذج الدومين `Conversion` نفسه (لا schemas مكررة).
- الـPOST يُحاول `enqueue` في طابور `conversions`؛ عند غياب Redis يبقى التحويل `queued` (§20.1).

## 19.5 تنزيل المخرجات (V1 — مثبت)

- `GET /api/v1/conversions/{id}/outputs/{key}` — أي ملف تحت `{id}/output/` (`document.md`، `metadata.json`، `units/...`).
- الأنواع: `.md` ← `text/markdown`، `.json` ← `application/json`، غيرهما ← `application/octet-stream`.
- التحويل المجهول أو المفتاح المفقود/غير الآمن ← `404` (لا تسريب)؛ المفتاح يُحل داخل نطاق التحويل فقط.

## 19.6 المصادقة (V1 — مثبت)

- حارس `X-API-Key` على `/api/v1/*` عدا شجرة `/health` (مسابر المراقبة مفتوحة).
- غياب الترويسة ← `401 UNAUTHORIZED`؛ مفتاح خاطئ ← `403 FORBIDDEN` (مقارنة ثابتة الزمن).
- المفاتيح من `API_KEYS` (فواصل)؛ بلا مفاتيح مضبوطة ← مفتوح (تطوير فقط — خطر إنتاج موثق).
- الحدود: بلا تدوير ديناميكي للمفاتيح (شريحة لاحقة).

## 19.7 مسابر الصحة (V1 — مثبت)

- `GET /api/v1/health/live` ← `200` دائما (الحياة).
- `GET /api/v1/health/ready` ← `200` وقاعدة البيانات `up`، وإلا `503` (الجاهزية — Redis خارجها لأن القيد يعمل بدونه).
- `GET /api/v1/health/detailed` ← `200` دائما: `db` و`redis` (`up/down`) و`queue_depth` (عدد طابور `conversions` أو `null`) و`app`/`env` (بلا أسرار).
- الكل بمغلفات `envelopes.py` (نجاح/خطأ) — لا صيغ أجنبية.

## 19.8 CORS والقائمة (V1 — مثبت)

- `CORS_ORIGINS` (فواصل) — فارغ يعني بلا CORS (نفس الأصل فقط)؛ مملوء يعني سماحا بتلك الأصول مع ترويسة `X-API-Key` وكشف `X-Request-ID`.
- `GET /api/v1/conversions?limit&offset` ← الأحدث أولا (`created_at` — ترحيل `0003`)، `limit` بين 1-100 (افتراضي 20).
- حد المعدل V1: نافذة ثابتة 60 ثانية لكل هوية (المفتاح أو IP) من `RATE_LIMIT_PER_MINUTE` (افتراضي 60، صفر يعطل) — التجاوز `429 RATE_LIMITED`؛ `/health` مستثناة؛ ذاكرة العملية فقط (عامل واحد).
- الأدوار V1: لاحقة المفتاح `:read` للقراءة فقط (GET مسموح، والكتابة `403`)؛ بلا لاحقة = كامل.

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

## 20.1 عقد الـWorker (V1 — مثبت)

- الدالة: `process_conversion(conversion_id, db, storage)` في `pipeline/process.py` (قابلة للاختبار بلا Redis).
- مدخل RQ: `process_conversion_job(conversion_id)` يبني الجلسة والتخزين من الإعدادات.
- الطابور `"conversions"`؛ الـPOST يُحاول الـenqueue وأي فشل يُبقي التحويل `queued` (يُسحب لاحقًا).
- حلقة الصفحة: `detect_blocks` ← قبول؟ ← وإلا تصيير الصفحة (`×2`) و`ocr_page_text` (Paddle/Gemini) ← بناء فقرات من النص ← `analyze_page` ← حفظ `{id}/pages/{n}.json` ← checkpoint (`DONE` + الطريقة والجودة) — commit بعد كل صفحة.
- المحاولات: حتى 3 لكل صفحة (الأولى نصية، ثم OCR) ثم `FAILED`؛ أي صفحة `FAILED` ← التحويل `FAILED` (رمز `PAGE_FAILED`).
- النجاح: تجميع `Document` ← `normalize_heading_levels` ← `render_document` ← حفظ `output/document.md` و`output/metadata.json` ← `COMPLETED` بتقدم 100.
- عامل واحد في V1؛ عند الإقلاع يستدعي `requeue_orphans` (إيجار 300 ثانية على `heartbeat_at` — ترحيل `0002`).
- الدخول: `python -m app.worker` (يستمع على `conversions`).
- سيرفر dev المحلي: نسخة Windows الأصلية (Redis 5 — العميل مثبت على `protocol=2` لانعدام `HELLO`) على `6379`؛ الرابط في `backend/.env` (`REDIS_URL`)؛ المرجع الوظيفي للمهام `module.attr` بالنقاط (RQ 2.x).

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

## 21.1 ترحيلات Alembic (مثبت)

- القرار المثبت فوقه يُستبدل: **Postgres مباشرة** (يُرفض SQLite في الإعدادات والاختبارات).
- الجداول تُدار بـAlembic (`backend/alembic/`) لا `create_all` في الإنتاج:
  - `uv run alembic upgrade head` — بيئة جديدة.
  - `uv run alembic stamp head` — قاعدة dev أُنشئت جداولها سابقًا بـ`create_all`.
  - `uv run alembic revision --autogenerate -m "..."` — أي جدول/عمود جديد.
- `env.py` يأخذ الرابط من `Settings` (يفشل بوضوح بلا `DATABASE_URL`)؛ الاختبار يولد SQL دون اتصال.

---

# 22. Storage (مثبت)

**Storage Abstraction — طبقة تخزين مجردة** ببروتوكول واحد يعتمد عليه الـPipeline:

```text
save(key, data) -> key / load(key) -> bytes / delete(key) / exists(key) -> bool
```

- المفاتيح مسارات منطقية (`/` فقط، بلا التباس بنظام الملفات).
- تخطيط المفاتيح لكل تحويل:

```text
{conversion_id}/input.<ext>
{conversion_id}/pages/{n}.json      # كتل الصفحة — حبيبية الاستئناف
{conversion_id}/assets/{asset_id}
{conversion_id}/output/document.md
{conversion_id}/output/metadata.json
```

- البداية: نظام ملفات محلي تحت `STORAGE_DIR` (كتابة ذرية `temp + rename`)، بلا تبعية جديدة.
- لاحقًا: `S3`/`MinIO` يطبقان نفس البروتوكول — الـPipeline لا يتغير.
- لا يُخزن: ردود OCR الخام (قابلة لإعادة الاشتقاق)، ولا `base64` داخل النماذج.
- الموقع في الكود (شريحة التنفيذ): `app/infrastructure/storage/`.

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

# 27. Task Lifecycle (مثبت)

الحالات (`ConversionStatus` — الانتقالات محكومة بـ`transition_to`):

```text
queued → processing → completed
                    ↘ failed → queued (إعادة قيد فقط)
                    ↘ partial → queued (استئناف الناقص)
```

## 27.1 إجابات الأسئلة الستة

- **أين الحالة؟** قاعدة البيانات (`Conversion` مصدر الحقيقة)؛ Redis يحمل `conversion_id` فقط.
- **الـprogress؟** مشتق: `round(100*done/total)` (صفر إن `total=0`)؛ `current_page` = آخر صفحة حاولها العامل.
- **الأخطاء؟** `Conversion.error` = أول خطأ قاتل `{code,message}` (الرموز من `core/errors/codes.py`)؛ وإخفاقات الصفحات في checkpoints.
- **الاستئناف؟** صف `PageCheckpoint` لكل صفحة عند القيد (`PENDING`)؛ العامل يتخطى `DONE` ويكمل من أول غير-`DONE` — لا إعادة من الصفر أبدًا.
- **عند إعادة تشغيل العامل؟** تحويلات `PROCESSING` بنبض أقدم من 300 ثانية (أو بلا نبض) تُعاد `QUEUED` عبر `requeue_orphans` — لا مساس بتحويل يعمل عليه عامل حي.
- **retry مقابل resume؟** `retry` = إعادة نفس الصفحة بنفس الطريقة (`attempts+1`، وTenacity لـGemini/الشبكة فقط)؛ `resume` = المتابعة من checkpoints بعد توقف.

## 27.2 قواعد الإكمال

- `COMPLETED` إذا كل الصفحات `DONE` (مع `method` و`quality` مسجلين).
- صفحات `DONE` وأخرى استنفدت محاولاتها (سقف V1: 3) ← `PARTIAL` مع تسمية الصفحات في `error` — والمخرجات تُبنى من الناجح فقط (أرقام الصفحات الأصلية محفوظة).
- بلا أي صفحة `DONE` ← `FAILED` (لا شيء يُخرج).
- إعادة قيد `PARTIAL` (كالفاشل) تستأنف من checkpoints؛ اكتمال اللاحق ← `COMPLETED` ويمسح الخطأ.
- فحصا `MAX_FILE_SIZE` و`MAX_PAGES` عند القيد، من الإعدادات.

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

حُسم في §22 و§27:

```text
queued → processing → completed
                    ↘ failed → queued
```

التفاصيل المثبتة: `checkpoint` لكل صفحة، `resume` من أول غير-`DONE`،
`retry` للصفحة مقابل `resume` للتحويل، `progress` مشتق، استرداد اليتيم
المشروط بالنبض (انتقال `processing→queued` + عمود `heartbeat_at`).

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

**بدأ التنفيذ البرمجي (تحديث):** نماذج `conversion` كاملة (`document-model.md` §9)،
`pipeline/structure.py` (كشف مبدئي)، `rendering/markdown.py` (§17.1)،
`quality/analyzer.py` (§7.2)، `pipeline/hierarchy.py` (§11.1) — كل شريحة بوثيقة ثم كود واختبار.

---

# 32. الخطوة التالية (تحديث)

اكتمل تصميم `Document Model` (`document-model.md` V1) وتنفيذه.
الخطوة التالية هي شريحة كود `Storage` المحلي (`§22`):

```text
وثيقة Storage/Task Lifecycle (تمت)
      ↓
infrastructure/storage/ + اختبار
      ↓
Conversion API (رفع/حالة)
      ↓
OCR + Segmentation
```

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

