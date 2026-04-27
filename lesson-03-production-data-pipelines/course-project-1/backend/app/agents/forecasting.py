import json
import logging
import re
from datetime import datetime, time, timezone, timedelta

from sqlalchemy import select, and_, func, extract

from app.agents.base import BaseAgent
from app.agents.messages import AgentMessage
from app.models.schedule import DeliverySchedule
from app.models.truck import Truck
from app.config import settings
from app.simulation_clock import sim_clock

logger = logging.getLogger(__name__)


class ForecastingAgent(BaseAgent):
    """Predicts workload using historical data + OpenAI LLM for intelligent analysis."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._openai_client = None

    def _get_openai_client(self):
        if self._openai_client is None and settings.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai_client

    async def handle(self, msg: AgentMessage) -> None:
        if msg.action in ("generate_forecast", "manual_trigger"):
            await self._generate_forecast(msg)

    async def _collect_historical_data(self, target_date) -> dict:
        """Collect historical delivery data from the last 7 days."""
        history_start = datetime.combine(target_date - timedelta(days=7), time.min, tzinfo=timezone.utc)
        history_end = datetime.combine(target_date - timedelta(days=1), time.max, tzinfo=timezone.utc)

        async with self.session_factory() as db:
            # Hourly aggregation
            q = (
                select(
                    extract("hour", DeliverySchedule.expected_arrival).label("hour"),
                    func.sum(Truck.cargo_volume_pallets).label("total_pallets"),
                    func.count().label("truck_count"),
                )
                .join(Truck, DeliverySchedule.truck_id == Truck.id)
                .where(
                    and_(
                        DeliverySchedule.expected_arrival >= history_start,
                        DeliverySchedule.expected_arrival <= history_end,
                    )
                )
                .group_by("hour")
                .order_by("hour")
            )
            result = await db.execute(q)
            hourly_rows = result.all()

            # Daily totals
            daily_q = (
                select(
                    func.date_trunc("day", DeliverySchedule.expected_arrival).label("day"),
                    func.sum(Truck.cargo_volume_pallets).label("total_pallets"),
                    func.count().label("truck_count"),
                )
                .join(Truck, DeliverySchedule.truck_id == Truck.id)
                .where(
                    and_(
                        DeliverySchedule.expected_arrival >= history_start,
                        DeliverySchedule.expected_arrival <= history_end,
                    )
                )
                .group_by("day")
                .order_by("day")
            )
            daily_result = await db.execute(daily_q)
            daily_rows = daily_result.all()

            # Today's scheduled
            today_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
            today_end = datetime.combine(target_date, time.max, tzinfo=timezone.utc)
            today_q = (
                select(
                    extract("hour", DeliverySchedule.expected_arrival).label("hour"),
                    func.sum(Truck.cargo_volume_pallets).label("total_pallets"),
                    func.count().label("truck_count"),
                )
                .join(Truck, DeliverySchedule.truck_id == Truck.id)
                .where(
                    and_(
                        DeliverySchedule.expected_arrival >= today_start,
                        DeliverySchedule.expected_arrival <= today_end,
                    )
                )
                .group_by("hour")
                .order_by("hour")
            )
            today_result = await db.execute(today_q)
            today_rows = today_result.all()

        return {
            "hourly_history": [
                {"hour": int(r[0]), "total_pallets": int(r[1]), "truck_count": int(r[2])}
                for r in hourly_rows
            ],
            "daily_totals": [
                {"day": str(r[0].date()) if r[0] else "unknown", "total_pallets": int(r[1]), "truck_count": int(r[2])}
                for r in daily_rows
            ],
            "today_scheduled": [
                {"hour": int(r[0]), "total_pallets": int(r[1]), "truck_count": int(r[2])}
                for r in today_rows
            ],
        }

    def _build_statistical_forecast(self, historical_data: dict) -> dict:
        """Fallback: simple moving average forecast."""
        hourly_history = historical_data["hourly_history"]
        hourly_data = {}
        for row in hourly_history:
            hour = row["hour"]
            avg_pallets = row["total_pallets"] / 7
            avg_trucks = row["truck_count"] / 7
            hourly_data[hour] = {
                "predicted_pallets": round(avg_pallets, 1),
                "predicted_trucks": round(avg_trucks, 1),
                "loaders_needed": max(1, round(avg_pallets / 10)),
                "forklift_needed": max(1, round(avg_pallets / 20)),
            }

        forecast = {}
        for h in range(6, 23):
            if h in hourly_data:
                forecast[str(h)] = hourly_data[h]
            else:
                forecast[str(h)] = {
                    "predicted_pallets": 0,
                    "predicted_trucks": 0,
                    "loaders_needed": 0,
                    "forklift_needed": 0,
                }
        return forecast

    async def _get_llm_forecast(self, historical_data: dict, target_date) -> dict | None:
        """Use OpenAI GPT to analyze historical data and produce an intelligent forecast."""
        client = self._get_openai_client()
        if not client:
            return None

        prompt = f"""You are an AI logistics analyst for a distribution center.

Analyze the following historical delivery data and produce a forecast for {target_date}.

## Historical Data (last 7 days)

### Hourly distribution (aggregated across 7 days):
{json.dumps(historical_data['hourly_history'], indent=2)}

### Daily totals:
{json.dumps(historical_data['daily_totals'], indent=2)}

### Today's already scheduled deliveries:
{json.dumps(historical_data['today_scheduled'], indent=2)}

## Staff requirements formula:
- 1 loader per 10 pallets
- 1 forklift operator per 20 pallets

## Task:
Produce a JSON forecast for each hour from 6:00 to 22:00 with the following structure:
{{
  "forecast": {{
    "6": {{"predicted_pallets": N, "predicted_trucks": N, "loaders_needed": N, "forklift_needed": N}},
    "7": ...
  }},
  "peak_hour": "HH",
  "total_predicted_pallets": N,
  "risk_level": "low|medium|high",
  "recommendations": [
    "recommendation 1",
    "recommendation 2"
  ],
  "analysis": "Brief analysis of patterns and risks"
}}

Consider:
- Day-of-week patterns
- Peak clustering risks
- Whether today's scheduled volume is unusual compared to history
- Staff adequacy recommendations

Return ONLY valid JSON, no markdown."""

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a logistics forecasting AI. Always respond with valid JSON only. Never use trailing commas in JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content.strip()
            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            # Fix trailing commas (common GPT issue)
            content = re.sub(r',\s*}', '}', content)
            content = re.sub(r',\s*]', ']', content)
            return json.loads(content)
        except Exception as e:
            logger.error(f"[forecasting] OpenAI API error: {e}")
            return None

    async def _generate_forecast(self, msg: AgentMessage) -> None:
        now = sim_clock.now()
        target_date = now.date()

        # Step 1: Collect historical data
        historical_data = await self._collect_historical_data(target_date)

        # Step 2: Try LLM forecast, fallback to statistical
        llm_result = await self._get_llm_forecast(historical_data, target_date)

        if llm_result and "forecast" in llm_result:
            forecast = llm_result["forecast"]
            peak_hour = llm_result.get("peak_hour", "12")
            total_predicted_pallets = llm_result.get("total_predicted_pallets", 0)
            risk_level = llm_result.get("risk_level", "unknown")
            recommendations = llm_result.get("recommendations", [])
            analysis = llm_result.get("analysis", "")
            source = "llm"

            await self.log(
                "forecast", "info",
                f"[LLM] Forecast for {target_date}: ~{total_predicted_pallets} pallets, "
                f"peak at {peak_hour}:00, risk: {risk_level}",
                {
                    "date": str(target_date),
                    "forecast": forecast,
                    "peak_hour": peak_hour,
                    "risk_level": risk_level,
                    "recommendations": recommendations,
                    "analysis": analysis,
                    "source": "llm",
                },
            )

            if recommendations:
                recs_text = "; ".join(recommendations)
                await self.log(
                    "forecast", "info" if risk_level == "low" else "warning",
                    f"[LLM] Recommendations: {recs_text}",
                    {"recommendations": recommendations},
                )
        else:
            forecast = self._build_statistical_forecast(historical_data)
            peak_hour = max(forecast.items(), key=lambda x: x[1]["predicted_pallets"])[0] if forecast else "12"
            total_predicted_pallets = sum(v["predicted_pallets"] for v in forecast.values())
            risk_level = "unknown"
            recommendations = []
            analysis = ""
            source = "statistical"

            if not settings.OPENAI_API_KEY:
                reason = "OpenAI API key not configured"
            else:
                reason = "LLM call failed, see logs"

            await self.log(
                "forecast", "info",
                f"[Statistical] Forecast for {target_date}: ~{total_predicted_pallets:.0f} pallets, "
                f"peak at {peak_hour}:00 ({reason})",
                {"date": str(target_date), "forecast": forecast, "peak_hour": peak_hour, "source": "statistical"},
            )

        response = self.create_response(msg, "forecast_ready", {
            "date": str(target_date),
            "forecast": forecast,
            "peak_hour": peak_hour,
            "total_predicted_pallets": total_predicted_pallets,
            "risk_level": risk_level,
            "recommendations": recommendations,
            "analysis": analysis,
            "source": source,
        })
        await self.send("coordinator", response)
