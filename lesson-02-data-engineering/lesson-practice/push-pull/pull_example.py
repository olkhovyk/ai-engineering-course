import requests
import time
from datetime import datetime


def pull_weather(city: str = "London") -> dict:
    url = f"https://wttr.in/{city}?format=j1"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    current = data["current_condition"][0]
    return {
        "city": city,
        "temp_c": current["temp_C"],
        "humidity": current["humidity"],
        "description": current["weatherDesc"][0]["value"],
        "pulled_at": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    for i in range(3):
        result = pull_weather("Kyiv")
        print(f"[PULL #{i+1}] {result['pulled_at']}")
        print(f"  Kyiv: {result['temp_c']}°C, {result['humidity']}% humidity, {result['description']}")
        print()
        if i < 2:
            time.sleep(5)
