"""
FastAPI обгортка для локального Ollama сервера + OpenAI
Дозволяє браузеру обходити CORS обмеження та порівнювати моделі через LLM-as-Judge
"""

from fastapi import FastAPI, HTTPException, Header, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from pydantic import BaseModel
from openai import AsyncOpenAI
from dotenv import load_dotenv
from typing import Optional
import base64
import io
from PIL import Image
import json

load_dotenv()

app = FastAPI(title="Local Llama Demo")

# CORS для браузера
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama сервер адреса
OLLAMA_BASE_URL = "http://localhost:11434"

# OpenAI клієнт (буде створюватись на запит з ключем від користувача)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Обслуговуємо HTML файли зі статичної папки
app.mount("/static", StaticFiles(directory=os.path.dirname(__file__)), name="static")


@app.get("/")
async def root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))


@app.get("/api/tags")
async def get_tags():
    """Отримати список доступних моделей з Ollama"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama недоступний: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


class GenerateRequest(BaseModel):
    model: str
    prompt: str
    stream: bool = False


class CompareRequest(BaseModel):
    prompt: str
    ollama_model: str = "llama2"


@app.post("/api/generate")
async def generate(request: GenerateRequest):
    """Відправити запит до Ollama та отримати відповідь"""
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": request.model,
                    "prompt": request.prompt,
                    "stream": request.stream
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama недоступний: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@app.post("/api/generate/openai")
async def generate_openai(request: GenerateRequest):
    """Відправити запит до OpenAI GPT-4o-mini та отримати відповідь"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY не встановлений")

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": request.prompt}],
            temperature=0.7
        )
        return {
            "response": response.choices[0].message.content,
            "model": "gpt-4o-mini",
            "tokens": response.usage.total_tokens
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI помилка: {str(e)}")


@app.post("/api/compare")
async def compare(request: CompareRequest, x_openai_key: Optional[str] = Header(None)):
    """Порівняти відповіді Ollama та OpenAI через LLM-as-Judge"""
    api_key = x_openai_key or OPENAI_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY не встановлений")

    try:
        # Запит до Ollama
        async with httpx.AsyncClient(timeout=300) as client:
            ollama_response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": request.ollama_model,
                    "prompt": request.prompt,
                    "stream": False
                }
            )
            ollama_response.raise_for_status()
            ollama_data = ollama_response.json()
            ollama_text = ollama_data.get("response", "")

        # Запит до OpenAI
        openai_client = AsyncOpenAI(api_key=api_key)
        openai_response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": request.prompt}],
            temperature=0.7
        )
        openai_text = openai_response.choices[0].message.content

        # LLM-as-Judge: детальна оцінка для кожної моделі
        ollama_judge_prompt = f"""Ти експерт-оцінювач. Оцініть цю відповідь на складне технічне питання.
МОВА: Відповідь ПОВИННА бути українською мовою.

ЗАПИТ: {request.prompt[:500]}...

ВІДПОВІДЬ (Ollama {request.ollama_model}):
{ollama_text[:1000]}

Оцініть по метриках (кожна 0-10):
1. **Технічна глибина** - розуміння складних архітектурних решень
2. **Специфічність** - конкретні приклади (моделі, інструменти, числа)
3. **Практичність** - чи можна реально використати рекомендацію
4. **Повнота** - охоплює усі аспекти питання (latency, cost, scalability)

ШТРАФ: Якщо відповідь англійською або змішаною мовою (замість чистої української) — знизьте ВСІ метрики на 3-4 бали за непослухання інструкції.

Формат: метрика1;метрика2;метрика3;метрика4;короткий коментар(макс 100 слів)"""

        openai_judge_prompt = f"""Ти експерт-оцінювач. Оцініть цю відповідь на складне технічне питання.
МОВА: Відповідь ПОВИННА бути українською мовою.

ЗАПИТ: {request.prompt[:500]}...

ВІДПОВІДЬ (OpenAI GPT-4o-mini):
{openai_text[:1000]}

Оцініть по метриках (кожна 0-10):
1. **Технічна глибина** - розуміння складних архітектурних решень
2. **Специфічність** - конкретні приклади (моделі, інструменти, числа)
3. **Практичність** - чи можна реально використати рекомендацію
4. **Повнота** - охоплює усі аспекти питання (latency, cost, scalability)

ШТРАФ: Якщо відповідь англійською або змішаною мовою (замість чистої української) — знизьте ВСІ метрики на 3-4 бали за непослухання інструкції.

Формат: метрика1;метрика2;метрика3;метрика4;короткий коментар(макс 100 слів)"""

        # Отримуємо оцінки для обох моделей паралельно
        ollama_judge_response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": ollama_judge_prompt}],
            temperature=0.3
        )

        openai_judge_response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": openai_judge_prompt}],
            temperature=0.3
        )

        ollama_judge_text = ollama_judge_response.choices[0].message.content
        openai_judge_text = openai_judge_response.choices[0].message.content

        # Парсимо оцінки
        def parse_scores(text):
            parts = text.split(";")
            try:
                return {
                    "depth": float(parts[0].strip()),
                    "specificity": float(parts[1].strip()),
                    "practicality": float(parts[2].strip()),
                    "completeness": float(parts[3].strip()),
                    "comment": parts[4].strip() if len(parts) > 4 else ""
                }
            except:
                return {"depth": 0, "specificity": 0, "practicality": 0, "completeness": 0, "comment": "Parse error"}

        ollama_scores = parse_scores(ollama_judge_text)
        openai_scores = parse_scores(openai_judge_text)

        return {
            "ollama": ollama_text,
            "openai": openai_text,
            "ollama_scores": ollama_scores,
            "openai_scores": openai_scores,
            "ollama_judge": ollama_judge_text,
            "openai_judge": openai_judge_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка порівняння: {str(e)}")


class VisionRequest(BaseModel):
    model: str
    prompt: str
    image_base64: str


@app.post("/api/vision")
async def vision_analyze(request: VisionRequest):
    """Аналізувати картинку через LLaVA (vision-language модель)"""
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            # Ollama /api/generate підтримує картинки через base64
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": request.model,
                    "prompt": request.prompt,
                    "images": [request.image_base64],
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama недоступний: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


class ImageGenerationRequest(BaseModel):
    prompt: str
    model: str = "flux"
    steps: int = 20
    guidance_scale: float = 7.5


@app.post("/api/generate-image")
async def generate_image(request: ImageGenerationRequest):
    """Генерувати зображення через Ollama (Flux, Stable Diffusion)"""
    try:
        async with httpx.AsyncClient(timeout=600) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": request.model,
                    "prompt": request.prompt,
                    "stream": False,
                    "parameters": {
                        "num_predict": request.steps,
                        "guidance_scale": request.guidance_scale
                    }
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Ollama недоступний: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@app.post("/api/openai/image")
async def generate_image_openai(request: ImageGenerationRequest, x_openai_key: Optional[str] = Header(None)):
    """Генерувати зображення через OpenAI DALL-E"""
    api_key = x_openai_key or OPENAI_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY не встановлений")

    try:
        openai_client = AsyncOpenAI(api_key=api_key)
        response = await openai_client.images.generate(
            model="dall-e-3",
            prompt=request.prompt,
            n=1,
            size="1024x1024",
            quality="standard"
        )
        return {
            "image_url": response.data[0].url,
            "prompt": request.prompt,
            "model": "dall-e-3"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI помилка: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
