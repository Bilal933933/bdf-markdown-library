"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiKeyStore } from "../state/apiKeyStore";

export function ApiKeyBar() {
  const { apiKey, setApiKey } = useApiKeyStore();
  const [draft, setDraft] = useState(apiKey);

  return (
    <div className="flex gap-2">
      <Input
        type="password"
        placeholder="مفتاح API (اختباري محليًا)"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        className="h-10 rounded-xl border-2 border-[#9ec1e6] bg-white shadow-sm"
      />
      <Button
        onClick={() => setApiKey(draft.trim())}
        className="h-10 shrink-0 rounded-lg bg-[#143a75] px-6 text-white hover:bg-[#1e4da1]"
      >
        حفظ
      </Button>
    </div>
  );
}
