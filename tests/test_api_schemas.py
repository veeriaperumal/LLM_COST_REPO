# ---------------------------------------------------------------------------
# test_api_schemas.py — Unit tests for the response envelope builders
# ---------------------------------------------------------------------------

from app.api.schemas import ApiError, ApiMeta, ApiResponse, fail, ok


def test_ok_shape():
    """ok() produces a success envelope with data and no error."""
    resp = ok({"model": "gpt-4o"})
    assert isinstance(resp, ApiResponse)
    assert resp.success is True
    assert resp.data == {"model": "gpt-4o"}
    assert resp.error is None
    assert isinstance(resp.meta, ApiMeta)
    assert resp.meta.timestamp  # non-empty ISO timestamp


def test_ok_no_data():
    """ok(None) is valid — data defaults to None."""
    resp = ok()
    assert resp.success is True
    assert resp.data is None


def test_fail_shape():
    """fail() produces an error envelope with structured error info."""
    resp = fail("NOT_FOUND", "Model not found", {"model_id": "x"})
    assert resp.success is False
    assert resp.data is None
    assert isinstance(resp.error, ApiError)
    assert resp.error.code == "NOT_FOUND"
    assert resp.error.message == "Model not found"
    assert resp.error.details == {"model_id": "x"}


def test_request_id_empty_outside_request():
    """Outside any HTTP request the meta request_id is an empty string."""
    assert ok().meta.request_id == ""