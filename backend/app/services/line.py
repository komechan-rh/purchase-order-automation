import re


def extract_quantity_from_text(text: str) -> int:
    normalized = text.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    patterns = [
        r"(\d+)\s*(?:個|つ|本|箱|袋|パック|セット)",
        r"[xX]\s*(\d+)",
        r"(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        value = int(match.group(1))
        if value >= 1:
            return value
    return 1
