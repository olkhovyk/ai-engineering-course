import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

import redis.asyncio as aioredis

from app.config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


@dataclass
class AgentMessage:
    source_agent: str
    target_agent: str
    msg_type: str  # "request", "response", "event", "command"
    action: str
    payload: dict = field(default_factory=dict)
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "AgentMessage":
        return cls(**json.loads(data))


async def publish_to(channel: str, msg: AgentMessage) -> None:
    r = await get_redis()
    await r.publish(channel, msg.to_json())


async def publish_truck_arrived(schedule_entry_id: int) -> None:
    msg = AgentMessage(
        source_agent="api",
        target_agent="coordinator",
        msg_type="event",
        action="truck_arrived",
        payload={"schedule_entry_id": schedule_entry_id},
    )
    await publish_to("agent:coordinator:inbox", msg)


async def publish_unloading_complete(schedule_entry_id: int) -> None:
    msg = AgentMessage(
        source_agent="api",
        target_agent="coordinator",
        msg_type="event",
        action="unloading_complete",
        payload={"schedule_entry_id": schedule_entry_id},
    )
    await publish_to("agent:coordinator:inbox", msg)


async def publish_manual_trigger(agent_name: str) -> None:
    msg = AgentMessage(
        source_agent="api",
        target_agent=agent_name,
        msg_type="command",
        action="manual_trigger",
        payload={},
    )
    await publish_to(f"agent:{agent_name}:inbox", msg)
