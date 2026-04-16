export type ReviewState = "unreviewed" | "needs-review" | "reviewed";

export type AnalysisScope =
  | {
      kind: "single";
      callIds: [string];
      label: string;
    }
  | {
      kind: "group";
      callIds: string[];
      label: string;
    };

export type CallRecord = {
  id: string;
  title: string;
  source: "upload" | "api" | "demo";
  status: "ready" | "processing" | "failed";
  declaredLanguage: string;
  speakerCount: number;
  durationSeconds: number;
  uploadedAt: string;
  region: string;
  reviewState: ReviewState;
  summary: string;
  audioUrl: string;
};

export type CallGroup = {
  id: string;
  name: string;
  callIds: string[];
  createdAt: string;
  purpose: string;
};

export type MetricCard = {
  id: string;
  label: string;
  value: string;
  delta?: string;
  trend?: "up" | "down" | "neutral";
  experimental?: boolean;
  confidence?: "high" | "medium" | "low";
};

export type WaveformTrack = {
  id: string;
  label: string;
  type: "speaker" | "transcript" | "pause" | "overlap" | "question" | "behavior" | "emotion" | "evidence";
  items: WaveformTrackItem[];
};

export type WaveformTrackItem = {
  id: string;
  label: string;
  startMs: number;
  endMs: number;
  tone?: "default" | "secondary" | "destructive" | "muted";
  experimental?: boolean;
};

export type BehaviorSignalTrack = {
  id: string;
  label: string;
  state: "computed" | "not-computed";
  score: number | null;
  confidence: "high" | "medium" | "low";
};

export type EmotionSignalTrack = {
  id: string;
  label: string;
  state: "computed" | "not-computed";
  score: number | null;
  confidence: "high" | "medium" | "low";
  experimental: true;
};

export type EvidenceRef = {
  id: string;
  label: string;
  timestampMs: number;
  type: "turn" | "event" | "metric";
};

export type QuestionInsight = {
  id: string;
  questionText: string;
  answerSpeaker: string;
  responseLatencyMs: number;
  answerLengthSeconds: number;
  hesitationIndex: number;
  behaviorSummary: string;
  emotionSummary: string;
  evidenceRefs: EvidenceRef[];
};

export type ProcessingWarning = {
  id: string;
  level: "info" | "warning" | "error";
  message: string;
};

export type ModelRunPlaceholder = {
  id: string;
  name: string;
  version: string;
  status: "placeholder";
};

export type AnalysisDataset = {
  scope: AnalysisScope;
  calls: CallRecord[];
  headlineMetrics: MetricCard[];
  behaviorSignals: BehaviorSignalTrack[];
  emotionSignals: EmotionSignalTrack[];
  waveformTracks: WaveformTrack[];
  questionInsights: QuestionInsight[];
  evidenceRefs: EvidenceRef[];
  processingWarnings: ProcessingWarning[];
  modelRuns: ModelRunPlaceholder[];
  rawJson: Record<string, unknown>;
};
