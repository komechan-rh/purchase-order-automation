type LineWebhookPayload = {
  events?: Array<{
    type?: string;
    replyToken?: string;
    message?: { type?: string; text?: string };
    source?: { userId?: string };
  }>;
};

type BackendIntentResponse = {
  order_id: number;
  item_name: string;
  quantity: number;
  product_url: string;
  status: string;
};

type GeminiResponse = {
  candidates?: Array<{
    content?: {
      parts?: Array<{
        text?: string;
      }>;
    };
  }>;
};
type GeminiReplyJson = {
  name: string;
  count: number;
  product_url: string;
  message: string;
};

const lineAccessToken = getProperty("LINE_CHANNEL_ACCESS_TOKEN");
const geminiApiKey = getProperty("GEMINI_API_KEY");
const geminiModel = getProperty("GEMINI_MODEL") || "gemini-3-flash-preview";

function doPost(
  e: GoogleAppsScript.Events.DoPost,
): GoogleAppsScript.Content.TextOutput {
  if (!lineAccessToken || !geminiApiKey) {
    return jsonResponse({
      ok: false,
      error: "Required Script Properties are missing",
    });
  }

  const raw = e.postData?.contents || "{}";
  const payload = JSON.parse(raw) as LineWebhookPayload;

  let processed = 0;

  for (const event of payload.events || []) {
    if (event.type !== "message") {
      continue;
    }
    if (event.message?.type !== "text") {
      continue;
    }

    const text = (event.message.text || "").trim();
    const replyToken = event.replyToken || "";
    if (!text || !replyToken) {
      continue;
    }

    const sheet = getSuppliesSheet();
    const values = sheet.getDataRange().getDisplayValues();
    const replyText = generateAmazonLinkReply(
      geminiApiKey,
      geminiModel,
      text,
      values,
    );

    replyToLine(lineAccessToken, replyToken, JSON.stringify(replyText));
    processed += 1;
  }

  return jsonResponse({ ok: true, processed });
}

function generateAmazonLinkReply(
  geminiApiKey: string,
  geminiModel: string,
  text: string,
  values: string[][],
): string | GeminiReplyJson {
  const prompt = [
    "あなたはLINEで購買候補を返すアシスタントです。",
    "ユーザー入力と商品一覧を見て、必要なAmazon商品リンクのみを抽出してください。",
    "JSON形式で出力して、以下のスキーマ通りに返答してください。",
    "スキーマ： name: 商品名（ユーザー入力から抽出）, count: 商品の個数（ユーザー入力から抽出）, product_url: Amazon商品リンク, message: ユーザー向けの短い日本語説明。",
    `ユーザー入力: ${text}`,
    `商品一覧: ${JSON.stringify(values)}`,
  ].join("\n");

  const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(geminiModel)}:generateContent?key=${encodeURIComponent(geminiApiKey)}`;
  const response = UrlFetchApp.fetch(endpoint, {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 1.0,
        responseMimeType: "application/json",
      },
    }),
    muteHttpExceptions: true,
  });

  const status = response.getResponseCode();
  if (status < 200 || status >= 300) {
    return `リンク取得に失敗しました（HTTP ${status}）`;
  }

  const payload = JSON.parse(response.getContentText()) as GeminiResponse;
  const textOutput =
    payload.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || "";
  const parsed = parseGeminiJson(textOutput)?.[0] as GeminiReplyJson;
  if (!parsed) {
    return "候補リンクを生成できませんでした。";
  }

  return parsed;
}

function parseGeminiJson(text: string): Record<string, unknown> | null {
  if (!text) {
    return null;
  }

  const normalized = text
    .replace(/^```json\s*/i, "")
    .replace(/^```\s*/i, "")
    .replace(/\s*```$/, "")
    .trim();
  try {
    const parsed = JSON.parse(normalized) as unknown;
    return typeof parsed === "object" && parsed !== null
      ? (parsed as Record<string, unknown>)
      : null;
  } catch (_error) {
    return null;
  }
}

function replyToLine(
  channelAccessToken: string,
  replyToken: string,
  text: string,
): void {
  UrlFetchApp.fetch("https://api.line.me/v2/bot/message/reply", {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify({
      replyToken,
      messages: [{ type: "text", text }],
    }),
    headers: {
      Authorization: `Bearer ${channelAccessToken}`,
    },
    muteHttpExceptions: true,
  });
}

function getProperty(key: string): string {
  return PropertiesService.getScriptProperties().getProperty(key) || "";
}

function getSuppliesSheet(): GoogleAppsScript.Spreadsheet.Sheet {
  const spreadsheetId = getProperty("GOOGLE_SHEET_ID");
  const spreadsheet = spreadsheetId
    ? SpreadsheetApp.openById(spreadsheetId)
    : SpreadsheetApp.getActiveSpreadsheet();

  if (!spreadsheet) {
    throw new Error(
      "Spreadsheet not found. Set GOOGLE_SHEET_ID in Script Properties.",
    );
  }

  const sheet = spreadsheet.getSheetByName("備品");
  if (!sheet) {
    throw new Error("Sheet '備品' not found.");
  }

  return sheet;
}

function jsonResponse(body: unknown): GoogleAppsScript.Content.TextOutput {
  const output = ContentService.createTextOutput(JSON.stringify(body));
  output.setMimeType(ContentService.MimeType.JSON);
  return output;
}
