# Backend

Amazon 商品リンクを受け取り、Playwright で購入フローを実行する API です。

## Setup

```bash
cd backend
cp .env.example .env
uv sync
uv run playwright install chromium
uv run uvicorn app.main:app --reload
```

`docker compose up` で起動する場合も、`docker-compose.yml` 側で `--reload` を有効にしているため、`app/` 配下の変更で自動再起動します。

## Required .env

- `BACKEND_API_KEY`
- `AMAZON_EMAIL`
- `AMAZON_PASSWORD`
- `AMAZON_HEADLESS` (default: `true`)
- `AMAZON_SCREENSHOT_ENABLED` (default: `true`)
- `AMAZON_SCREENSHOT_DIR` (default: `artifacts/screenshots`)

## API

- `GET /health`
- `POST /api/purchases/amazon` (`name`, `count`, `product_url`, `message` を受け取る)

## Amazon automation notes

- 毎回 `AMAZON_EMAIL` / `AMAZON_PASSWORD` で Amazon にログインします。
- MFA が有効なアカウントはこの実装では購入フローを継続できません。
- ログイン後と購入準備地点で確認用スクリーンショットを保存します。
