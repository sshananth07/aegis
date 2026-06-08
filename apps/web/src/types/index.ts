export interface Prompt {
  id: string
  name: string
  description: string | null
  created_at: string
}

export interface PromptVersion {
  id: string
  prompt_id: string
  version: number
  template: string
  created_at: string
}

export interface Evaluation {
  id: string
  prompt_version_id: string
  provider: string
  response: string | null
  status: string
  score: number | null
  score_details: Record<string, number | null> | null
  latency_ms: number | null
  token_usage: number | null
  token_usage_estimated: boolean | null
  cost: number | null
  created_at: string
}

export interface Dataset {
  id: string
  name: string
  description: string | null
  created_at: string
  items: DatasetItem[]
}

export interface DatasetItem {
  id: string
  dataset_id: string
  input_text: string
  expected_output: string | null
  check_json: boolean
  required_keywords: string[]
  required_json_fields: string[]
  created_at: string
}

export interface BenchmarkSuite {
  id: string
  name: string
  description: string | null
  prompt_id: string
  prompt_version_id: string
  dataset_id: string
  providers: string[]
  pass_threshold: number
  created_at: string
}

export interface BenchmarkRun {
  id: string
  suite_id: string
  status: string
  total_cases: string
  passed_cases: string
  avg_latency_ms: number | null
  avg_score: number | null
  avg_cost: number | null
  results: BenchmarkResult[] | null
  created_at: string
}

export interface BenchmarkResult {
  evaluation_group_id: string
  provider: string
  input: string
  response: string | null
  score: number
  score_details: Record<string, unknown>
  failure_reasons: string[]
  latency_ms: number
  token_usage: number
  cost: number
  passed: boolean
  divergence_score?: number
  divergence_detected?: boolean
  rankings?: ProviderRanking[]
  error?: string | null
}

export interface ProviderRanking {
  provider: string
  score: number
  latency_ms: number
  cost: number
  passed: boolean
  rank: number
}

export interface APIKey {
  id: string
  user_id: string
  name: string
  key_prefix: string
  scopes: string[]
  last_used_at: string | null
  expires_at: string | null
  revoked: boolean
  created_at: string
}

export interface APIKeyCreateResponse extends APIKey {
  key: string
export interface Job {
  id: string
  job_type: string
  status: string
  entity_id: string | null
  entity_type: string | null
  result_id: string | null
  progress: number
  total: number
  error: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface Webhook {
  id: string
  user_id: string
  url: string
  event_types: string[]
  active: boolean
  created_at: string
}

export interface WebhookCreateResponse extends Webhook {
  secret: string
}

export interface WebhookDelivery {
  id: string
  webhook_id: string
  event_type: string
  status: string
  response_code: number | null
  error_message: string | null
  attempted_at: string
}
