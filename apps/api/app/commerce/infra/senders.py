"""Pluggable delivery; console logs metadata only, never verification content."""

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from uuid import uuid4

import httpx

from app.commerce.infra.resilience import CircuitBreaker

logger = logging.getLogger("askflow.mall.notify")


class ConsoleSender:
    async def send(self, *, target: str, subject: str, body: str):
        reference = str(uuid4())
        logger.info("console delivery reference=%s content_bytes=%s", reference, len(body.encode()))
        return reference


class SmtpSender:
    def __init__(self, settings):
        self.settings = settings
        self.breaker = CircuitBreaker("smtp", settings)

    async def send(self, *, target: str, subject: str, body: str):
        return await self.breaker.call(
            lambda: asyncio.to_thread(self._send, target=target, subject=subject, body=body), readonly=False)

    def _send(self, *, target, subject, body):
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = self.settings.smtp_from, target, subject
        message.set_content(body)
        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port,
                          timeout=self.settings.external_timeout_seconds) as smtp:
            smtp.starttls()
            if self.settings.smtp_username:
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
            smtp.send_message(message)
        return str(uuid4())


class HttpSmsSender:
    def __init__(self, settings):
        self.settings = settings
        self.breaker = CircuitBreaker("sms", settings)

    async def send(self, *, target: str, subject: str, body: str):
        return await self.breaker.call(lambda: self._send(target=target, body=body), readonly=False)

    async def _send(self, *, target: str, body: str):
        async with httpx.AsyncClient(timeout=self.settings.external_timeout_seconds) as client:
            response = await client.post(self.settings.sms_provider_url,
                headers={"Authorization": "Bearer " + self.settings.sms_provider_token},
                json={"target": target, "message": body})
            response.raise_for_status()
            return str(response.json()["message_id"])
