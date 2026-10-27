import numpy as np
import pytest
import requests
from app.src.hosted_inference import HostedModel


def test_hosted_model_preserves_thresholds_and_response(monkeypatch):
    model = HostedModel("example/1", "private-test-key")
    result = {"image": {"width": 32, "height": 32}, "predictions": []}
    def post(url, **kwargs):
        assert url == "https://detect.roboflow.com/example/1"
        assert kwargs["params"] == {"api_key": "private-test-key", "confidence": 10, "overlap": 50}
        assert kwargs["data"]
        return type("Response", (), {"status_code": 200, "json": lambda self: result})()
    monkeypatch.setattr(model.session, "post", post)
    assert model.infer(np.zeros((32, 32, 3), dtype=np.uint8)) == [result]


def test_hosted_errors_do_not_expose_credentials(monkeypatch):
    model = HostedModel("example/1", "private-test-key")
    def post(*args, **kwargs):
        raise requests.ConnectionError("https://example.com?api_key=private-test-key")
    monkeypatch.setattr(model.session, "post", post)
    with pytest.raises(RuntimeError) as error:
        model.infer(np.zeros((32, 32, 3), dtype=np.uint8))
    assert "private-test-key" not in str(error.value)
