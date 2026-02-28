from dataclasses import dataclass

import httpx

from app.settings import settings


@dataclass(frozen=True)
class CatalogItem:
    item_name: str
    product_url: str


async def fetch_catalog_items() -> list[CatalogItem]:
    if not settings.google_sheet_id:
        raise ValueError("GOOGLE_SHEET_ID is not configured")
    if not settings.google_sheets_api_key:
        raise ValueError("GOOGLE_SHEETS_API_KEY is not configured")

    endpoint = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{settings.google_sheet_id}"
        f"/values/{settings.google_sheet_range}"
    )
    params = {"key": settings.google_sheets_api_key}

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(endpoint, params=params)
        response.raise_for_status()
        payload = response.json()

    rows = payload.get("values", [])
    items: list[CatalogItem] = []
    for row in rows:
        if len(row) < 2:
            continue
        name = str(row[0]).strip()
        url = str(row[1]).strip()
        if not name or not url:
            continue
        if name == "商品名" and url == "商品リンク":
            continue
        items.append(CatalogItem(item_name=name, product_url=url))

    if not items:
        raise ValueError("Catalog is empty")
    return items


def find_catalog_item(items: list[CatalogItem], requested_name: str) -> CatalogItem | None:
    needle = requested_name.strip().lower()
    if not needle:
        return None

    for item in items:
        if item.item_name.lower() == needle:
            return item

    for item in items:
        if needle in item.item_name.lower() or item.item_name.lower() in needle:
            return item

    return None
