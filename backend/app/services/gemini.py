import json
import re
from dataclasses import dataclass

import httpx

from app.services.line import extract_quantity_from_text
from app.settings import settings


@dataclass(frozen=True)
class ParsedIntent:
    item_name: str
    quantity: int
    note: str


def _extract_json_object(text: str) -> dict[str, object] | None:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        candidate = candidate.replace("json", "", 1).strip()

    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None

    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _heuristic_parse(text: str, catalog_names: list[str]) -> ParsedIntent:
    quantity = extract_quantity_from_text(text)
    name = ""
    for catalog_name in catalog_names:
        if catalog_name and catalog_name in text:
            name = catalog_name
            break
    if not name and catalog_names:
        name = catalog_names[0]
    return ParsedIntent(item_name=name, quantity=quantity, note=text.strip())


async def parse_purchase_intent_with_gemini(text: str, catalog_names: list[str]) -> ParsedIntent:
    if not text.strip():
        raise ValueError("text is empty")

    if not settings.gemini_api_key:
        return _heuristic_parse(text, catalog_names)

    prompt = (
        "あなたは購買指示の構造化アシスタントです。"
        "次の入力文から item_name, quantity, note をJSONで返してください。"
        "JSON以外は出力しないこと。quantityは1以上の整数。"
        f"商品候補: {', '.join(catalog_names)}。"
        f"入力文: {text}"
    )

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}"
        f":generateContent?key={settings.gemini_api_key}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(endpoint, json=body)
            response.raise_for_status()
            payload = response.json()
    except Exception:  # noqa: BLE001
        return _heuristic_parse(text, catalog_names)

    text_output = (
        payload.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
    )

    data = _extract_json_object(text_output)
    if not data:
        return _heuristic_parse(text, catalog_names)

    item_name = str(data.get("item_name", "")).strip()
    quantity_raw = data.get("quantity", 1)
    note = str(data.get("note", "")).strip()

    try:
        quantity = int(quantity_raw)
    except (TypeError, ValueError):
        quantity = extract_quantity_from_text(text)

    if quantity < 1:
        quantity = 1

    if not item_name:
        return _heuristic_parse(text, catalog_names)

    return ParsedIntent(item_name=item_name, quantity=quantity, note=note)
