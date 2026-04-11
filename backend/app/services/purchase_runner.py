from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.settings import Settings, settings
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright


AMAZON_LOGIN_LINK = "https://www.amazon.co.jp/ap/signin?ie=UTF8&ie=UTF8&openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.co.jp%2Fap%2Fsignin%3Fopenid.pape.max_auth_age%3D900%26openid.return_to%3Dhttps%253A%252F%252Fwww.amazon.co.jp%252Fgp%252Fyourstore%252Fhome%253Fpath%253D%25252Fgp%25252Fyourstore%25252Fhome%2526signIn%253D1%2526useRedirectOnSuccess%253D1%2526action%253Dsign-out%2526ref_%253Dabn_yadd_sign_out%26openid.assoc_handle%3Djpflex%26openid.mode%3Dcheckid_setup%26openid.ns%3Dhttp%253A%252F%252Fspecs.openid.net%252Fauth%252F2.0&openid.assoc_handle=jpflex&openid.mode=checkid_setup&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&switch_account=signin&ignoreAuthState=1&disableLoginPrepopulate=1&ref_=ap_sw_aa"
logger = logging.getLogger("uvicorn.error").getChild("app.services.purchase_runner")


class AmazonPurchaseService:
    def __init__(self, app_settings: Settings) -> None:
        self.settings = app_settings

    async def run(
        self,
        item_name: str,
        quantity: int,
        note: str,
        product_url: str | None = None,
    ) -> None:
        _ = item_name, note
        target = self.resolve_target_url(product_url)

        logger.info("Purchase automation started")

        async with PlaywrightSessionManager(self.settings) as session:
            await session.login()
            await session.add_item_to_cart(quantity, target)
            await session.place_order(quantity)
            await session.capture_screenshot("ready-for-purchase", target)

    def resolve_target_url(self, product_url: str | None) -> str:
        target = product_url or self.settings.automation_target_url
        parsed = urlparse(target)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Invalid product URL")
        if "amazon." not in parsed.netloc:
            raise ValueError("Only Amazon product URLs are supported")
        return target


class PlaywrightSessionManager:
    def __init__(self, app_settings: Settings) -> None:
        self.settings = app_settings
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.screenshot_index = 0

    async def __aenter__(self) -> PlaywrightSessionManager:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.settings.amazon_headless)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.context is not None:
            await self.context.close()
        if self.browser is not None:
            await self.browser.close()
        if self.playwright is not None:
            await self.playwright.stop()

    async def login(self) -> None:
        if not self.settings.amazon_email or not self.settings.amazon_password:
            raise RuntimeError("Amazon credentials are required")
        page = self._require_page()
        await page.goto(
            AMAZON_LOGIN_LINK,
            wait_until="domcontentloaded",
        )

        # 表示されているログイン画面の入力欄に Amazon アカウントのメールアドレスを入力する。
        for selector in ['input[name="email"]', 'input[type="email"]']:
            locator = page.locator(selector)
            if await locator.count():
                await locator.first.fill(self.settings.amazon_email)
                break
        else:
            raise RuntimeError("Expected email input element not found")

        # パスワード入力画面へ進む。
        for selector in ['input#continue', 'input.a-button-input']:
            locator = page.locator(selector)
            if await locator.count():
                await locator.first.click()
                break
        else:
            raise RuntimeError("Expected continue button not found")

        await self.capture_screenshot("before-input-password")

        # パスワードを入力してサインインを送信する。
        for selector in ['input[name="password"]', 'input[type="password"]']:
            locator = page.locator(selector)
            if await locator.count():
                await locator.first.fill(self.settings.amazon_password)
                break
        else:
            raise RuntimeError("Expected password input element not found")

        await self.capture_screenshot("before-submit")
        for selector in ['#signInSubmit', 'input#signInSubmit', 'input.a-button-input']:
            locator = page.locator(selector)
            if await locator.count():
                await locator.first.click()
                break
        else:
            raise RuntimeError("Expected sign-in button not found")

        if await page.locator('input[name="otpCode"]').count():
            raise RuntimeError("Amazon OTP challenge detected. This flow does not support MFA.")

        await self.capture_screenshot("after-logged-in")
        logger.info("Amazon login succeeded")

    async def add_item_to_cart(self, quantity: int, product_url: str) -> None:
        page = self._require_page()
        await page.goto(product_url, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")

        # Buy Now ボタンがある場合は、そのままチェックアウトへ進む。
        if await page.locator("#buy-now-button").count():
            await page.click("#buy-now-button")
            return

        # 商品ページ側で数量を変更できる場合はここで合わせる。
        value = str(quantity)
        for selector in ["#quantity", 'select[name="quantity"]']:
            try:
                locator = page.locator(selector)
                if await locator.count():
                    await locator.select_option(value=value)
                    break
            except Exception:  # noqa: BLE001
                continue

        # 利用可能な追加ボタンを使って商品をカートへ入れる。
        for selector in [
            "#add-to-cart-button",
            'input[name="submit.add-to-cart"]',
            "#submit\\.add-to-cart",
        ]:
            locator = page.locator(selector)
            if await locator.count():
                await locator.first.click()
                break
        else:
            raise RuntimeError("Expected add-to-cart button not found")

        # カート追加後のサイドシートが出た場合は閉じる。
        for selector in ['#attach-close_sideSheet-link', '[aria-label="閉じる"]', '[aria-label="Close"]']:
            locator = page.locator(selector)
            if await locator.count():
                await locator.first.click()
                break

        # カート画面からチェックアウトへ進む。
        for selector in [
            'input[name="proceedToRetailCheckout"]',
            '#sc-buy-box-ptc-button input',
            'a[href*="proceedToCheckout"]',
        ]:
            locator = page.locator(selector)
            if await locator.count():
                await locator.first.click()
                break
        else:
            raise RuntimeError("Expected checkout button not found")

    async def place_order(self, quantity: int) -> None:
        page = self._require_page()

        # 数量変更や画面遷移の前に、最初のチェックアウト画面を保存する。
        await self.capture_screenshot("before-checkout-quantity")

        # チェックアウト側で数量を変更できる場合はここで合わせる。
        value = str(quantity)
        for selector in ['select[name^="quantity"]', 'select[data-action="a-dropdown-select"]']:
            locator = page.locator(selector)
            if await locator.count():
                try:
                    await locator.first.select_option(value=value)
                    await page.wait_for_load_state("networkidle")
                    break
                except Exception:  # noqa: BLE001
                    continue

        # 配送先や支払い方法の確認画面を順に進めて、注文確定ボタンまで到達する。
        for selector in [
            'input[name="proceedToRetailCheckout"]',
            'input[data-testid="Address_selectShipToThisAddress"]',
            'input[name="shipToThisAddress"]',
            'input[name="ppw-widgetEvent:SetPaymentPlanSelectContinueEvent"]',
            'input[name="ppw-widgetEvent:SelectAddressEvent"]',
        ]:
            locator = page.locator(selector)
            if await locator.count():
                await locator.first.click()
                await page.wait_for_load_state("networkidle")

        # 最後の注文確定ボタンを押して購入を完了する。
        for selector in [
            'input[name="placeYourOrder1"]',
            'input[name="placeYourOrder"]',
            '#submitOrderButtonId input',
        ]:
            locator = page.locator(selector)
            if await locator.count():
                await locator.first.click()
                return
        raise RuntimeError("Expected place-order button not found")

    async def capture_screenshot(self, label: str, product_url: str | None = None) -> Path | None:
        if not self.settings.amazon_screenshot_enabled:
            return None

        page = self._require_page()
        output_dir = Path(self.settings.amazon_screenshot_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.screenshot_index += 1
        suffix = self._build_screenshot_suffix(label, product_url)
        file_path = output_dir / f"{self.screenshot_index}_{suffix}.png"
        await page.screenshot(path=str(file_path), full_page=True)
        return file_path

    def _build_screenshot_suffix(self, label: str, product_url: str | None = None) -> str:
        host = ""
        if product_url:
            host = urlparse(product_url).netloc.replace(".", "-")
        raw = "-".join(part for part in [label, host] if part)
        sanitized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in raw.lower())
        return sanitized.strip("-") or "capture"

    def _require_page(self) -> Page:
        if self.page is None:
            raise RuntimeError("Playwright page is not initialized")
        return self.page


purchase_service = AmazonPurchaseService(settings)


async def run_purchase_automation(
    item_name: str,
    quantity: int,
    note: str,
    product_url: str | None = None,
) -> None:
    await purchase_service.run(item_name, quantity, note, product_url)
