import math

from sqlalchemy import select, and_

from app.agents.base import BaseAgent
from app.agents.messages import AgentMessage
from app.models.schedule import DeliverySchedule
from app.models.truck import Truck
from app.models.dock import Dock
from app.models.staff import Staff
from app.models.shift import Shift
from app.models.assignment import Assignment
from app.simulation_clock import sim_clock


class CoordinatorAgent(BaseAgent):
    """Central orchestrator that coordinates all other agents."""

    async def handle(self, msg: AgentMessage) -> None:
        if msg.action == "truck_arrived":
            await self._handle_truck_arrival(msg)
        elif msg.action == "unloading_complete":
            await self._handle_unloading_complete(msg)
        elif msg.action == "staffing_ok":
            await self._assign_staff(msg)
        elif msg.action == "staffing_shortage":
            await self._handle_shortage(msg)
        elif msg.action == "extra_staff_added":
            await self.log("decision", "info", f"Extra staff added: {msg.payload.get('added', 0)} workers called in")
        elif msg.action == "forecast_ready":
            await self._handle_forecast(msg)
        elif msg.action == "shifts_planned":
            await self.log("decision", "info", f"Shifts planned: {msg.payload.get('shifts_created', 0)} new shifts")
        elif msg.action == "manual_trigger":
            await self._run_daily_planning(msg)

    async def _handle_truck_arrival(self, msg: AgentMessage) -> None:
        schedule_entry_id = msg.payload["schedule_entry_id"]
        await self.log("decision", "info", f"Processing truck arrival for schedule #{schedule_entry_id}")

        # Ask alert agent to check staffing
        check_msg = AgentMessage(
            source_agent=self.name,
            target_agent="alert",
            msg_type="request",
            action="check_staffing",
            payload={"schedule_entry_id": schedule_entry_id},
            correlation_id=msg.correlation_id,
        )
        await self.send("alert", check_msg)

    async def _assign_staff(self, msg: AgentMessage) -> None:
        """When staffing is OK, assign workers and dock to truck."""
        schedule_entry_id = msg.payload["schedule_entry_id"]
        now = sim_clock.now()

        async with self.session_factory() as db:
            entry = await db.get(DeliverySchedule, schedule_entry_id)
            if not entry:
                return
            truck = await db.get(Truck, entry.truck_id)
            if not truck:
                return

            # Find free dock
            dock_q = select(Dock).where(Dock.status == "free").limit(1)
            dock_result = await db.execute(dock_q)
            dock = dock_result.scalar_one_or_none()
            if not dock:
                await self.log("decision", "warning", f"No free dock for truck {truck.license_plate}")
                return

            # Calculate needs
            loaders_needed = max(1, math.ceil(truck.cargo_volume_pallets / 10))
            forklift_needed = max(1, math.ceil(truck.cargo_volume_pallets / 20))

            # Find available staff on shift
            active_shifts_q = select(Shift.staff_id).where(
                and_(
                    Shift.shift_date == now.date(),
                    Shift.start_time <= now.time(),
                    Shift.end_time > now.time(),
                )
            )
            shift_result = await db.execute(active_shifts_q)
            on_shift_ids = [r[0] for r in shift_result.all()]

            assigned_names = []

            if on_shift_ids:
                # Assign loaders
                loader_q = select(Staff).where(
                    and_(Staff.id.in_(on_shift_ids), Staff.role == "loader", Staff.status == "available")
                ).limit(loaders_needed)
                loader_result = await db.execute(loader_q)
                loaders = loader_result.scalars().all()

                for loader in loaders:
                    a = Assignment(
                        schedule_entry_id=schedule_entry_id,
                        staff_id=loader.id,
                        dock_id=dock.id,
                        role_needed="loader",
                        assigned_by="coordinator_agent",
                    )
                    db.add(a)
                    loader.status = "busy"
                    assigned_names.append(f"{loader.full_name} (loader)")

                # Assign forklift operators
                forklift_q = select(Staff).where(
                    and_(Staff.id.in_(on_shift_ids), Staff.role == "forklift_operator", Staff.status == "available")
                ).limit(forklift_needed)
                forklift_result = await db.execute(forklift_q)
                forklifts = forklift_result.scalars().all()

                for op in forklifts:
                    a = Assignment(
                        schedule_entry_id=schedule_entry_id,
                        staff_id=op.id,
                        dock_id=dock.id,
                        role_needed="forklift_operator",
                        assigned_by="coordinator_agent",
                    )
                    db.add(a)
                    op.status = "busy"
                    assigned_names.append(f"{op.full_name} (forklift)")

            # Update dock and schedule
            dock.status = "occupied"
            entry.dock_id = dock.id
            entry.status = "in_progress"
            truck.status = "unloading"

            await db.commit()

        staff_str = ", ".join(assigned_names) if assigned_names else "no staff assigned"
        await self.log(
            "decision", "info",
            f"Assigned truck {truck.license_plate} to dock {dock.code}: {staff_str}",
            {"schedule_entry_id": schedule_entry_id, "dock": dock.code, "staff": assigned_names},
        )

    async def _handle_shortage(self, msg: AgentMessage) -> None:
        """When alert detects shortage, request extra staff from shift planner."""
        loader_deficit = msg.payload.get("loader_deficit", 0)
        forklift_deficit = msg.payload.get("forklift_deficit", 0)
        schedule_entry_id = msg.payload.get("schedule_entry_id")

        await self.log(
            "decision", "warning",
            f"Shortage detected for schedule #{schedule_entry_id}. "
            f"Requesting {loader_deficit} loaders, {forklift_deficit} forklift ops",
        )

        # Still try to assign what we have
        await self._assign_staff(msg)

        # Request extra staff
        extra_msg = AgentMessage(
            source_agent=self.name,
            target_agent="shift_planner",
            msg_type="command",
            action="request_extra_staff",
            payload={
                "loader_deficit": loader_deficit,
                "forklift_deficit": forklift_deficit,
                "schedule_entry_id": schedule_entry_id,
            },
            correlation_id=msg.correlation_id,
        )
        await self.send("shift_planner", extra_msg)

    async def _handle_unloading_complete(self, msg: AgentMessage) -> None:
        schedule_entry_id = msg.payload["schedule_entry_id"]

        async with self.session_factory() as db:
            entry = await db.get(DeliverySchedule, schedule_entry_id)
            if not entry:
                return
            truck = await db.get(Truck, entry.truck_id)

            # Free the dock
            if entry.dock_id:
                dock = await db.get(Dock, entry.dock_id)
                if dock:
                    dock.status = "free"

            # Free assigned staff
            assign_q = select(Assignment).where(
                and_(Assignment.schedule_entry_id == schedule_entry_id, Assignment.completed_at.is_(None))
            )
            assign_result = await db.execute(assign_q)
            assignments = assign_result.scalars().all()

            for a in assignments:
                a.completed_at = sim_clock.now()
                staff = await db.get(Staff, a.staff_id)
                if staff:
                    staff.status = "available"

            if truck:
                truck.status = "departed"

            await db.commit()

        await self.log(
            "decision", "info",
            f"Unloading complete for schedule #{schedule_entry_id}. Dock and staff freed.",
            {"schedule_entry_id": schedule_entry_id},
        )

    async def _handle_forecast(self, msg: AgentMessage) -> None:
        """Use forecast to trigger shift planning."""
        forecast = msg.payload.get("forecast", {})
        target_date = msg.payload.get("date")
        source = msg.payload.get("source", "unknown")
        risk_level = msg.payload.get("risk_level", "")
        recommendations = msg.payload.get("recommendations", [])
        analysis = msg.payload.get("analysis", "")

        log_msg = f"Received forecast for {target_date} (source: {source})"
        if risk_level:
            log_msg += f", risk: {risk_level}"
        await self.log("decision", "info", log_msg)

        if analysis:
            await self.log("decision", "info", f"[LLM Analysis] {analysis}")

        if recommendations:
            severity = "warning" if risk_level in ("medium", "high") else "info"
            for rec in recommendations:
                await self.log("decision", severity, f"[LLM Recommendation] {rec}")

        plan_msg = AgentMessage(
            source_agent=self.name,
            target_agent="shift_planner",
            msg_type="command",
            action="plan_shifts",
            payload={"forecast": forecast, "date": target_date},
            correlation_id=msg.correlation_id,
        )
        await self.send("shift_planner", plan_msg)

    async def _run_daily_planning(self, msg: AgentMessage) -> None:
        """Trigger full daily planning: forecast -> shift planning -> alert check."""
        await self.log("decision", "info", "Starting daily planning cycle")

        forecast_msg = AgentMessage(
            source_agent=self.name,
            target_agent="forecasting",
            msg_type="command",
            action="generate_forecast",
            payload={},
        )
        await self.send("forecasting", forecast_msg)

        # Also check upcoming arrivals
        alert_msg = AgentMessage(
            source_agent=self.name,
            target_agent="alert",
            msg_type="command",
            action="manual_trigger",
            payload={},
        )
        await self.send("alert", alert_msg)
