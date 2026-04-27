import json
import logging
from abc import ABC, abstractmethod

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.messages import AgentMessage, publish_to
from app.models.agent_log import AgentLog

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    def __init__(self, name: str, redis: aioredis.Redis, session_factory: async_sessionmaker[AsyncSession]):
        self.name = name
        self.redis = redis
        self.session_factory = session_factory
        self.inbox_channel = f"agent:{name}:inbox"

    async def start(self) -> None:
        logger.info(f"[{self.name}] Agent started, listening on {self.inbox_channel}")
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.inbox_channel, "agent:broadcast")
        async for raw_message in pubsub.listen():
            if raw_message["type"] != "message":
                continue
            try:
                msg = AgentMessage.from_json(raw_message["data"])
                logger.info(f"[{self.name}] Received: {msg.action} from {msg.source_agent}")
                await self.handle(msg)
            except Exception as e:
                logger.error(f"[{self.name}] Error handling message: {e}", exc_info=True)
                await self.log("error", "critical", f"Error: {e}")

    @abstractmethod
    async def handle(self, msg: AgentMessage) -> None:
        ...

    async def send(self, target: str, msg: AgentMessage) -> None:
        channel = f"agent:{target}:inbox"
        await publish_to(channel, msg)

    async def broadcast(self, msg: AgentMessage) -> None:
        await publish_to("agent:broadcast", msg)

    async def log(self, event_type: str, severity: str, message: str, payload: dict | None = None) -> None:
        async with self.session_factory() as db:
            entry = AgentLog(
                agent_name=self.name,
                event_type=event_type,
                severity=severity,
                message=message,
                payload=payload,
            )
            db.add(entry)
            await db.commit()

    def create_response(self, original: AgentMessage, action: str, payload: dict) -> AgentMessage:
        return AgentMessage(
            source_agent=self.name,
            target_agent=original.source_agent,
            msg_type="response",
            action=action,
            payload=payload,
            correlation_id=original.correlation_id,
        )
