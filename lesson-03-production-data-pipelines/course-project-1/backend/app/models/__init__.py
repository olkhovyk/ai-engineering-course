from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.dock import Dock
from app.models.truck import Truck
from app.models.staff import Staff
from app.models.shift import Shift
from app.models.schedule import DeliverySchedule
from app.models.assignment import Assignment
from app.models.agent_log import AgentLog
from app.models.notification import Notification

__all__ = [
    "Base",
    "Dock",
    "Truck",
    "Staff",
    "Shift",
    "DeliverySchedule",
    "Assignment",
    "AgentLog",
    "Notification",
]
