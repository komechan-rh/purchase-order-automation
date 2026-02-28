from app.services.line import extract_quantity_from_text


def test_extract_quantity_from_text() -> None:
    assert extract_quantity_from_text("トイレットペーパーを1つ買って") == 1
    assert extract_quantity_from_text("牛乳を３本") == 3
    assert extract_quantity_from_text("水 x 12") == 12
    assert extract_quantity_from_text("洗剤を買って") == 1
