# 購買管理自動化アプリ

シェアハウス向けの購買依頼を、LINE自然言語入力から自動実行するアプリです。

- フロントエンド: Google Apps Script (TypeScript + pnpm + clasp)
- バックエンド: FastAPI (Python + Playwright + uv + Docker)
- AI: Gemini API（自然言語から商品名・数量を抽出）
- 商品マスタ: Google Spreadsheet（商品名・商品リンク）

## フロー

1. LINEでメッセージ送信（例: `トイレットペーパーを1つ買ってください`）
2. GAS (`doPost`) がWebhook受信し、バックエンドへ転送
3. バックエンドがスプレッドシートの商品一覧を取得
4. Gemini APIで自然言語を構造化（商品名・数量・メモ）
5. 商品リンクを確定してPlaywrightで購買処理
6. GASが処理結果をLINEへ返信

## ディレクトリ

```text
.
├── backend
│   ├── app
│   │   ├── main.py
│   │   ├── schemas.py
│   │   └── services
│   │       ├── catalog.py
│   │       ├── gemini.py
│   │       ├── line.py
│   │       └── purchase_runner.py
│   ├── docker-compose.yml
│   ├── pyproject.toml
│   └── .env.example
└── frontend
    ├── src/Code.ts
    ├── package.json
    └── appsscript.json
```

## クイックスタート

### 1. Backend

```bash
cd backend
cp .env.example .env
uv sync
uv run playwright install chromium
uv run uvicorn app.main:app --reload
```

### 2. Frontend (GAS)

```bash
cd frontend
cp .clasp.json.example .clasp.json
pnpm install
pnpm run push
```
