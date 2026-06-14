import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const client = axios.create({ baseURL: API_BASE, timeout: 30000 });

export interface ContentItem {
  id: string; title: string; url: string; source: string; snippet?: string;
  content: string; topic?: string; topics?: string; published_at: string;
  author?: string; engagement?: number; source_type?: string;
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
  const { data } = await client.get<ContentItem[]>('/search', { params });
  return data;
}

export async function getByTopic(topic: string, limit = 50): Promise<ContentItem[]> {
  const { data } = await client.get<ContentItem[]>(`/topics/${encodeURIComponent(topic)}`, { params: { limit } });
  return data;
}

export async function getBySource(source: string, limit = 50): Promise<ContentItem[]> {
  const { data } = await client.get<ContentItem[]>(`/sources/${encodeURIComponent(source)}`, { params: { limit } });
  return data;
}

export async function getRecent(limit = 20): Promise<ContentItem[]> {
  const { data } = await client.get<ContentItem[]>('/recent', { params: { limit } });
  return data;
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

export async function ragQuery(question: string): Promise<any> {
  const { data } = await client.post('/ai/rag/query', { question });
  return data;
}

export default client;
