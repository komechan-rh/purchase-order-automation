from playwright.async_api import async_playwright

from app.settings import settings


async def run_purchase_automation(
    item_name: str,
    quantity: int,
    note: str,
    product_url: str | None = None,
) -> None:
    # 実運用ではECサイトのログイン〜注文確定までをここに実装
    # 最初は疎通確認として対象ページへアクセスし、タイトル取得のみ行う
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        target = product_url or settings.automation_target_url
        await page.goto(target, wait_until="domcontentloaded")
        _ = await page.title()
        await browser.close()
