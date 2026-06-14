import axios from 'axios';

const client = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000,
});

export interface Stats {
  total_items: number;
  total_sources: number;
  total_topics: number;
  topic_distribution: Record<string, number>;
  source_health: Record<string, string>;
}

export interface ContentItem {
  id: string;
  title: string;
  url: string;
  source: string;
  snippet: string;
  topic?: string;
  content: string;
  published_at: string;
  ingested_at: string;
}

export interface Source {
  id: string;
  name: string;
  status: string;
  last_crawl: string;
  items_count: number;
  url: string;
}

export interface DigestResult {
  digest: string;
  generated_at: string;
  download_url: string;
}

export interface ScheduleConfig {
  interval_seconds: number;
  sources: string[];
  active: boolean;
}

export interface PipelineResult {
  status: string;
  message: string;
  new_items: number;
}

export async function fetchStats(): Promise<Stats> {
  const { data } = await client.get<Stats>('/api/stats');
  return data;
}

export async function searchItems(
  q: string,
  source?: string,
  limit?: number
): Promise<ContentItem[]> {
  const params: Record<string, string | number> = { q };
  if (source) params.source = source;
  if (limit) params.limit = limit;
  const { data } = await client.get<ContentItem[]>('/api/search', { params });
  return data;
}

export async function getByTopic(topic: string): Promise<ContentItem[]> {
  const { data } = await client.get<ContentItem[]>(`/api/topics/${encodeURIComponent(topic)}`);
  return data;
}

export async function getBySource(source: string): Promise<ContentItem[]> {
  const { data } = await client.get<ContentItem[]>(`/api/sources/${encodeURIComponent(source)}`);
  return data;
}

export async function runPipeline(sources: string[]): Promise<PipelineResult> {
  const { data } = await client.post<PipelineResult>('/api/pipeline', { sources });
  return data;
}

export async function getRecent(): Promise<ContentItem[]> {
  const { data } = await client.get<ContentItem[]>('/api/recent');
  return data;
}

export async function getDigest(): Promise<DigestResult> {
  const { data } = await client.get<DigestResult>('/api/digest');
  return data;
}

export async function getSources(): Promise<Source[]> {
  const { data } = await client.get<Source[]>('/api/sources');
  return data;
}

export async function getTopics(): Promise<string[]> {
  const { data } = await client.get<string[]>('/api/topics');
  return data;
}

export async function triggerScrape(sourceId: string): Promise<PipelineResult> {
  const { data } = await client.post<PipelineResult>(`/api/sources/${encodeURIComponent(sourceId)}/scrape`);
  return data;
}

export async function getSchedule(): Promise<ScheduleConfig> {
  const { data } = await client.get<ScheduleConfig>('/api/schedule');
  return data;
}

export async function updateSchedule(config: ScheduleConfig): Promise<ScheduleConfig> {
  const { data } = await client.put<ScheduleConfig>('/api/schedule', config);
  return data;
}

export default client;
