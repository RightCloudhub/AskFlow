"""Skill team membership for handoff queue scoping (PRD Wave B)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team, TeamMember


class TeamService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_team(
        self, name: str, *, description: str = "", intent_scope: str = ""
    ) -> Team:
        team = Team(name=name, description=description, intent_scope=intent_scope)
        self.db.add(team)
        await self.db.flush()
        await self.db.refresh(team)
        return team

    async def add_member(self, team_id: str, user_id: str) -> TeamMember:
        existing = await self.db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id, TeamMember.user_id == user_id
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            return row
        row = TeamMember(team_id=team_id, user_id=user_id)
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def list_teams(self) -> list[Team]:
        result = await self.db.execute(select(Team).order_by(Team.name))
        return list(result.scalars().all())

    async def list_members(self, team_id: str) -> list[TeamMember]:
        result = await self.db.execute(
            select(TeamMember).where(TeamMember.team_id == team_id)
        )
        return list(result.scalars().all())

    async def user_team_ids(self, user_id: str) -> list[str]:
        result = await self.db.execute(
            select(TeamMember.team_id).where(TeamMember.user_id == user_id)
        )
        return [r[0] for r in result.all()]

    async def team_intent_scopes(self, user_id: str) -> set[str]:
        team_ids = await self.user_team_ids(user_id)
        if not team_ids:
            return set()
        result = await self.db.execute(select(Team).where(Team.id.in_(team_ids)))
        scopes: set[str] = set()
        for t in result.scalars().all():
            for part in (t.intent_scope or "").split(","):
                p = part.strip()
                if p:
                    scopes.add(p)
        return scopes
