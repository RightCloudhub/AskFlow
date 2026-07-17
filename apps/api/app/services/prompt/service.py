"""Prompt template versioning + in-process cache (PRD §4.10)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt import PromptTemplate, PromptVersion

# process-local active content cache; epoch bumps invalidate
_cache: dict[str, str] = {}
_epoch = 0


def invalidate_prompt_cache() -> None:
    global _epoch, _cache
    _epoch += 1
    _cache = {}


class PromptService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_defaults(self) -> None:
        defaults = {
            "rag.system": "你是企业智能客服助手。仅依据证据回答，不知则说明不确定。引用用 [n]。",
            "rag.fallback_llm_down": "模型暂时不可用，请稍后重试或转人工。",
            "clarify.default": "我还不太确定您的具体需求，能否补充更多细节？",
        }
        for key, content in defaults.items():
            existing = await self.db.execute(select(PromptTemplate).where(PromptTemplate.key == key))
            if existing.scalar_one_or_none() is None:
                await self.create_template(key, content, description=f"default {key}")

    async def create_template(
        self,
        key: str,
        content: str,
        *,
        description: str = "",
        created_by: str | None = None,
    ) -> PromptTemplate:
        tpl = PromptTemplate(key=key, description=description)
        self.db.add(tpl)
        await self.db.flush()
        ver = PromptVersion(template_id=tpl.id, version=1, content=content, created_by=created_by)
        self.db.add(ver)
        await self.db.flush()
        tpl.active_version_id = ver.id
        await self.db.flush()
        await self.db.refresh(tpl)
        invalidate_prompt_cache()
        return tpl

    async def list_templates(self) -> list[PromptTemplate]:
        result = await self.db.execute(select(PromptTemplate).order_by(PromptTemplate.key))
        return list(result.scalars().all())

    async def get_active_content(self, key: str) -> str | None:
        if key in _cache:
            return _cache[key]
        result = await self.db.execute(select(PromptTemplate).where(PromptTemplate.key == key))
        tpl = result.scalar_one_or_none()
        if tpl is None or not tpl.active_version_id:
            return None
        ver = await self.db.get(PromptVersion, tpl.active_version_id)
        if ver is None:
            return None
        _cache[key] = ver.content
        return ver.content

    async def add_version(
        self,
        key: str,
        content: str,
        *,
        created_by: str | None = None,
        activate: bool = True,
    ) -> PromptVersion:
        result = await self.db.execute(select(PromptTemplate).where(PromptTemplate.key == key))
        tpl = result.scalar_one_or_none()
        if tpl is None:
            tpl = await self.create_template(key, content, created_by=created_by)
            ver = await self.db.get(PromptVersion, tpl.active_version_id)
            assert ver is not None
            return ver

        versions = await self.db.execute(
            select(PromptVersion)
            .where(PromptVersion.template_id == tpl.id)
            .order_by(PromptVersion.version.desc())
        )
        latest = versions.scalars().first()
        next_v = (latest.version if latest else 0) + 1
        ver = PromptVersion(
            template_id=tpl.id,
            version=next_v,
            content=content,
            created_by=created_by,
        )
        self.db.add(ver)
        await self.db.flush()
        if activate:
            tpl.active_version_id = ver.id
            invalidate_prompt_cache()
        await self.db.flush()
        await self.db.refresh(ver)
        return ver

    async def activate_version(self, key: str, version: int) -> PromptTemplate:
        result = await self.db.execute(select(PromptTemplate).where(PromptTemplate.key == key))
        tpl = result.scalar_one_or_none()
        if tpl is None:
            raise ValueError("template_not_found")
        ver_result = await self.db.execute(
            select(PromptVersion).where(
                PromptVersion.template_id == tpl.id,
                PromptVersion.version == version,
            )
        )
        ver = ver_result.scalar_one_or_none()
        if ver is None:
            raise ValueError("version_not_found")
        tpl.active_version_id = ver.id
        invalidate_prompt_cache()
        await self.db.flush()
        await self.db.refresh(tpl)
        return tpl
