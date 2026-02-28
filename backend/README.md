# Backend

GASから転送された自然言語の購買指示を受け取り、スプレッドシートの商品カタログとGeminiを使って購買対象を決定し、Playwrightで購買処理を実行します。

## Setup

```bash
cd backend
cp .env.example .env
uv sync
uv run playwright install chromium
uv run uvicorn app.main:app --reload
```

## Required .env

- `BACKEND_API_KEY`
- `GOOGLE_SHEET_ID`
- `GOOGLE_SHEET_RANGE` (default: `catalog!A:B`)
- `GOOGLE_SHEETS_API_KEY`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`

## API

- `GET /health`
- `POST /api/purchases`
- `GET /api/purchases`
- `POST /api/line/intents` (GASから自然言語を受け取る)

## Spreadsheet format

`catalog` シートのA列/B列を使用します。

- A列: 商品名
- B列: 商品リンク

注: 現在の実装は Google Sheets API Key で取得するため、対象スプレッドシートはAPIキーで参照可能な公開設定が必要です。
