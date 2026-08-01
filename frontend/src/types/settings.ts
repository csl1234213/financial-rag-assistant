export type LLMProvider =
  | 'deepseek'
  | 'gemini'
  | 'openai'
  | 'anthropic'
  | 'doubao';

export interface ProviderSettings {
  provider: LLMProvider;
  display_name: string;
  configured: boolean;
  is_default: boolean;
  key_hint: string | null;
  model: string;
  models: string[];
  updated_at: string | null;
}

export interface LLMSettingsResponse {
  providers: ProviderSettings[];
  default_provider: LLMProvider | null;
}

export interface UpdateProviderSettingsRequest {
  api_key?: string;
  model?: string;
}
