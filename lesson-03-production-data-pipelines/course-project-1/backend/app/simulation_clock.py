from datetime import datetime, timezone


class SimulationClock:
    def __init__(self):
        self._current_time: datetime | None = None

    def set_time(self, dt: datetime) -> None:
        self._current_time = dt

    def advance(self, minutes: int) -> datetime:
        from datetime import timedelta
        if self._current_time is None:
            self._current_time = datetime.now(timezone.utc)
        self._current_time += timedelta(minutes=minutes)
        return self._current_time

    def now(self) -> datetime:
        if self._current_time is None:
            return datetime.now(timezone.utc)
        return self._current_time

    def reset(self) -> None:
        self._current_time = None


sim_clock = SimulationClock()
