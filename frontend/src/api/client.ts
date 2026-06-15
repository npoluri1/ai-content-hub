import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const client = axios.create({ baseURL: API_BASE, timeout: 30000 });

export interface ContentItem {
  id: string; title: string; url: string; source: string; snippet?: string;
  content: string; topic?: string; topics?: string; published_at: string;
  author?: string; engagement?: number; source_type?: string;
  image_urls?: string[]; video_url?: string; audio_url?: string;
}

function normalizeItem(raw: any): ContentItem {
  if (!raw || typeof raw !== 'object') return { id:'', title:'', url:'', source:'', content:'', published_at:'' };
  const meta = raw.metadata || {};
  return {
    id: raw.id || meta.id || '',
    title: raw.title || meta.title || '',
    url: raw.url || meta.url || '',
    source: raw.source || meta.source || '',
    snippet: raw.snippet || meta.snippet || (raw.content || '').slice(0, 300),
    content: raw.content || meta.content || '',
    topic: raw.topic || meta.topic || '',
    topics: raw.topics || meta.topics || '',
    published_at: raw.published_at || meta.published_at || '',
    author: raw.author || meta.author || '',
    engagement: raw.engagement ?? meta.engagement ?? 0,
    source_type: raw.source_type || meta.source_type || '',
    image_urls: raw.image_urls || meta.image_urls || [],
    video_url: raw.video_url || meta.video_url || '',
    audio_url: raw.audio_url || meta.audio_url || (meta.audio_url || ''),
  };
}

export interface Stats {
  total_items: number; by_source: Record<string, number>; by_topic: Record<string, number>;
}

export interface DigestResult { digest: string }

export async function fetchStats(): Promise<Stats> {
  const { data } = await client.get<Stats>('/stats');
  return data;
}

export async function searchItems(q: string, source?: string, limit = 50): Promise<ContentItem[]> {
  const params: Record<string,string|number> = { q, limit };
  if (source) params.source = source;
  const { data } = await client.get<any[]>('/search', { params });
  return (data || []).map(normalizeItem);
}

export async function getByTopic(topic: string, limit = 50): Promise<ContentItem[]> {
  const { data } = await client.get<any[]>(`/topics/${encodeURIComponent(topic)}`, { params: { limit } });
  return (data || []).map(normalizeItem);
}

export async function getBySource(source: string, limit = 50): Promise<ContentItem[]> {
  const { data } = await client.get<any[]>(`/sources/${encodeURIComponent(source)}`, { params: { limit } });
  return (data || []).map(normalizeItem);
}

export async function getRecent(limit = 20): Promise<ContentItem[]> {
  const { data } = await client.get<any[]>('/recent', { params: { limit } });
  return (data || []).map(normalizeItem);
}

export async function getDigest(): Promise<DigestResult> {
  const { data } = await client.get<DigestResult>('/digest');
  return data;
}

export async function getTopics(): Promise<string[]> {
  const { data } = await client.get<Stats>('/stats');
  return Object.keys(data.by_topic).filter(Boolean).sort();
}

export async function getSources(): Promise<{id:string;name:string;count:number}[]> {
  const { data } = await client.get<Stats>('/stats');
  return Object.entries(data.by_source).map(([name, count]) => ({ id: name, name, count }));
}

export async function runAllSources(): Promise<void> {
  await client.post('/run');
}

export async function triggerScrape(source: string): Promise<void> {
  await client.post(`/run?sources=${source}`);
}

export async function analyzeSentiment(text: string): Promise<any> {
  const { data } = await client.post('/mlops/sentiment', { text });
  return data;
}

export async function detectPII(text: string): Promise<any> {
  const { data } = await client.post('/compliance/pii/detect', { text });
  return data;
}

export async function moderateContent(text: string): Promise<any> {
  const { data } = await client.post('/compliance/moderate', { text });
  return data;
}

export async function ragQuery(question: string, model_id?: string): Promise<any> {
  const { data } = await client.post('/ai/rag/query', { question, model_id });
  return data;
}

// === Model Management ===

export interface ModelInfo {
  id: string; name: string; provider: string; tier: 'free' | 'premium';
  description: string; context_window: number; supports_streaming: boolean;
  supports_vision: boolean; supports_tools: boolean; supports_image: boolean;
  supports_file: boolean; supports_audio: boolean; supports_video: boolean;
  cost_per_1k_input: number; cost_per_1k_output: number;
}

export interface ModelListResponse {
  active_model: ModelInfo; active_tier: string;
  free_models: ModelInfo[]; premium_models: ModelInfo[];
}

export async function getModels(): Promise<ModelListResponse> {
  const { data } = await client.get<ModelListResponse>('/ai/models');
  return data;
}

export async function switchModel(modelId: string): Promise<any> {
  const { data } = await client.post('/ai/models/switch', { model_id: modelId });
  return data;
}

export async function switchTier(tier: string): Promise<any> {
  const { data } = await client.post('/ai/models/tier', { tier });
  return data;
}

export async function getActiveModel(): Promise<ModelInfo> {
  const { data } = await client.get<ModelInfo>('/ai/models/active');
  return data;
}

export default client;
