# Document Conversion Engine — Backend

## الإعداد

```powershell
uv sync --locked
```

## التشغيل

```powershell
uv run uvicorn app.main:app --reload
```

من جذر المشروع، شغّل `./validate.ps1` للتحقق الكامل من الباك.

## هيكل الاختبارات

الاختبارات مقسمة إلى ملفين فقط:

- `tests/test_api.py`: اختبارات HTTP والصحة والتحقق العام والاستجابات.
- `tests/test_core.py`: اختبارات الإعدادات والأخطاء والـlogger.

عند إضافة feature جديدة، أضف اختبارها إلى الملف المناسب بدل إنشاء ملف منفصل لكل حالة.

## توسيع الإعدادات

تتكون إعدادات التطبيق من الحزمة `app/core/config/`:

- `settings.py`: نموذج الإعدادات ومصنعها المؤقت.
- `validators.py`: قواعد تحقق مستقلة للمتغيرات.
- `__init__.py`: الواجهة العامة للحزمة.

يرث أي مكوّن إعداداته من `app.core.config.Settings` ثم يمرر الصنف الجديد إلى `get_settings`:

```python
class StorageSettings(Settings):
    storage_dir: Path = Path("storage")


settings = get_settings(StorageSettings)
```

بهذا تبقى قواعد البيئة الأساسية في مكان واحد، بينما تضيف الوحدات إعداداتها دون تعديل المصنع الأساسي.

## بنية الأخطاء

توجد أخطاء التطبيق في `app/core/errors/`:

- `codes.py`: الرموز الثابتة التي يستهلكها العملاء.
- `exceptions.py`: الأخطاء المتوقعة مثل `NotFoundError` و`ConflictError`.
- `handlers.py`: تحويل أخطاء التطبيق وFastAPI إلى `ErrorEnvelope` موحّد.

## التحقق من الطلبات

تستخدم FastAPI نموذج Pydantic للتحقق تلقائيًا من `body` و`query` و`path`، ثم تلتقط `core/validation` أخطاء `RequestValidationError` عالميًا وتحولها إلى تفاصيل ثابتة:

```json
{
    "field": "query.limit",
    "message": "...",
    "type": "int_parsing"
}
```

هذا هو البديل الطبيعي لـ`ValidationPipe` في Nest، ولا تحتاج كل route إلى إضافة validator يدوي؛ يكفي تعريف schema أو type صحيح للمدخلات.

## التسجيل

يستخدم الباك `structlog` فوق واجهة `logging` القياسية، لذلك يمكن للكود الحالي الاستمرار في استخدام `logging.getLogger`. كل سجل يذهب إلى الطرفية وإلى ملف JSON دوّار:

```text
logs/app.log
```

يمكن تغيير الإعدادات من البيئة عبر `LOG_FILE` و`LOG_MAX_BYTES` و`LOG_BACKUP_COUNT`. يضاف `request_id` تلقائيًا إلى كل سجل داخل طلب HTTP.

لإضافة خطأ مجال جديد، أنشئ صنفًا يرث من `AppError` داخل `exceptions.py`، وحدد `status_code` و`code` و`default_message` فقط.
