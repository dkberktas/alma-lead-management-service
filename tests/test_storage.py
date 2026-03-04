import pytest

from app.services.storage import build_key, get_storage_backend


def test_build_key_preserves_extension():
    key = build_key("my_resume.pdf")
    assert key.endswith(".pdf")
    assert len(key) > len(".pdf")


def test_build_key_defaults_to_pdf():
    key = build_key(None)
    assert key.endswith(".pdf")


def test_get_storage_backend_s3_requires_bucket():
    from app.core.config import Settings

    s = Settings(storage_backend="s3", s3_bucket="")
    with pytest.raises(RuntimeError, match="S3_BUCKET"):
        get_storage_backend(s)
