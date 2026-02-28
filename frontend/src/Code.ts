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

function doPost(e: GoogleAppsScript.Events.DoPost): GoogleAppsScript.Content.TextOutput {
  const backendUrl = getProperty("BACKEND_URL");
  const backendApiKey = getProperty("BACKEND_API_KEY");
  const lineAccessToken = getProperty("LINE_CHANNEL_ACCESS_TOKEN");

  if (!backendUrl || !backendApiKey || !lineAccessToken) {
    return jsonResponse({ ok: false, error: "Required Script Properties are missing" });
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

    const replyMessage = handleLineTextEvent(backendUrl, backendApiKey, text, event.source?.userId || "");
    replyToLine(lineAccessToken, replyToken, replyMessage);
    processed += 1;
  }

  return jsonResponse({ ok: true, processed });
}

function handleLineTextEvent(
  backendUrl: string,
  backendApiKey: string,
  text: string,
  userId: string,
): string {
  const req = {
    text,
    user_id: userId,
    reply_token: "",
  };

  const response = UrlFetchApp.fetch(`${backendUrl}/api/line/intents`, {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(req),
    headers: {
      "X-API-Key": backendApiKey,
    },
    muteHttpExceptions: true,
  });

  const status = response.getResponseCode();
  if (status < 200 || status >= 300) {
    return `購買依頼の登録に失敗しました（HTTP ${status}）`;
  }

  const data = JSON.parse(response.getContentText()) as BackendIntentResponse;
  return [
    "購買依頼を受け付けました。",
    `商品: ${data.item_name}`,
    `数量: ${data.quantity}`,
    `注文ID: ${data.order_id}`,
  ].join("\n");
}

function replyToLine(channelAccessToken: string, replyToken: string, text: string): void {
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

function jsonResponse(body: unknown): GoogleAppsScript.Content.TextOutput {
  const output = ContentService.createTextOutput(JSON.stringify(body));
  output.setMimeType(ContentService.MimeType.JSON);
  return output;
}
