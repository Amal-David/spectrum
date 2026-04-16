export type ReviewState = "unreviewed" | "needs-review" | "reviewed"

export type QualityTier = "healthy" | "watch" | "risky"

export type TrustTier = "trusted" | "discounted" | "review"

export type BusinessOutcome = "resolved" | "escalated" | "abandoned" | "converted"

export type AnalysisScope =
  | {
      kind: "single"
      callIds: [string]
      label: string
    }
  | {
      kind: "group"
      callIds: string[]
      label: string
    }

export type AudioAsset = {
  originalUrl: string
  normalizedUrl: string
  telephonyUrl?: string
}

export type CallRecord = {
  id: string
  title: string
  source: "upload" | "api" | "demo"
  status: "ready" | "processing" | "failed"
  sessionType: "sales" | "support" | "collections" | "research"
  language: string
  declaredLanguage: string
  state: string
  stateCode: string
  district?: string
  region: string
  speakerCount: number
  durationSeconds: number
  uploadedAt: string
  reviewState: ReviewState
  summary: string
  audioUrl: string
  audioAsset: AudioAsset
  qualityTier: QualityTier
  trustTier: TrustTier
  businessOutcome: BusinessOutcome
  workflowId: string
  workflowLabel: string
  agentLabel: string
  promptVersion: string
  qualityScore: number
  trustScore: number
  frictionScore: number
  avgSnrDb: number
  explainabilityFlags: string[]
  environmentTags: string[]
  topQuestionIssue: string
}

export type CallGroup = {
  id: string
  name: string
  callIds: string[]
  createdAt: string
  purpose: string
}

export type MetricCard = {
  id: string
  label: string
  value: string
  delta?: string
  trend?: "up" | "down" | "neutral"
  experimental?: boolean
  confidence?: "high" | "medium" | "low"
}

export type BusinessMetric = {
  id: string
  label: string
  value: string
  delta?: string
  trend?: "up" | "down" | "neutral"
  description: string
}

export type BusinessTrendPoint = {
  date: string
  conversations: number
  completions: number
  escalations: number
  containmentRate: number
}

export type BusinessOutcomeMixPoint = {
  label: string
  resolved: number
  escalated: number
  abandoned: number
  converted: number
}

export type DemographicSlice = {
  id: string
  state: string
  district?: string
  region: string
  language: string
  urbanicity?: "metro" | "urban" | "semi-urban"
  callVolume: number
  completionRate: number
  escalationRate: number
  qualityScore: number
  trustScore: number
  frictionScore: number
  hesitationScore: number
  rapportScore: number
  frustrationRisk: number
  avgSnrDb: number
}

export type GeographySummary = {
  state: string
  stateCode: string
  region: string
  callVolume: number
  completionRate: number
  escalationRate: number
  avgSnrDb: number
  hesitationScore: number
  frictionScore: number
  frustrationRisk: number
  trustTier: TrustTier
}

export type StatePerformancePoint = {
  state: string
  stateCode: string
  x: number
  y: number
  callVolume: number
  completionRate: number
  escalationRate: number
  avgSnrDb: number
  trustScore: number
}

export type LanguageDistribution = {
  language: string
  callVolume: number
  completionRate: number
}

export type EmotionAggregate = {
  id: string
  demographicKey: string
  demographicLabel: string
  emotion: string
  score: number
  confidence: "high" | "medium" | "low"
  sampleSize: number
  trustTier: TrustTier
}

export type BehaviorAggregate = {
  id: string
  demographicKey: string
  demographicLabel: string
  fillerDensity: number
  interruptionRate: number
  overlapRate: number
  responseLatencyMs: number
  reciprocity: number
  engagementDrift: number
  directness: number
  hesitationScore: number
}

export type QualityTrendPoint = {
  date: string
  avgSnrDb: number
  noisySegmentRate: number
  vadFpCount: number
  vadFnCount: number
  insightDiscountRate: number
}

export type EnvironmentTagMetric = {
  tag: string
  count: number
}

export type AgentPerformanceSlice = {
  id: string
  workflowLabel: string
  agentLabel: string
  promptVersion: string
  campaign: string
  volume: number
  successRate: number
  escalationRate: number
  qualityScore: number
  trustScore: number
  frictionScore: number
}

export type ReviewQueueItem = {
  id: string
  title: string
  detail: string
  severity: "critical" | "watch" | "info"
  href: string
}

export type DashboardDataset = {
  businessMetrics: BusinessMetric[]
  businessTrend: BusinessTrendPoint[]
  outcomeMix: BusinessOutcomeMixPoint[]
  statePerformance: StatePerformancePoint[]
  geographySummaries: GeographySummary[]
  languageDistribution: LanguageDistribution[]
  demographicSlices: DemographicSlice[]
  emotionAggregates: EmotionAggregate[]
  behaviorAggregates: BehaviorAggregate[]
  qualityTrend: QualityTrendPoint[]
  environmentTags: EnvironmentTagMetric[]
  agentPerformance: AgentPerformanceSlice[]
  reviewQueue: ReviewQueueItem[]
}

export type WaveformTrack = {
  id: string
  label: string
  type:
    | "speaker"
    | "transcript"
    | "pause"
    | "overlap"
    | "question"
    | "behavior"
    | "emotion"
    | "evidence"
    | "quality"
    | "event"
  items: WaveformTrackItem[]
}

export type WaveformTrackItem = {
  id: string
  label: string
  startMs: number
  endMs: number
  tone?: "default" | "secondary" | "destructive" | "muted"
  experimental?: boolean
}

export type BehaviorSignalTrack = {
  id: string
  label: string
  state: "computed" | "not-computed"
  score: number | null
  confidence: "high" | "medium" | "low"
}

export type EmotionSignalTrack = {
  id: string
  label: string
  state: "computed" | "not-computed"
  score: number | null
  confidence: "high" | "medium" | "low"
  experimental: true
}

export type EvidenceRef = {
  id: string
  label: string
  timestampMs: number
  type: "turn" | "event" | "metric"
}

export type QuestionInsight = {
  id: string
  questionText: string
  answerSpeaker: string
  responseLatencyMs: number
  answerLengthSeconds: number
  hesitationIndex: number
  directnessScore: number
  affectTag: string
  qualityMask: string[]
  behaviorSummary: string
  emotionSummary: string
  evidenceRefs: EvidenceRef[]
}

export type ProcessingWarning = {
  id: string
  level: "info" | "warning" | "error"
  message: string
}

export type ModelRunPlaceholder = {
  id: string
  name: string
  version: string
  status: "placeholder"
}

export type AnalysisDataset = {
  scope: AnalysisScope
  calls: CallRecord[]
  headlineMetrics: MetricCard[]
  qualityMetrics: MetricCard[]
  structureMetrics: MetricCard[]
  businessMetrics: MetricCard[]
  behaviorSignals: BehaviorSignalTrack[]
  emotionSignals: EmotionSignalTrack[]
  waveformTracks: WaveformTrack[]
  questionInsights: QuestionInsight[]
  evidenceRefs: EvidenceRef[]
  processingWarnings: ProcessingWarning[]
  modelRuns: ModelRunPlaceholder[]
  rawJson: Record<string, unknown>
}
