import asyncio
from datetime import datetime, date, time, timezone, timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Base
from app.models.dock import Dock
from app.models.truck import Truck
from app.models.staff import Staff
from app.models.shift import Shift
from app.models.schedule import DeliverySchedule
from app.simulation_clock import sim_clock

DOCKS = [
    {"code": "D-01", "dock_type": "standard"},
    {"code": "D-02", "dock_type": "standard"},
    {"code": "D-03", "dock_type": "standard"},
    {"code": "D-04", "dock_type": "refrigerated"},
    {"code": "D-05", "dock_type": "refrigerated"},
]

TRUCKS = [
    {"license_plate": "AA1234BK", "carrier_name": "Нова Пошта Логістика", "cargo_type": "palletized", "cargo_volume_pallets": 20},
    {"license_plate": "BB5678CD", "carrier_name": "Делівері", "cargo_type": "palletized", "cargo_volume_pallets": 30},
    {"license_plate": "CC9012EF", "carrier_name": "SAT", "cargo_type": "palletized", "cargo_volume_pallets": 15},
    {"license_plate": "DD3456GH", "carrier_name": "Інтайм", "cargo_type": "bulk", "cargo_volume_pallets": 40},
    {"license_plate": "EE7890IJ", "carrier_name": "Укрпошта", "cargo_type": "palletized", "cargo_volume_pallets": 10},
    {"license_plate": "FF1122KL", "carrier_name": "Мист Експрес", "cargo_type": "refrigerated", "cargo_volume_pallets": 25},
    {"license_plate": "GG3344MN", "carrier_name": "Нова Пошта Логістика", "cargo_type": "palletized", "cargo_volume_pallets": 35},
    {"license_plate": "HH5566OP", "carrier_name": "Делівері", "cargo_type": "palletized", "cargo_volume_pallets": 20},
    {"license_plate": "II7788QR", "carrier_name": "SAT", "cargo_type": "bulk", "cargo_volume_pallets": 45},
    {"license_plate": "JJ9900ST", "carrier_name": "Інтайм", "cargo_type": "palletized", "cargo_volume_pallets": 15},
    {"license_plate": "KK1111UV", "carrier_name": "Укрпошта", "cargo_type": "palletized", "cargo_volume_pallets": 20},
    {"license_plate": "LL2222WX", "carrier_name": "Мист Експрес", "cargo_type": "refrigerated", "cargo_volume_pallets": 30},
    {"license_plate": "MM3333YZ", "carrier_name": "Нова Пошта Логістика", "cargo_type": "palletized", "cargo_volume_pallets": 25},
    {"license_plate": "NN4444AB", "carrier_name": "Делівері", "cargo_type": "palletized", "cargo_volume_pallets": 10},
    {"license_plate": "OO5555CD", "carrier_name": "SAT", "cargo_type": "palletized", "cargo_volume_pallets": 30},
    {"license_plate": "PP6666EF", "carrier_name": "Інтайм", "cargo_type": "bulk", "cargo_volume_pallets": 50},
    {"license_plate": "QQ7777GH", "carrier_name": "Укрпошта", "cargo_type": "palletized", "cargo_volume_pallets": 20},
    {"license_plate": "RR8888IJ", "carrier_name": "Мист Експрес", "cargo_type": "refrigerated", "cargo_volume_pallets": 15},
    {"license_plate": "SS9999KL", "carrier_name": "Нова Пошта Логістика", "cargo_type": "palletized", "cargo_volume_pallets": 25},
    {"license_plate": "TT0000MN", "carrier_name": "Делівері", "cargo_type": "palletized", "cargo_volume_pallets": 35},
]

STAFF = [
    {"full_name": "Петренко Іван", "role": "loader", "phone": "+380501234501"},
    {"full_name": "Коваленко Олег", "role": "loader", "phone": "+380501234502"},
    {"full_name": "Шевченко Микола", "role": "loader", "phone": "+380501234503"},
    {"full_name": "Бондаренко Андрій", "role": "loader", "phone": "+380501234504"},
    {"full_name": "Ткаченко Сергій", "role": "loader", "phone": "+380501234505"},
    {"full_name": "Кравченко Василь", "role": "loader", "phone": "+380501234506"},
    {"full_name": "Олійник Петро", "role": "loader", "phone": "+380501234507"},
    {"full_name": "Мельник Дмитро", "role": "loader", "phone": "+380501234508"},
    {"full_name": "Поліщук Ярослав", "role": "loader", "phone": "+380501234509"},
    {"full_name": "Лисенко Тарас", "role": "loader", "phone": "+380501234510"},
    {"full_name": "Савченко Олександр", "role": "forklift_operator", "phone": "+380501234511"},
    {"full_name": "Руденко Віталій", "role": "forklift_operator", "phone": "+380501234512"},
    {"full_name": "Марченко Богдан", "role": "forklift_operator", "phone": "+380501234513"},
    {"full_name": "Левченко Роман", "role": "forklift_operator", "phone": "+380501234514"},
    {"full_name": "Мороз Юрій", "role": "forklift_operator", "phone": "+380501234515"},
]


async def clear_all(db: AsyncSession):
    for table in ["assignments", "delivery_schedule", "shifts", "notifications", "agent_logs", "trucks", "staff", "docks"]:
        await db.execute(text(f"DELETE FROM {table}"))
    await db.commit()


async def seed_base_data(db: AsyncSession):
    """Insert docks, trucks, and staff."""
    # Check if data exists
    existing = await db.execute(select(Dock).limit(1))
    if existing.scalar_one_or_none():
        return

    for d in DOCKS:
        db.add(Dock(**d))
    for t in TRUCKS:
        db.add(Truck(**t))
    for s in STAFF:
        db.add(Staff(**s))
    await db.commit()


async def create_historical_schedules(db: AsyncSession, base_date: date):
    """Create 3 days of historical delivery data for forecasting."""
    trucks_result = await db.execute(select(Truck))
    trucks = trucks_result.scalars().all()

    for day_offset in range(1, 4):
        d = base_date - timedelta(days=day_offset)
        for i, truck in enumerate(trucks[:15]):
            hour = 7 + (i % 14)  # spread from 07:00 to 20:00
            arrival = datetime.combine(d, time(hour, (i * 7) % 60), tzinfo=timezone.utc)
            entry = DeliverySchedule(
                truck_id=truck.id,
                expected_arrival=arrival,
                actual_arrival=arrival + timedelta(minutes=(i % 3) * 10),
                estimated_unload_minutes=30 + (truck.cargo_volume_pallets // 5) * 5,
                status="completed",
            )
            db.add(entry)
    await db.commit()


SCENARIOS = {
    "normal_day": {
        "description": "20 trucks spread evenly, adequate staff",
        "truck_count": 20,
        "distribution": "even",  # trucks spread from 07:00 to 20:00
    },
    "peak_overload": {
        "description": "40 trucks clustered at midday, insufficient staff",
        "truck_count": 40,
        "distribution": "peak",  # most trucks arrive 11:00-13:00
    },
    "late_arrivals": {
        "description": "Trucks arrive 1-2 hours late",
        "truck_count": 15,
        "distribution": "late",  # expected early but shifted late
    },
}


async def load_scenario(name: str) -> dict:
    if name not in SCENARIOS:
        return {"ok": False, "error": f"Unknown scenario: {name}. Available: {list(SCENARIOS.keys())}"}

    scenario = SCENARIOS[name]

    async with async_session() as db:
        await clear_all(db)
        await seed_base_data(db)

        trucks_result = await db.execute(select(Truck))
        trucks = trucks_result.scalars().all()

        base_date = sim_clock.now().date()
        if base_date.year < 2026:
            base_date = date(2026, 4, 10)

        # Create historical data
        await create_historical_schedules(db, base_date)

        count = min(scenario["truck_count"], len(trucks))

        for i in range(count):
            truck = trucks[i % len(trucks)]

            if scenario["distribution"] == "even":
                hour = 7 + int((i / count) * 13)
                minute = (i * 17) % 60
            elif scenario["distribution"] == "peak":
                # Cluster around 11:00-13:00
                if i < count * 0.3:
                    hour = 7 + int((i / (count * 0.3)) * 3)
                    minute = (i * 23) % 60
                elif i < count * 0.8:
                    hour = 11 + int(((i - count * 0.3) / (count * 0.5)) * 2)
                    minute = (i * 13) % 60
                else:
                    hour = 14 + int(((i - count * 0.8) / (count * 0.2)) * 6)
                    minute = (i * 31) % 60
            else:  # late
                hour = 7 + int((i / count) * 6)
                minute = (i * 19) % 60

            hour = min(int(hour), 21)
            arrival = datetime.combine(base_date, time(hour, minute), tzinfo=timezone.utc)

            entry = DeliverySchedule(
                truck_id=truck.id,
                expected_arrival=arrival,
                estimated_unload_minutes=30 + (truck.cargo_volume_pallets // 5) * 5,
                status="planned",
            )
            db.add(entry)

        await db.commit()

    # Set simulation clock to start of day
    sim_clock.set_time(datetime.combine(base_date, time(5, 0), tzinfo=timezone.utc))

    return {
        "ok": True,
        "scenario": name,
        "description": scenario["description"],
        "trucks_scheduled": count,
        "simulation_date": base_date.isoformat(),
        "current_time": sim_clock.now().isoformat(),
    }


async def run_seed():
    async with async_session() as db:
        await seed_base_data(db)
        base_date = sim_clock.now().date()
        await create_historical_schedules(db, base_date)


if __name__ == "__main__":
    asyncio.run(run_seed())
