import type { AppConfig } from "../config";

interface GeminiAttemptResult {
  text: string;
}

type ComboOutcome = "OK" | "QUOTA" | "TIMEOUT" | "ERR";

/**
 * محاولة واحدة لاستدعاء Gemini بمفتاح ونموذج معيّنين.
 */
async function attempt(
  key: string,
  model: string,
  prompt: string,
  imageBase64: string,
  timeoutMs: number
): Promise<GeminiAttemptResult> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);

  try {
    const resp = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(
        key
      )}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [
            {
              parts: [
                { text: prompt },
                { inline_data: { mime_type: "image/jpeg", data: imageBase64 } },
              ],
            },
          ],
        }),
        signal: ctrl.signal,
      }
    );

    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${errText.slice(0, 200)}`);
    }

    const json = await resp.json();
    const text =
      json?.candidates?.[0]?.content?.parts
        ?.map((p: { text?: string }) => p.text || "")
        .join("") || "";

    return { text };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * يستخرج نص صفحة واحدة عبر Gemini Vision، مع تدوير على عدة مفاتيح/نماذج
 * والتعامل مع حدود الحصة (429/503) بفترات تبريد، وحظر دائم للمفاتيح/النماذج
 * التي ترفض الطلب بشكل نهائي (400/401/403/404).
 *
 * يرمي خطأ فقط بعد استنفاد كل التركيبات الممكنة.
 */
export async function ocrPageImage(
  imageBase64: string,
  config: Pick<
    AppConfig,
    | "geminiKeys"
    | "geminiModel"
    | "geminiFallbackModels"
    | "geminiPrompt"
    | "requestTimeoutMs"
    | "maxRetriesPerPage"
  >
): Promise<string> {
  const models = [
    config.geminiModel,
    ...config.geminiFallbackModels.filter((m) => m !== config.geminiModel),
  ];

  const combos = config.geminiKeys.flatMap((key, keyIdx) =>
    models.map((model) => ({
      key,
      model,
      label: `k${keyIdx + 1}/${model}`,
    }))
  );

  const banned = new Set<string>();
  const cooldownUntil = new Map<string, number>();

  for (let round = 0; round < config.maxRetriesPerPage; round++) {
    let anyOnCooldown = false;
    let triedAny = false;

    for (const combo of combos) {
      if (banned.has(combo.label)) continue;

      const cooldown = cooldownUntil.get(combo.label);
      if (cooldown && cooldown > Date.now()) {
        anyOnCooldown = true;
        continue;
      }

      triedAny = true;

      const outcome = await new Promise<{
        state: ComboOutcome;
        text: string;
      }>((resolve) => {
        const timeout = setTimeout(
          () => resolve({ state: "TIMEOUT", text: "" }),
          50_000
        );

        attempt(
          combo.key,
          combo.model,
          config.geminiPrompt,
          imageBase64,
          config.requestTimeoutMs
        )
          .then((r) => {
            clearTimeout(timeout);
            resolve({ state: "OK", text: r.text });
          })
          .catch((e: Error) => {
            clearTimeout(timeout);
            const isQuota = /429|503/.test(e.message);
            resolve({ state: isQuota ? "QUOTA" : "ERR", text: e.message });
          });
      });

      if (outcome.state === "OK" && outcome.text.trim()) {
        return outcome.text.trim();
      }

      if (outcome.state === "QUOTA") {
        cooldownUntil.set(combo.label, Date.now() + 45_000);
        anyOnCooldown = true;
      } else if (outcome.state === "TIMEOUT") {
        cooldownUntil.set(combo.label, Date.now() + 30_000);
        anyOnCooldown = true;
      } else if (/HTTP 4(0[0-9]|1[0-9]|04)/.test(outcome.text)) {
        // رفض نهائي (مفتاح غير صالح، نموذج غير موجود...) — احظر هذا التركيب فقط
        banned.add(combo.label);
      } else {
        anyOnCooldown = true;
      }
    }

    if (banned.size === combos.length) {
      throw new Error("كل مفاتيح/نماذج Gemini مرفوضة نهائيًا لهذه الصفحة.");
    }
    if (!triedAny || !anyOnCooldown) break;

    await new Promise((r) => setTimeout(r, 60_000));
  }

  throw new Error("فشلت معالجة الصفحة عبر جميع المفاتيح/النماذج المتاحة.");
}
