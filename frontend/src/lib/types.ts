export interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "analyst" | "viewer";
  org_id: string;
}

export interface Overview {
  total_mentions: number;
  positive_pct: number;
  negative_pct: number;
  avg_per_day: number;
}

export interface TrendPoint {
  time: string;
  count: number;
  positive: number;
  negative: number;
  neutral: number;
}

export interface SentimentBreakdown {
  positive: number;
  negative: number;
  neutral: number;
  timeline: TrendPoint[];
}

export interface KeywordStat { word: string; count: number; sentiment: string }
export interface SourceStat { name: string; count: number; sentiment: string }
export interface Spike { time: string; keyword: string; magnitude: number; z_score: number; count: number }

export interface Mention {
  id: string;
  keyword_id: string;
  source: string;
  source_url: string;
  title: string | null;
  content: string;
  author: string | null;
  published_at: string;
  upvotes: number;
  comment_count: number;
}

export interface AlertRule {
  id: string;
  name: string;
  condition: Record<string, unknown>;
  channels: string[];
  is_enabled: boolean;
  created_at: string;
}

export interface AlertItem {
  id: string;
  rule_id: string;
  keyword: string;
  trigger_reason: string;
  mention_count: number;
  channel: string;
  is_read: boolean;
  triggered_at: string;
}

export interface Report {
  id: string;
  type: "pdf" | "csv";
  status: "queued" | "processing" | "done" | "failed";
  download_url: string | null;
  expires_at: string | null;
  file_size_bytes: number | null;
  created_at: string;
  completed_at: string | null;
}
