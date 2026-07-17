from app.services.audit.masking.mask import mask_detail, mask_string


def test_mask_email_and_password():
    detail = {
        "email": "alice@example.com",
        "password": "supersecret",
        "note": "contact bob@corp.io for token Bearer abc.def.ghi",
    }
    masked = mask_detail(detail)
    assert masked["password"] == "***"
    assert "alice@example.com" not in str(masked)
    assert "***" in masked["email"]
    assert "Bearer ***" in masked["note"] or "***" in masked["note"]


def test_mask_string_phone():
    s = mask_string("call 13800138000 please")
    assert "13800138000" not in s
