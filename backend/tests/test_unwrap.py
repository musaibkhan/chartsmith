from src.core.unwrap import detect_wrapper, unwrap_values

UPSTREAM = {"deploymentMode": "x", "loki": {}, "gateway": {}, "ingester": {}}


def test_detect_argocd_wrapper():
    user = {"loki": {"deploymentMode": "Distributed", "gateway": {}, "ingester": {}}}
    assert detect_wrapper(user, UPSTREAM) == "loki"


def test_no_wrapper_when_keys_overlap():
    user = {"deploymentMode": "x", "gateway": {}}
    assert detect_wrapper(user, UPSTREAM) is None


def test_unwrap_strips_prefix():
    yaml_text = "loki:\n  deploymentMode: Distributed\n  gateway: {}\n"
    out = unwrap_values(yaml_text, "loki")
    assert out == {"deploymentMode": "Distributed", "gateway": {}}
