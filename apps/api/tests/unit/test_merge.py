from app.utils.merge import merge_patch


def test_merge_patch_nested():
    base = {"a": 1, "pending_slot": {"turns_waited": 0, "tool": "search_order"}}
    out = merge_patch(base, {"pending_slot": {"turns_waited": 1}, "b": 2})
    assert out["a"] == 1
    assert out["b"] == 2
    assert out["pending_slot"]["turns_waited"] == 1
    assert out["pending_slot"]["tool"] == "search_order"


def test_merge_patch_delete():
    out = merge_patch({"pending_slot": {"x": 1}}, {"pending_slot": None})
    assert "pending_slot" not in out
