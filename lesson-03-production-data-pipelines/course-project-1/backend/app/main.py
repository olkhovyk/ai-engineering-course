import asyncio
import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import async_session
from app.agents.coordinator import CoordinatorAgent
from app.agents.alert import OperationalAlertAgent
from app.agents.shift_planner import ShiftPlanningAgent
from app.agents.forecasting import ForecastingAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent_tasks: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start agents
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    agents = [
        CoordinatorAgent("coordinator", redis_client, async_session),
        OperationalAlertAgent("alert", redis_client, async_session),
        ShiftPlanningAgent("shift_planner", redis_client, async_session),
        ForecastingAgent("forecasting", redis_client, async_session),
    ]

    for agent in agents:
        task = asyncio.create_task(agent.start())
        agent_tasks.append(task)

    logger.info("All agents started")
    yield

    # Cleanup
    for task in agent_tasks:
        task.cancel()
    await redis_client.close()
    logger.info("Agents stopped")


app = FastAPI(
    title="Distribution Center Multi-Agent System",
    description="Real-time HR and transport logistics synchronization",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from app.routers import trucks, docks, staff, shifts, schedules, assignments, dashboard, agents, notifications, simulation

app.include_router(trucks.router, prefix="/api/v1")
app.include_router(docks.router, prefix="/api/v1")
app.include_router(staff.router, prefix="/api/v1")
app.include_router(shifts.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(assignments.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(simulation.router, prefix="/api/v1")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
