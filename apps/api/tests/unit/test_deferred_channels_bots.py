"""Deferred PRD: WeCom/DingTalk parse, i18n, bots, sandbox, attachments."""

from __future__ import annotations

import base64
import hashlib
import hmac

import pytest

from app.services.bots.profiles import get_bot, list_bots
from app.services.channels.dingtalk.service import DingTalkService
from app.services.channels.wecom.service import WeComService
from app.services.chat.attachments import normalize_attachments
from app.services.i18n.messages import t
from app.services.sandbox.guard import require_sandbox, sandbox_allowed
from app.services.agent.reasoning import reasoning_allowed_for_intent, reasoning_extra_steps
from app.plugins.manifest import resolve_features


def test_wecom_parse_text_and_image():
    svc = WeComService(db=None)  # type: ignore[arg-type]
    assert svc.parse_message({"MsgType": "text", "FromUserName": "u1", "Content": "hello"}) == (
        "u1",
        "hello",
    )
    img = svc.parse_message({"MsgType": "image", "FromUserName": "u1", "MediaId": "m99"})
    assert img is not None
    assert img[0] == "u1"
    assert "attachment" in img[1]


def test_wecom_url_verify_token():
    from app.core.config import get_settings

    get_settings.cache_clear()
    import os

    os.environ["WECOM_TOKEN"] = "tok"
    get_settings.cache_clear()
    svc = WeComService(db=None, settings=get_settings())  # type: ignore[arg-type]
    ts, nonce, echo = "1", "n", "echo"
    items = sorted(["tok", ts, nonce, echo])
    sig = hashlib.sha1("".join(items).encode()).hexdigest()
    assert svc.verify_url(msg_signature=sig, timestamp=ts, nonce=nonce, echostr=echo) == echo
    os.environ.pop("WECOM_TOKEN", None)
    get_settings.cache_clear()


def test_dingtalk_sign_and_parse():
    from app.core.config import get_settings
    import os

    os.environ["DINGTALK_APP_SECRET"] = "sec"
    get_settings.cache_clear()
    svc = DingTalkService(db=None, settings=get_settings())  # type: ignore[arg-type]
    ts = "1710000000000"
    string_to_sign = f"{ts}\nsec"
    digest = hmac.new(b"sec", string_to_sign.encode(), hashlib.sha256).digest()
    sign = base64.b64encode(digest).decode()
    assert svc.verify_sign(ts, sign) is True
    parsed = svc.parse_message(
        {"text": {"content": "  退货  "}, "senderStaffId": "staff1", "conversationId": "c1"}
    )
    assert parsed == ("staff1", "退货")
    os.environ.pop("DINGTALK_APP_SECRET", None)
    get_settings.cache_clear()


def test_i18n_en_and_zh():
    assert "无法确信" in t("refuse.weak", "zh-CN")
    assert "cannot answer" in t("refuse.weak", "en-US").lower()


def test_bot_profiles_default_and_json(monkeypatch):
    monkeypatch.setenv(
        "BOT_PROFILES_JSON",
        '[{"id":"sales","name":"Sales","knowledge_tags":["sales"],"locale":"en-US"}]',
    )
    from app.core.config import get_settings

    get_settings.cache_clear()
    bots = list_bots()
    ids = {b["id"] for b in bots}
    assert "default" in ids
    assert "sales" in ids
    sales = get_bot("sales")
    assert sales.knowledge_tags == ["sales"]
    monkeypatch.delenv("BOT_PROFILES_JSON", raising=False)
    get_settings.cache_clear()


def test_attachments_normalize():
    out = normalize_attachments(
        [{"kind": "image", "name": "a.png", "url": "https://x/a.png"}, {"kind": "evil"}]
    )
    assert len(out) == 2
    assert out[0]["kind"] == "image"
    assert out[1]["kind"] == "file"


def test_sandbox_default_off(monkeypatch):
    monkeypatch.delenv("SANDBOX_ENABLED", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()
    assert sandbox_allowed() is False
    with pytest.raises(RuntimeError, match="sandbox_disabled"):
        require_sandbox()


def test_reasoning_default_off(monkeypatch):
    monkeypatch.delenv("REASONING_ENABLED", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()
    assert reasoning_allowed_for_intent("product_faq") is False
    assert reasoning_extra_steps("product_faq") == 0
    monkeypatch.setenv("REASONING_ENABLED", "1")
    get_settings.cache_clear()
    assert reasoning_allowed_for_intent("product_faq") is True
    assert reasoning_extra_steps("product_faq") >= 1
    monkeypatch.delenv("REASONING_ENABLED", raising=False)
    get_settings.cache_clear()


def test_full_profile_includes_wecom_dingtalk():
    feats = resolve_features("full", None)
    assert "wecom" in feats
    assert "dingtalk" in feats
    assert "feishu" in feats


def test_core_only_excludes_im_channels():
    feats = resolve_features("core-only", None)
    assert "wecom" not in feats
    assert "dingtalk" not in feats
