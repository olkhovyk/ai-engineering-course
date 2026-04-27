import math

from sqlalchemy import select, and_

from app.agents.base import BaseAgent
from app.agents.messages import AgentMessage
from app.models.schedule import DeliverySchedule
from app.models.truck import Truck
from app.models.staff import Staff
from app.models.shift import Shift
from app.models.notification import Notification
from app.simulation_clock import sim_clock


class OperationalAlertAgent(BaseAgent):
    """Detects staffing shortages when trucks arrive or are about to arrive."""

    async def handle(self, msg: AgentMessage) -> None:
        if msg.action == "check_staffing":
            await self._check_staffing(msg)
        elif msg.action == "manual_trigger":
            await self._check_upcoming(msg)

    async def _check_staffing(self, msg: AgentMessage) -> None:
        schedule_entry_id = msg.payload.get("schedule_entry_id")
        async with self.session_factory() as db:
            entry = await db.get(DeliverySchedule, schedule_entry_id)
            if not entry:
                return
            truck = await db.get(Truck, entry.truck_id)
            if not truck:
                return

            # Calculate needed staff
            loaders_needed = max(1, math.ceil(truck.cargo_volume_pallets / 10))
            forklift_needed = max(1, math.ceil(truck.cargo_volume_pallets / 20))

            # Find available staff
            now = sim_clock.now()
            active_shifts_q = select(Shift.staff_id).where(
                and_(
                    Shift.shift_date == now.date(),
                    Shift.start_time <= now.time(),
                    Shift.end_time > now.time(),
                )
            )
            active_shift_result = await db.execute(active_shifts_q)
            on_shift_ids = [r[0] for r in active_shift_result.all()]

            if not on_shift_ids:
                available_loaders = 0
                available_forklift = 0
            else:
                loader_q = select(Staff).where(
                    and_(Staff.id.in_(on_shift_ids), Staff.role == "loader", Staff.status == "available")
                )
                forklift_q = select(Staff).where(
                    and_(Staff.id.in_(on_shift_ids), Staff.role == "forklift_operator", Staff.status == "available")
                )
                loader_result = await db.execute(loader_q)
                forklift_result = await db.execute(forklift_q)
                available_loaders = len(loader_result.scalars().all())
                available_forklift = len(forklift_result.scalars().all())

            loader_deficit = max(0, loaders_needed - available_loaders)
            forklift_deficit = max(0, forklift_needed - available_forklift)

            payload = {
                "schedule_entry_id": schedule_entry_id,
                "truck": truck.license_plate,
                "loaders_needed": loaders_needed,
                "forklift_needed": forklift_needed,
                "loaders_available": available_loaders,
                "forklift_available": available_forklift,
                "loader_deficit": loader_deficit,
                "forklift_deficit": forklift_deficit,
            }

            if loader_deficit > 0 or forklift_deficit > 0:
                await self.log(
                    "alert", "warning",
                    f"Staffing shortage for truck {truck.license_plate}: "
                    f"need {loaders_needed} loaders (have {available_loaders}), "
                    f"need {forklift_needed} forklift ops (have {available_forklift})",
                    payload,
                )
                n = Notification(
                    title=f"Staffing shortage: truck {truck.license_plate}",
                    body=f"Deficit: {loader_deficit} loaders, {forklift_deficit} forklift operators",
                    severity="warning",
                    source_agent=self.name,
                )
                db.add(n)
                await db.commit()

                response = self.create_response(msg, "staffing_shortage", payload)
            else:
                await self.log(
                    "check", "info",
                    f"Staffing OK for truck {truck.license_plate}: "
                    f"{available_loaders} loaders, {available_forklift} forklift ops available",
                    payload,
                )
                response = self.create_response(msg, "staffing_ok", payload)

            await self.send("coordinator", response)

    async def _check_upcoming(self, msg: AgentMessage) -> None:
        """Check all trucks arriving in the next 30 minutes."""
        from datetime import timedelta
        now = sim_clock.now()
        window_end = now + timedelta(minutes=30)

        async with self.session_factory() as db:
            q = select(DeliverySchedule).where(
                and_(
                    DeliverySchedule.expected_arrival >= now,
                    DeliverySchedule.expected_arrival <= window_end,
                    DeliverySchedule.status == "planned",
                )
            )
            result = await db.execute(q)
            upcoming = result.scalars().all()

            for entry in upcoming:
                check_msg = AgentMessage(
                    source_agent=self.name,
                    target_agent=self.name,
                    msg_type="request",
                    action="check_staffing",
                    payload={"schedule_entry_id": entry.id},
                    correlation_id=msg.correlation_id,
                )
                await self._check_staffing(check_msg)

        await self.log("check", "info", f"Checked {len(upcoming)} upcoming arrivals in next 30 min")
