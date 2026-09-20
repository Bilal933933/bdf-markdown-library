# دليل الوكيل: Document Conversion Engine — Backend

> هذا الملف هو تعليمات أي نموذج/وكيل يعمل على الباك. دليل سير عمل OCR اليدوي في `AGENTS.md` الجذري — لا تخلط بينهما.

المراجع الملزمة قبل أي عمل: `backend/docs/DOCUMENTATION.md` (القرارات) و`backend/docs/document-model.md` (الـSchema + خريطة الملفات §9).

---

## 1. المعمارية: الدومينات

```text
backend/app/
├── main.py                  # create_app() فقط — لا منطق هنا
├── core/                    # config / errors / logging / validation (حزم فرعية بواجهات مستقرة)
├── api/
│   ├── router.py            # جذر /api/v1
│   ├── envelopes.py         # عقود HTTP فقط (نجاح/خطأ) — ليست نماذج دومين
│   └── v1/                  # route لكل مورد (health.py ...) — لا ملفات فارغة
├── middleware/              # request_id
├── infrastructure/          # database / redis / storage — تُنشأ كل واحدة في شريحتها
└── domains/
    └── conversion/          # الدومين الجذري (Document نموذج داخله لا دومينًا مستقلًا)
        └── models/          # حقيقة الدومين: نموذج = ملف (انظر §2)
                             # schemas/ وservices/ وpipeline/ لاحقًا عند مسؤولية فعلية
```

ممنوع: `app/services/` و`app/repositories/` و`app/schemas/` العامة، منطق وهمي، مجلدات
استباقية ("قد نحتاجها")، استيراد الدومينات من بعضها. كل مجلد يكتسب وجوده بمسؤولية فعلية.

## 2. قواعد نماذج الدومين (ملزمة)

1. **نموذج واحد = ملف واحد** في `domains/<name>/models/` (`cell.py` و`row.py` منفصلان رغم صغرهما).
2. كل ملف يصرّح في ترويسته: `Required: ... / Optional: ...` مع القيم الافتراضية.
3. الحقول الإلزامية أولًا في تعريف النموذج، الاختيارية آخرًا (`| None = None`).
4. حزمة `models/__init__.py` تعيد تصدير كل شيء (`__all__`) — الاستيراد دائمًا من الحزمة لا من الملفات.
5. أي نموذج جديد = ملف + سطر في `__init__` + صف في خريطة `document-model.md` §9.
6. الاتحاد المميّز (discriminated union) للحمولات + مدقق تطابق `kind/type`.
7. `models/` = حقيقة الدومين، و`schemas/` داخل الدومين = عقود API الداخلة/الخارجة فقط (لا تخلطهما).

## 3. الأدوات والمكتبات

| الطبقة | المكتبة | الحالة |
|---|---|---|
| API | FastAPI / Uvicorn / Pydantic v2 / pydantic-settings | مثبتة |
| Logging | structlog (JSON + ملف دوّار) + ContextVar لـrequest-id | مثبتة |
| اختبار/جودة | pytest / httpx / ruff (E,F,I,UP,B + سطر 100) / mypy | مثبتة (dev) |
| DB | SQLAlchemy + PostgreSQL (محليًا SQLite مؤقتًا مرفوض — القرار: Postgres مباشرة) | تُضاف في شريحة DB |
| مهام | Redis + RQ (الـclient أولًا، بلا سيرفر محلي الآن) | تُضاف في شريحتها |
| PDF | PyMuPDF (أساسي) + pdfplumber (جداول فقط) | تُضاف مع Structure Detection |
| صور | OpenCV + Pillow | تُضاف مع Preprocessing |
| OCR | PaddleOCR (أساسي) + Gemini (fallback مشروط) | تُضاف مع OCR |
| مستندات | python-docx | تُضاف مع DOCX |
| موثوقية | Tenacity (Gemini/الشبكة فقط) | تُضاف مع OCR |

قاعدة: **لا تُعلن تبعية قبل مرحلتها** (`pyproject.toml` فقط ما يُستخدم الآن).

## 4. الأوامر (من `backend/`)

```powershell
uv sync                       # تثبيت
uv run pytest                 # اختبارات
uv run ruff check app tests   # lint
uv run ruff format app tests  # format
uv run mypy app               # types
uv run uvicorn app.main:app --port 8123   # تشغيل (8123: لأن 8000 محجوز)
.\validate.ps1                # من الجذر: sync + pytest + format-check + lint + mypy
```

## 5. العقود الثابتة

- النجاح: `{"data": ..., "meta": {"request_id": ...}}` — الخطأ: `{"error": {"code","message","details","request_id"}}`.
- `X-Request-ID` تُقبل من العميل أو تُولّد؛ تظهر في الترويسة والمغلف والlogs.
- رموز الأخطاء في `core/errors/codes.py` (StrEnum) — لا رموز مبعثرة.
- الإعدادات عبر `get_settings()` فقط — ممنوع `os.getenv` مبعثر. `production + debug=True` مرفوض بالمدقق.

## 6. قواعد العمل

- تصميم (وثيقة) قبل كود؛ كود قبل commit؛ لا commit لأسرار أبدًا (مفاتيح API = حظر دفع من GitHub).
- `.env` محلي فقط. `logs/` و`.venv/` و`__pycache__/` مُتجاهلة.
- الاختبارات بجانب الكود (`tests/test_<domain>.py`) — لا شريحة بلا اختبار.
- أوامر التنفيذ الصريحة فقط ("نفّذ ...") — الاقتراح والمراجعة بلا تنفيذ.
