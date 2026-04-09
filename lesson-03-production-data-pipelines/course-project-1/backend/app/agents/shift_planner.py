from datetime import time

from sqlalchemy import select, and_

from app.agents.base import BaseAgent
from app.agents.messages import AgentMessage
from app.models.staff import Staff
from app.models.shift import Shift
from app.simulation_clock import sim_clock


class ShiftPlanningAgent(BaseAgent):
    """Plans and adjusts staff shifts based on forecasted or actual demand."""

    async def handle(self, msg: AgentMessage) -> None:
        if msg.action == "plan_shifts":
            await self._plan_shifts(msg)
        elif msg.action == "request_extra_staff":
            await self._add_emergency_shifts(msg)
        elif msg.action == "manual_trigger":
            await self._plan_shifts(msg)

    async def _plan_shifts(self, msg: AgentMessage) -> None:
        """Create shifts for a given date based on forecast data."""
        now = sim_clock.now()
        target_date = now.date()

        forecast = msg.payload.get("forecast", {})
        # Default: morning shift 06:00-14:00, evening shift 14:00-22:00
        shifts_config = [
            {"start": time(6, 0), "end": time(14, 0), "label": "morning"},
            {"start": time(14, 0), "end": time(22, 0), "label": "evening"},
        ]

        async with self.session_factory() as db:
            # Get all staff
            staff_result = await db.execute(select(Staff))
            all_staff = staff_result.scalars().all()
            loaders = [s for s in all_staff if s.role == "loader"]
            forklift_ops = [s for s in all_staff if s.role == "forklift_operator"]

            created_count = 0
            for shift_cfg in shifts_config:
                # Check existing shifts
                existing_q = select(Shift).where(
                    and_(
                        Shift.shift_date == target_date,
                        Shift.start_time == shift_cfg["start"],
                    )
                )
                existing_result = await db.execute(existing_q)
                existing_staff_ids = {s.staff_id for s in existing_result.scalars().all()}

                # Assign loaders: split between shifts
                if shift_cfg["label"] == "morning":
                    loader_pool = loaders[: len(loaders) // 2 + 1]
                    forklift_pool = forklift_ops[: len(forklift_ops) // 2 + 1]
                else:
                    loader_pool = loaders[len(loaders) // 2:]
                    forklift_pool = forklift_ops[len(forklift_ops) // 2:]

                for staff_member in loader_pool + forklift_pool:
                    if staff_member.id in existing_staff_ids:
                        continue
                    shift = Shift(
                        staff_id=staff_member.id,
                        shift_date=target_date,
                        start_time=shift_cfg["start"],
                        end_time=shift_cfg["end"],
                        created_by="shift_planner_agent",
                    )
                    db.add(shift)
                    created_count += 1

            await db.commit()

        await self.log(
            "shift_change", "info",
            f"Planned {created_count} shifts for {target_date}",
            {"date": str(target_date), "shifts_created": created_count},
        )

        response = self.create_response(msg, "shifts_planned", {"shifts_created": created_count})
        await self.send("coordinator", response)

    async def _add_emergency_shifts(self, msg: AgentMessage) -> None:
        """Add extra staff shifts when there's a shortage."""
        now = sim_clock.now()
        loader_deficit = msg.payload.get("loader_deficit", 0)
        forklift_deficit = msg.payload.get("forklift_deficit", 0)
        shift_start = now.time()
        shift_end = time(min(shift_start.hour + 6, 23), 0)

        async with self.session_factory() as db:
            # Find off-duty staff not on any shift today
            all_staff_result = await db.execute(select(Staff))
            all_staff = all_staff_result.scalars().all()

            today_shifts_q = select(Shift.staff_id).where(Shift.shift_date == now.date())
            today_shifts_result = await db.execute(today_shifts_q)
            on_shift_today = {r[0] for r in today_shifts_result.all()}

            available_loaders = [s for s in all_staff if s.role == "loader" and s.id not in on_shift_today]
            available_forklift = [s for s in all_staff if s.role == "forklift_operator" and s.id not in on_shift_today]

            added = 0
            for i in range(min(loader_deficit, len(available_loaders))):
                shift = Shift(
                    staff_id=available_loaders[i].id,
                    shift_date=now.date(),
                    start_time=shift_start,
                    end_time=shift_end,
                    created_by="shift_planner_agent",
                )
                db.add(shift)
                available_loaders[i].status = "available"
                added += 1

            for i in range(min(forklift_deficit, len(available_forklift))):
                shift = Shift(
                    staff_id=available_forklift[i].id,
                    shift_date=now.date(),
                    start_time=shift_start,
                    end_time=shift_end,
                    created_by="shift_planner_agent",
                )
                db.add(shift)
                available_forklift[i].status = "available"
                added += 1

            await db.commit()

        await self.log(
            "shift_change", "info",
            f"Emergency: called in {added} extra staff for {now.date()} starting at {shift_start}",
            {"extra_staff": added, "loader_deficit": loader_deficit, "forklift_deficit": forklift_deficit},
        )

        response = self.create_response(msg, "extra_staff_added", {"added": added})
        await self.send("coordinator", response)
