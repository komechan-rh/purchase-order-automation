from app.services.catalog import CatalogItem, find_catalog_item


def test_find_catalog_item_exact() -> None:
    items = [
        CatalogItem(item_name="トイレットペーパー", product_url="https://example.com/tp"),
        CatalogItem(item_name="牛乳", product_url="https://example.com/milk"),
    ]
    found = find_catalog_item(items, "牛乳")
    assert found is not None
    assert found.product_url == "https://example.com/milk"


def test_find_catalog_item_partial() -> None:
    items = [
        CatalogItem(item_name="トイレットペーパー", product_url="https://example.com/tp"),
    ]
    found = find_catalog_item(items, "トイレットペーパーを買って")
    assert found is not None
