from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent_log import AgentLog
from app.schemas.agent_log import AgentLogOut

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/logs", response_model=list[AgentLogOut])
async def list_agent_logs(
    agent_name: str | None = None,
    severity: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(AgentLog).order_by(AgentLog.created_at.desc()).limit(limit)
    if agent_name:
        q = q.where(AgentLog.agent_name == agent_name)
    if severity:
        q = q.where(AgentLog.severity == severity)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.post("/trigger/{agent_name}")
async def trigger_agent(agent_name: str):
    from app.agents.messages import publish_manual_trigger
    valid_agents = ["coordinator", "shift_planner", "alert", "forecasting"]
    if agent_name not in valid_agents:
        raise HTTPException(400, f"Unknown agent: {agent_name}. Valid: {valid_agents}")
    await publish_manual_trigger(agent_name)
    return {"ok": True, "triggered": agent_name}


@router.get("/status")
async def agents_status(db: AsyncSession = Depends(get_db)):
    q = (
        select(AgentLog.agent_name, func.max(AgentLog.created_at).label("last_activity"))
        .group_by(AgentLog.agent_name)
    )
    result = await db.execute(q)
    rows = result.all()
    return [{"agent_name": r[0], "last_activity": r[1]} for r in rows]
