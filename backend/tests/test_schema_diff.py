from src.core.schema_diff import schema_diff, affected_user_keys


def test_detects_removed_and_type_change():
    old = {"a": 1, "b": {"c": "x"}, "z": True}
    new = {"a": "1", "b": {}, "z": True}
    d = schema_diff(old, new)
    assert any("z" not in r for r in d["removed_keys"])  # b.c removed
    assert any(tc["path"].endswith("'a']") for tc in d["type_changes"])


def test_affected_user_keys_picks_up_user_overrides():
    old = {"foo": {"bar": "old"}}
    new = {"foo": {}}
    d = schema_diff(old, new)
    user = {"foo": {"bar": "set-by-user"}}
    assert "foo.bar" in affected_user_keys(user, d)
