# Frontend (Google Apps Script)

LINE Webhookを受信し、バックエンド連携とLINE返信を行います。

## Setup

```bash
cd frontend
cp .clasp.json.example .clasp.json
pnpm install
pnpm run push
```

## Required Script Properties

- `BACKEND_URL` (e.g. `https://your-backend.example.com`)
- `BACKEND_API_KEY`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `GEMINI_API_KEY`
- `GEMINI_MODEL` (optional, default: `gemini-1.5-flash`)

## LINE連携

1. GASをウェブアプリとしてデプロイ（`doPost` を公開）
2. LINE Messaging APIのWebhook URLにGAS WebアプリURLを設定
3. LINEで自然言語指示を送信（例: `トイレットペーパーを1つ買ってください`）
4. GASがバックエンドへ転送し、結果をLINEに返信
