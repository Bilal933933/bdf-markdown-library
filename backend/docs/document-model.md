# Document Model — التصميم المفصّل (V1)

> مرجع §8 و§32 من `DOCUMENTATION.md`. هذه الوثيقة هي مصدر الحقيقة للـSchema.
> القاعدة الحاكمة: **استخراج الحقيقة أولًا، فهم البنية ثانيًا، التقسيم الدلالي ثالثًا.**

---

## 1. الكيانات الأساسية

```text
Document
├── metadata: DocumentMetadata
├── pages: Page[]
├── units: Unit[]          # تُبنى في طبقة Segmentation لاحقًا (Rule 6) — فارغة بعد الاستخراج
└── assets: Asset[]
```

### 1.1 Document

| الحقل | النوع | إلزامي | المصدر |
|---|---|---|---|
| `id` | str (slug أو uuid) | نعم | مولّد عند الإدخال |
| `source_file` | str | نعم | المدخل |
| `metadata` | DocumentMetadata | نعم | استخراج + إدخال |
| `pages` | Page[] | نعم | Extraction |
| `units` | Unit[] | نعم (قد تكون فارغة) | Segmentation |
| `assets` | Asset[] | نعم (قد تكون فارغة) | Extraction |

### 1.2 Page — كيان مستقل (قرار §32/2)

`Page` كيان مستقل لا مجرد حاوية، لأن الـresume والـQuality Gate يعملان على مستوى الصفحة.

| الحقل | النوع | إلزامي | ملاحظة |
|---|---|---|---|
| `number` | int (يبدأ من 1) | نعم | هو المعرّف داخل المستند |
| `width` / `height` | float | لا | نقاط PDF أو بكسل الصورة |
| `blocks` | Block[] | نعم | مرتبة بـ`order` صريح |
| `quality` | float 0-1 | لا | من Quality Gate |
| `extraction_method` | str | لا | `pymupdf` / `paddleocr` / `gemini` ... للصفحة ككل |

### 1.3 Block

| الحقل | النوع | إلزامي | ملاحظة |
|---|---|---|---|
| `id` | str (`p{page}-b{order}` لحظة الاستخراج) | نعم | ثابت لا يتغير بعد الإنشاء — حتى لو أُعيد حساب `order` |
| `type` | BlockType | نعم | حرفي V1 أدناه |
| `order` | int | نعم | **صريح وقابل لإعادة الحساب عند الدمج** — الترتيب لا يُستنتج من المصفوفة (قرار §32) |
| `source` | BlockSource | نعم | التتبع (§4) |
| payload | حسب النوع | نعم | §1.4 |

`BlockType` في V1 (حرفي مغلق — الامتداد §2.3):

```text
heading | paragraph | list | table | image | quote | code
```

### 1.4 حمولات الأنواع (payload)

**heading**: `{ "level": 1-6, "text": str }`
**paragraph**: `{ "text": str }`
**list**: `{ "ordered": bool, "items": [{ "text": str, "level": int }] }` — `level` يدعم القوائم المتداخلة.
**table**: `Table` (§3).
**image**: `{ "asset_id": str, "alt": str, "caption": str | null }` — المحتوى في `assets` لا في الـBlock.
**quote**: `{ "text": str, "attribution": str | null }`
**code**: `{ "language": str | null, "text": str }`

---

## 2. البنية التعليمية (تُبنى لاحقًا — مخططها مثبت الآن)

```text
Unit
├── id, title
├── page_range: [start, end]
├── status: confirmed | unknown_section
├── confidence: float
└── lessons: Lesson[]
    ├── id, title
    ├── page_range, status, confidence
    └── sections: Section[]
        ├── heading_snapshot: str
        ├── block_refs: str[]   # مراجع لمعرفات Blocks — لا نسخ
        └── ...
```

- `block_refs` مراجع لا نسخ: النص مصدر حقيقته Blocks الصفحات (§5).
- `status: unknown_section` مع `confidence` هو تطبيق Rule 1 — لا اختراع.
- الأنواع الدلالية (`example | exercise | definition | note`): **مؤجلة** — تُضاف كقيم جديدة في `BlockType` عندما تُطلب فعليًا، دون تغيير الهيكل.

---

## 3. الجداول

```text
Table
├── rows: Row[]
│   └── cells: Cell[]
│       ├── text: str
│       ├── header: bool
│       ├── colspan: int = 1
│       └── rowspan: int = 1
├── confidence: float
└── fallback_image: asset_id | null
```

**سياسة الجدول غير الموثوق**: إذا `confidence < threshold` (يُثبت في Quality Gate):

1. يُحفظ النص المستخرج كما هو (لا يُحذف).
2. تُرفق صورة مقتطع الجدول في `fallback_image`.
3. يُوسم `needs_review: true` — والـRenderer يخرجه كجدول + رابط الصورة.

لا جداول متداخلة في V1 (تُعامل كصورة + Gemini عند الحاجة).

---

## 4. التتبع (Provenance) — كل Block

```text
BlockSource
├── file: str              # الملف الأصلي
├── pages: int[]           # عادة صفحة واحدة
├── bbox: [x0, y0, x1, y1] | null   # إلزامي لمخرجات OCR/الصور، اختياري للنص
├── confidence: float | null
├── method: pymupdf | pdfplumber | paddleocr | gemini | tesseract | docx | text
└── needs_review: bool = false
```

### 4.1 مصفوفة الحقل ← المصدر

| الحقل | Extraction | Structure Detection |
|---|---|---|
| نص الفقرات/القوائم | ✓ | — |
| `heading.level` الأولي (حجم/عتبة خط) | ✓ | — |
| تصحيح `heading.level` الهرمي | — | ✓ Hierarchy |
| `table` الخلايا | ✓ (pdfplumber) | — |
| `Unit/Lesson/Section` | — | ✓ Segmentation |
| `order` | ✓ (ترتيب الاستخراج) | يُعاد حسابه عند الدمج |
| `quality/confidence` | — | ✓ Quality Gate |

---

## 5. مصدر الحقيقة

1. **النص المستخرج** (Blocks) هو مصدر الحقيقة — الـMarkdown مشتق يُعاد توليده دائمًا.
2. **الأصول** (`assets`) ملفات خارجية يُشار إليها — لا تُضمّن base64 في النموذج.
3. **الـMetadata المشتقة** (إحصاءات المحتوى) تُحسب عند الإخراج لا تُخزن يدويًا.

---

## 6. إجابات §32 الـ13

1. `Document`: §1.1. 2. `Page`: §1.2 مستقل. 3. `Block`: §1.3 + `order` صريح.
4. الأنواع: §1.4 (V1 مغلق) + §2 (المؤجل). 5-7. `Unit/Lesson/Section`: §2 بمراجع لا نسخ.
8. `Table/Row/Cell`: §3. 9. `Asset`: `{id, kind, storage_key, mime, width, height, pages[]}`.
10. Metadata: §7. 11. العلاقات: §1-§2. 12. المصدر: §4.1.
13. مصدر الحقيقة: §5. 14. الإحداثيات/confidence: §4 (إلزامية للصور/OCR).

---

## 7. Metadata المستند

```text
DocumentMetadata
├── title: str | null
├── subject / grade / stage: str | null   # من الإدخال أو Segmentation — لا تُخترع
├── page_count: int
├── stats: { paragraphs, headings, tables, images, lists, quotes, code }
└── extraction: { methods: str[], ocr_pages: int[], quality: float | null }
```

---

## 8. خارج النطاق في V1

- اكتشاف `Example/Exercise/Definition/Note` (مخطط مؤجل §2).
- الجداول المتداخلة. - `bbox` إلزاميًا لنص PDF (اختياري).
- أي حقل Metadata لا دليل عليه (Rule 1).

---

## 9. خريطة النموذج ← الملفات

قاعدة: نموذج واحد = ملف واحد. كل ملف يصرّح في ترويسته بالحقول الإلزامية والاختيارية.

| النموذج | الملف |
|---|---|
| `BlockType` / `ExtractionMethod` / `UnitStatus` | `app/domains/conversion/models/enums.py` |
| `BBox` / `BlockSource` | `app/domains/conversion/models/source.py` |
| `HeadingPayload` | `app/domains/conversion/models/heading.py` |
| `ParagraphPayload` | `app/domains/conversion/models/paragraph.py` |
| `ListItem` / `ListPayload` | `app/domains/conversion/models/list.py` |
| `Cell` | `app/domains/conversion/models/cell.py` |
| `Row` | `app/domains/conversion/models/row.py` |
| `TablePayload` | `app/domains/conversion/models/table.py` |
| `ImagePayload` | `app/domains/conversion/models/image.py` |
| `QuotePayload` | `app/domains/conversion/models/quote.py` |
| `CodePayload` | `app/domains/conversion/models/code.py` |
| `Block` / `BlockPayload` | `app/domains/conversion/models/block.py` |
| `Page` | `app/domains/conversion/models/page.py` |
| `Asset` | `app/domains/conversion/models/asset.py` |
| `Section` / `Lesson` / `Unit` | `app/domains/conversion/models/structure.py` |
| `ContentStats` / `ExtractionInfo` / `DocumentMetadata` | `app/domains/conversion/models/metadata.py` |
| `Document` | `app/domains/conversion/models/document.py` |
| `Conversion` / `ConversionError` + `ConversionStatus` | `app/domains/conversion/models/conversion.py` + `enums.py` |
| `PageCheckpoint` + `CheckpointStatus` | `app/domains/conversion/models/checkpoint.py` + `enums.py` |
| الواجهة العامة (`__all__`) | `app/domains/conversion/models/__init__.py` |
