import httpx

import config

async def ai_unique_text(text: str) -> str:
    """Отправляет текст в OpenRouter API для уникализации."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {config.OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    prompt = config.AI_PROMPT.format(text=text)
    data = {"model": config.OPENROUTER_MODEL_NAME, "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "text"}}

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            ai_markdown_text = result['choices'][0]['message']['content'].strip()
            return convert_markdown_to_html(ai_markdown_text)
        except Exception as e:
            print(f"❌ Ошибка при запросе к AI: {e}")
            error_message = f"❌ Ошибка уникализации. {escape_html_entities(str(e))}"
            return f"<b>{error_message}</b>\n\nОригинал:\n{text}"