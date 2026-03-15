import asyncio
from pathlib import Path

import pytest

from app.services.purchase_runner import AmazonPurchaseService, PlaywrightSessionManager
from app.settings import Settings


def build_settings(**overrides: object) -> Settings:
    base = {
        "automation_target_url": "https://www.amazon.co.jp/dp/B000TEST",
        "amazon_email": "user@example.com",
        "amazon_password": "secret",
        "amazon_screenshot_enabled": True,
        "amazon_screenshot_dir": "artifacts/test-screenshots",
    }
    base.update(overrides)
    return Settings.model_validate(base)


def test_resolve_target_url_accepts_amazon_url() -> None:
    service = AmazonPurchaseService(build_settings())

    assert service.resolve_target_url("https://www.amazon.co.jp/dp/B000TEST") == "https://www.amazon.co.jp/dp/B000TEST"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/item",
        "notaurl",
    ],
)
def test_resolve_target_url_rejects_non_amazon_url(url: str) -> None:
    service = AmazonPurchaseService(build_settings())

    with pytest.raises(ValueError):
        service.resolve_target_url(url)


def test_capture_screenshot_saves_file_to_configured_directory(tmp_path: Path) -> None:
    class FakePage:
        def __init__(self) -> None:
            self.calls: list[tuple[str, bool]] = []

        async def screenshot(self, path: str, full_page: bool) -> None:
            self.calls.append((path, full_page))

    fake_page = FakePage()
    runner = PlaywrightSessionManager(
        build_settings(amazon_screenshot_dir=str(tmp_path), amazon_screenshot_enabled=True)
    )
    runner.page = fake_page  # type: ignore[assignment]

    saved_path = asyncio.run(
        runner.capture_screenshot("after-login", "https://www.amazon.co.jp/dp/B000TEST")
    )

    assert saved_path is not None
    assert saved_path.parent == tmp_path
    assert saved_path.suffix == ".png"
    assert saved_path.name.startswith("1_")
    assert "after-login" in saved_path.name
    assert fake_page.calls == [(str(saved_path), True)]


def test_capture_screenshot_increments_filename_prefix(tmp_path: Path) -> None:
    class FakePage:
        def __init__(self) -> None:
            self.calls: list[tuple[str, bool]] = []

        async def screenshot(self, path: str, full_page: bool) -> None:
            self.calls.append((path, full_page))

    runner = PlaywrightSessionManager(
        build_settings(amazon_screenshot_dir=str(tmp_path), amazon_screenshot_enabled=True)
    )
    runner.page = FakePage()  # type: ignore[assignment]

    first_path = asyncio.run(runner.capture_screenshot("first-shot"))
    second_path = asyncio.run(runner.capture_screenshot("second-shot"))

    assert first_path is not None
    assert second_path is not None
    assert first_path.name.startswith("1_")
    assert second_path.name.startswith("2_")


def test_capture_screenshot_returns_none_when_disabled(tmp_path: Path) -> None:
    class FakePage:
        async def screenshot(self, path: str, full_page: bool) -> None:  # pragma: no cover
            raise AssertionError("screenshot should not be called")

    runner = PlaywrightSessionManager(
        build_settings(amazon_screenshot_dir=str(tmp_path), amazon_screenshot_enabled=False)
    )
    runner.page = FakePage()  # type: ignore[assignment]

    saved_path = asyncio.run(runner.capture_screenshot("after-login"))

    assert saved_path is None


def test_add_item_to_cart_proceeds_to_checkout() -> None:
    class FakeLocator:
        async def count(self) -> int:
            return 1

        @property
        def first(self) -> "FakeLocator":
            return self

        async def select_option(self, value: str) -> None:
            _ = value
            return None

        async def click(self) -> None:
            return None

    class FakePage:
        async def click(self, selector: str) -> None:
            _ = selector
            return None

        def locator(self, selector: str) -> FakeLocator:
            return FakeLocator()

        async def goto(self, url: str, wait_until: str) -> None:
            return None

        async def wait_for_load_state(self, state: str) -> None:
            return None

    runner = PlaywrightSessionManager(build_settings())
    runner.page = FakePage()  # type: ignore[assignment]

    calls: list[str] = []

    async def goto(url: str, wait_until: str) -> None:
        _ = wait_until
        calls.append(f"goto:{url}")

    async def wait_for_load_state(state: str) -> None:
        calls.append(f"wait:{state}")

    runner.page.goto = goto  # type: ignore[method-assign]
    runner.page.wait_for_load_state = wait_for_load_state  # type: ignore[method-assign]

    asyncio.run(runner.add_item_to_cart(2, "https://www.amazon.co.jp/dp/B000TEST"))

    assert "goto:https://www.amazon.co.jp/dp/B000TEST" in calls
    assert "wait:networkidle" in calls


def test_place_order_submits_order() -> None:
    class FakeLocator:
        async def count(self) -> int:
            return 1

        @property
        def first(self) -> "FakeLocator":
            return self

        async def select_option(self, value: str) -> None:
            _ = value
            return None

        async def click(self) -> None:
            return None

    class FakePage:
        def locator(self, selector: str) -> FakeLocator:
            return FakeLocator()

        async def wait_for_load_state(self, state: str) -> None:
            return None

    runner = PlaywrightSessionManager(build_settings())
    runner.page = FakePage()  # type: ignore[assignment]

    calls: list[str] = []

    async def capture_screenshot(label: str, product_url: str | None = None) -> None:
        _ = product_url
        calls.append(f"screenshot:{label}")

    runner.capture_screenshot = capture_screenshot  # type: ignore[method-assign]

    asyncio.run(runner.place_order(2))

    assert "screenshot:before-checkout-quantity" in calls
