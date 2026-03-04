import pytest

from app.services.storage import build_key, create_s3_backend


def test_build_key_preserves_extension():
    key = build_key("my_resume.pdf")
    assert key.endswith(".pdf")
    assert len(key) > len(".pdf")


def test_build_key_defaults_to_pdf():
    key = build_key(None)
    assert key.endswith(".pdf")


def test_create_s3_backend_requires_bucket():
    from app.core.config import Settings

    s = Settings(s3_bucket="")
    with pytest.raises(RuntimeError, match="S3_BUCKET"):
        create_s3_backend(s)
