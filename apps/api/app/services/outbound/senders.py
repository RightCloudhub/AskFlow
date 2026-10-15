"""Outbound channel senders with per-process token caching (arch §4.1)."""

import json
import time
from collections.abc import Awaitable, Callable

import httpx

from app.core.config import Settings, get_settings
from app.services.outbound.render import CHANNEL_LIMITS

HTTP_TIMEOUT_SEC = 10.0
TOKEN_EXPIRY_SKEW_SECONDS = 60
STATUS_SENT = "sent"
STATUS_NO_TOKEN = "no_token"
HTTP_ERROR_FLOOR = 400
DEFAULT_TOKEN_TTL_SECONDS = 7200

FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
FEISHU_SEND_URL = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
WECOM_TOKEN_URL = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
WECOM_SEND_URL = "https://qyapi.weixin.qq.com/cgi-bin/message/send"
DINGTALK_TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
DINGTALK_SEND_URL = "https://api.dingtalk.com/v1.0/robot/oToMessages/batchSend"

_TOKEN_CACHE: dict[str, tuple[str, float]] = {}

SenderFn = Callable[..., Awaitable[str]]


def _cached_token(key: str) -> str | None:
    entry = _TOKEN_CACHE.get(key)
    if entry is None or entry[1] <= time.time():
        return None
    return entry[0]


def _store_token(key: str, token: str, expires_in: float) -> None:
    ttl = max(expires_in - TOKEN_EXPIRY_SKEW_SECONDS, 0)
    _TOKEN_CACHE[key] = (token, time.time() + ttl)


async def _post(url: str, *, json_payload: dict, headers: dict | None = None) -> httpx.Response:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SEC) as client:
        return await client.post(url, json=json_payload, headers=headers)


async def _get(url: str, *, params: dict) -> httpx.Response:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SEC) as client:
        return await client.get(url, params=params)


def _http_status(response: httpx.Response, *, api_key: str = "errcode") -> str:
    if response.status_code >= HTTP_ERROR_FLOOR:
        return f"http_{response.status_code}"
    data = response.json() if response.content else {}
    code = data.get("code", data.get(api_key))
    if code not in (0, None):
        return f"api_{code}"
    return STATUS_SENT


async def send_feishu(*, target: str, text: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    token = _cached_token("feishu")
    if token is None:
        response = await _post(
            FEISHU_TOKEN_URL,
            json_payload={"app_id": settings.feishu_app_id, "app_secret": settings.feishu_app_secret},
        )
        data = response.json() if response.content else {}
        token = data.get("tenant_access_token")
        if not token:
            return STATUS_NO_TOKEN
        _store_token("feishu", token, float(data.get("expire", DEFAULT_TOKEN_TTL_SECONDS)))
    response = await _post(
        FEISHU_SEND_URL,
        json_payload={
            "receive_id": target,
            "msg_type": "text",
            "content": json.dumps({"text": text[: CHANNEL_LIMITS["feishu"]]}, ensure_ascii=False),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return _http_status(response)


async def send_wecom(*, target: str, text: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    token = _cached_token("wecom")
    if token is None:
        response = await _get(
            WECOM_TOKEN_URL,
            params={"corpid": settings.wecom_corp_id, "corpsecret": settings.wecom_corp_secret},
        )
        data = response.json() if response.content else {}
        token = data.get("access_token")
        if not token:
            return STATUS_NO_TOKEN
        _store_token("wecom", token, float(data.get("expires_in", DEFAULT_TOKEN_TTL_SECONDS)))
    response = await _post(
        WECOM_SEND_URL,
        json_payload={
            "touser": target,
            "msgtype": "text",
            "agentid": settings.wecom_agent_id,
            "text": {"content": text[: CHANNEL_LIMITS["wecom"]]},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return _http_status(response)


async def send_dingtalk(*, target: str, text: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    token = _cached_token("dingtalk")
    if token is None:
        response = await _post(
            DINGTALK_TOKEN_URL,
            json_payload={
                "appKey": settings.dingtalk_app_key,
                "appSecret": settings.dingtalk_app_secret,
            },
        )
        data = response.json() if response.content else {}
        token = data.get("accessToken")
        if not token:
            return STATUS_NO_TOKEN
        _store_token("dingtalk", token, float(data.get("expireIn", DEFAULT_TOKEN_TTL_SECONDS)))
    response = await _post(
        DINGTALK_SEND_URL,
        json_payload={
            "robotCode": settings.dingtalk_robot_code,
            "userIds": [target],
            "msgKey": "sampleText",
            "msgParam": json.dumps({"content": text[: CHANNEL_LIMITS["dingtalk"]]}),
        },
        headers={"x-acs-dingtalk-access-token": token},
    )
    return _http_status(response)


SENDERS: dict[str, SenderFn] = {
    "feishu": send_feishu,
    "wecom": send_wecom,
    "dingtalk": send_dingtalk,
}


def get_sender(channel: str) -> SenderFn | None:
    return SENDERS.get(channel)


def sender_configured(channel: str, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if channel == "feishu":
        return bool(settings.feishu_app_id and settings.feishu_app_secret)
    if channel == "wecom":
        return bool(
            settings.wecom_corp_id and settings.wecom_corp_secret and settings.wecom_agent_id
        )
    if channel == "dingtalk":
        return bool(
            settings.dingtalk_app_key
            and settings.dingtalk_app_secret
            and settings.dingtalk_robot_code
        )
    return False
