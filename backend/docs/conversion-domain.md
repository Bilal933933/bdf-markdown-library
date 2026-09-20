# Conversion Domain — التصميم (V1)

> الدومين الجذري: عملية التحويل من رفع الملف إلى النتيجة.
> `Document` نموذج داخله (`models/document.py`) لا دومينًا مستقلًا.

---

## 1. الكيانات

```text
Conversion
├── id: str
├── source_file: str
├── status: queued | processing | completed | failed
├── progress: 0-100
├── total_pages: int
├── current_page: int
├── error: { code, message } | null
└── checkpoints: PageCheckpoint[]   # مراجع لا نسخ

PageCheckpoint
├── conversion_id: str
├── page_number: int (≥1)
├── status: pending | done | failed
├── method: ExtractionMethod | null
├── quality: float | null
└── attempts: int
```

## 2. دورة الحياة (الحالات المسموحة فقط)

```text
queued ──→ processing ──→ completed
               │    ↺ resume (من checkpoint)
               ↓
            failed ──→ queued (retry: محاولة جديدة)
```

- `completed` نهائية — لا خروج منها.
- **retry ≠ resume**: retry تعيد المهمة إلى `queued` (محاولة جديدة من البداية)؛
  resume تواصل `processing` من آخر `PageCheckpoint` ناجح (الكتاب المتوقف عند صفحة 173).
- `progress` مشتق من checkpoints (`done / total_pages`) — يُحسب لا يُخزّن يدويًا مستقبلًا.

## 3. ما ليس في V1

- أولويات/جدولة RQ (شريحة المهام).
- تخزين النتائج (شريحة Storage).
- جداول DB (شريحة DB — تُشتق من هذا الشكل).
