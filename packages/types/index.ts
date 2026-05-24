// Shared types used across frontend and any future packages

export type Provider = "openai" | "gemini" | "ollama"

export type EvaluationStatus = 
  | "pending"
  | "running"
  | "completed"
  | "failed"

export type ReviewStatus =
  | "pending"
  | "approved"
  | "rejected"

export interface TraceEvent {
  trace_id: string
  evaluation_id: string
  event_type: string
  provider?: Provider
  latency_ms?: number
  timestamp: string
} 