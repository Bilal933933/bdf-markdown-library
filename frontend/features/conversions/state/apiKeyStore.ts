import { create } from "zustand";
import { getStoredApiKey, setStoredApiKey } from "@/lib/apiClient";

type ApiKeyState = {
  apiKey: string;
  setApiKey: (key: string) => void;
};

export const useApiKeyStore = create<ApiKeyState>((set) => ({
  apiKey: getStoredApiKey() ?? "",
  setApiKey: (key) => {
    setStoredApiKey(key);
    set({ apiKey: key });
  },
}));
