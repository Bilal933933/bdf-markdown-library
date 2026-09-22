from collections.abc import Iterator
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.conversions import get_storage
from app.core.config import Settings
from app.domains.conversion.pipeline.process import process_conversion
from app.domains.conversion.services.conversions import create_conversion
from app.infrastructure.database import (
    Base,
    ConversionRow,
    PageCheckpointRow,
    get_engine,
    get_session_factory,
)
from app.infrastructure.database.session import get_db
from app.infrastructure.storage import LocalStorage
from app.main import app


def build_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_font(fontname="arr", fontfile="C:/Windows/Fonts/arial.ttf")
    page.insert_font(fontname="arb", fontfile="C:/Windows/Fonts/arialbd.ttf")
    page.insert_text((72, 72), "الوحدة الأولى", fontname="arb", fontsize=26)
    page.insert_text(
        (72, 150),
        "المبتدأ اسم مرفوع يقع في أول الجملة والخبر يتمم معناه.",
        fontname="arr",
        fontsize=12,
    )
    return doc.tobytes()


@pytest.fixture()
def processed(tmp_path: Path) -> Iterator[tuple[TestClient, str]]:
    Base.metadata.create_all(get_engine())
    storage = LocalStorage(tmp_path)
    db = get_session_factory()()
    conversion = create_conversion(db, storage, "book.pdf", build_pdf(), Settings())
    process_conversion(conversion.id, db, storage, Settings(gemini_keys="", gemini_api_key=""))
    db.close()

    def override_db() -> Iterator[Session]:
        session = get_session_factory()()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage] = lambda: storage
    try:
        yield TestClient(app), conversion.id
    finally:
        app.dependency_overrides.clear()
        db = get_session_factory()()
        try:
            db.query(PageCheckpointRow).filter_by(conversion_id=conversion.id).delete()
            db.query(ConversionRow).filter_by(id=conversion.id).delete()
            db.commit()
        finally:
            db.close()


def test_download_document_md(processed: tuple[TestClient, str]) -> None:
    http, conversion_id = processed
    response = http.get(f"/api/v1/conversions/{conversion_id}/outputs/document.md")
    assert response.status_code == 200
    assert "text/markdown" in response.headers["content-type"]
    assert "الوحدة الأولى" in response.text


def test_download_unit_metadata_json(processed: tuple[TestClient, str]) -> None:
    http, conversion_id = processed
    response = http.get(f"/api/v1/conversions/{conversion_id}/outputs/units/01/metadata.json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    assert response.json()["title"] == "الوحدة الأولى"


def test_missing_key_and_conversion_return_404(processed: tuple[TestClient, str]) -> None:
    http, conversion_id = processed
    assert http.get(f"/api/v1/conversions/{conversion_id}/outputs/nope.md").status_code == 404
    assert http.get("/api/v1/conversions/unknown/outputs/document.md").status_code == 404
    traversal = http.get(f"/api/v1/conversions/{conversion_id}/outputs/../input.pdf")
    assert traversal.status_code in (404, 400)
