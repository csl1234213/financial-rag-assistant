import { deleteJson, getJson, putJson } from './client';
import {
  createProviderSettingsRequest,
  parseLLMSettingsResponse,
  parseProviderSettings,
} from './settingsContract';
import type {
  LLMProvider,
  LLMSettingsResponse,
  ProviderSettings,
} from '../types/settings';

const llmSettingsEndpoint = '/v1/settings/llm';

function providerEndpoint(provider: LLMProvider): string {
  return `${llmSettingsEndpoint}/${provider}`;
}

export async function getLLMSettings(): Promise<LLMSettingsResponse> {
  const payload = await getJson<unknown>(llmSettingsEndpoint);
  return parseLLMSettingsResponse(payload);
}

export async function updateLLMProvider(
  provider: LLMProvider,
  apiKey: string,
  model: string,
): Promise<ProviderSettings> {
  const payload = await putJson<unknown>(
    providerEndpoint(provider),
    createProviderSettingsRequest(apiKey, model),
  );
  return parseProviderSettings(payload);
}

export async function clearLLMProvider(
  provider: LLMProvider,
): Promise<ProviderSettings> {
  const payload = await deleteJson<unknown>(providerEndpoint(provider));
  return parseProviderSettings(payload);
}

export async function setDefaultLLMProvider(
  provider: LLMProvider,
): Promise<LLMSettingsResponse> {
  const payload = await putJson<unknown>(
    `${llmSettingsEndpoint}/default`,
    { provider },
  );
  return parseLLMSettingsResponse(payload);
}
