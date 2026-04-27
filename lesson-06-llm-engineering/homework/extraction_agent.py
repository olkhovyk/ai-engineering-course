import openai
import requests
import json
import sys
import os

from dotenv import load_dotenv


load_dotenv()


# ── OLLAMA (self-hosted) ──
def call_ollama(prompt: str) -> str:
    """Викликає локальну модель через Ollama API"""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama2",  # або mistral
            "prompt": prompt,
            "stream": False,
        },
    )
    return response.json()["response"]


# ── OPENAI (cloud) ──
def call_openai(prompt: str) -> str:
    """Викликає GPT-4o-mini через OpenAI API"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing. Add it to the .env file.")

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """You are a meeting transcription parser.
Extract tasks, decisions, and a summary from meeting text.
Return ONLY valid JSON, no markdown, no extra text.""",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


# ── EXTRACTION LOGIC ──
def extract_meeting_data(text: str, provider: str = "ollama") -> dict:
    """
    Витягує структурований JSON з неструктурованого тексту зустрічі.

    Args:
        text: Транскрипт / протокол зустрічі
        provider: "ollama" або "openai"

    Returns:
        dict: {"summary": str, "tasks": [...], "decisions": [...]}
    """

    prompt = f"""Прочитай цей текст зустрічі та витягни:
1. summary (одна речення на українській)
2. tasks (список завдань з owner, task, deadline)
3. decisions (рішення, які було прийнято)

Текст:
{text}

Поверни ТІЛЬКИ JSON, нічого більше:
{{
  "summary": "...",
  "tasks": [
    {{"owner": "...", "task": "...", "deadline": "..."}}
  ],
  "decisions": ["..."]
}}"""

    if provider == "ollama":
        response_text = call_ollama(prompt)
    elif provider == "openai":
        response_text = call_openai(prompt)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    # Спробуй спарсити JSON
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON: {response_text[:200]}")
        return None


# ── MAIN ──
if __name__ == "__main__":
    # Читай з файлу або stdin
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        with open(input_file, "r", encoding="utf-8") as f:
            meeting_text = f.read()
    else:
        meeting_text = """
        Анна: Добрий день. Новий квартал, новий дизайн.
        У нас є потрібно зробити новий dashboard для аналітики.
        Іван, ти можеш взяти дизайн UI? Дедлайн п'ятниця, ні, краще наступна п'ятниця.
        Анна: Мартин, ты на backend? Давай API для користувачів.
        Мартин: Окей, я можу, але мені потрібні spec. До 15 травня, так?
        Анна: Все так. І хлопці, kod review обов'язковий перед merge, це точно вирішено.
        """

    # Тестуй обидві моделі
    print("🤖 Testing Ollama (local)...")
    result_local = extract_meeting_data(meeting_text, provider="ollama")
    print(json.dumps(result_local, indent=2, ensure_ascii=False))

    print("\n☁️  Testing OpenAI (cloud)...")
    result_cloud = extract_meeting_data(meeting_text, provider="openai")
    print(json.dumps(result_cloud, indent=2, ensure_ascii=False))
