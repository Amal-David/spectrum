import type {
  AnalysisDataset,
  AnalysisScope,
  BehaviorSignalTrack,
  CallGroup,
  CallRecord,
  EmotionSignalTrack,
  EvidenceRef,
  MetricCard,
  ModelRunPlaceholder,
  ProcessingWarning,
  QuestionInsight,
  WaveformTrack,
} from "@/lib/types";

export const demoAudioUrl = "/demo-call.wav";

export const calls: CallRecord[] = [
  {
    id: "call-001",
    title: "Founder interview - pricing objections",
    source: "demo",
    status: "ready",
    declaredLanguage: "English + Hindi",
    speakerCount: 2,
    durationSeconds: 1820,
    uploadedAt: "2026-04-14T09:15:00.000Z",
    region: "India",
    reviewState: "needs-review",
    summary: "Long hesitation after pricing and ROI questions with one interruption cluster near the middle.",
    audioUrl: demoAudioUrl,
  },
  {
    id: "call-002",
    title: "Support QA - onboarding confusion",
    source: "upload",
    status: "ready",
    declaredLanguage: "English",
    speakerCount: 2,
    durationSeconds: 1260,
    uploadedAt: "2026-04-14T13:45:00.000Z",
    region: "United States",
    reviewState: "unreviewed",
    summary: "High overlap early, then a stable handoff after the agent clarifies setup steps.",
    audioUrl: demoAudioUrl,
  },
  {
    id: "call-003",
    title: "Research session - multilingual flow",
    source: "api",
    status: "ready",
    declaredLanguage: "English + Tamil",
    speakerCount: 3,
    durationSeconds: 2140,
    uploadedAt: "2026-04-15T11:10:00.000Z",
    region: "India",
    reviewState: "reviewed",
    summary: "Multiple code-switch boundaries with low overlap and one long pause before the closing decision.",
    audioUrl: demoAudioUrl,
  },
  {
    id: "call-004",
    title: "Sales discovery - compliance blockers",
    source: "upload",
    status: "processing",
    declaredLanguage: "English",
    speakerCount: 2,
    durationSeconds: 980,
    uploadedAt: "2026-04-15T16:00:00.000Z",
    region: "United Kingdom",
    reviewState: "unreviewed",
    summary: "Still processing artifacts for timing and evidence generation.",
    audioUrl: demoAudioUrl,
  },
  {
    id: "call-005",
    title: "Pilot agent eval - handoff quality",
    source: "demo",
    status: "ready",
    declaredLanguage: "English",
    speakerCount: 2,
    durationSeconds: 1540,
    uploadedAt: "2026-04-16T08:25:00.000Z",
    region: "Singapore",
    reviewState: "needs-review",
    summary: "Balanced talk time, elevated hesitation around policy exceptions, and moderate frustration markers.",
    audioUrl: demoAudioUrl,
  },
];

export const callGroups: CallGroup[] = [
  {
    id: "group-001",
    name: "Pricing friction cluster",
    callIds: ["call-001", "call-005"],
    createdAt: "2026-04-16T07:30:00.000Z",
    purpose: "Compare hesitation and affect around pricing or policy questions.",
  },
  {
    id: "group-002",
    name: "Onboarding conversations",
    callIds: ["call-002", "call-003"],
    createdAt: "2026-04-15T18:10:00.000Z",
    purpose: "Inspect how multilingual support changes turn-taking and overlap patterns.",
  },
];

export const dashboardMetrics: MetricCard[] = [
  { id: "m1", label: "Calls analyzed", value: "42", delta: "+12%", trend: "up" },
  { id: "m2", label: "Average talk balance", value: "54 / 46", delta: "-2%", trend: "neutral" },
  { id: "m3", label: "Pause density", value: "0.82 / min", delta: "+8%", trend: "up" },
  { id: "m4", label: "Overlap rate", value: "6.1%", delta: "-4%", trend: "down" },
];

export const dashboardTrendSeries = [
  { date: "Apr 10", calls: 6, overlap: 4.8, hesitation: 42 },
  { date: "Apr 11", calls: 8, overlap: 5.4, hesitation: 45 },
  { date: "Apr 12", calls: 5, overlap: 5.1, hesitation: 43 },
  { date: "Apr 13", calls: 7, overlap: 6.2, hesitation: 49 },
  { date: "Apr 14", calls: 9, overlap: 6.4, hesitation: 51 },
  { date: "Apr 15", calls: 4, overlap: 5.8, hesitation: 48 },
  { date: "Apr 16", calls: 3, overlap: 6.1, hesitation: 50 },
];

export const recentAnomalies = [
  {
    id: "a1",
    title: "Pricing hesitation spike",
    detail: "call-001 shows a 2.3x slower response after the pricing question.",
  },
  {
    id: "a2",
    title: "Emotion confidence drop",
    detail: "call-003 affect tracks are present but confidence drops during code-switch spans.",
  },
  {
    id: "a3",
    title: "Review needed",
    detail: "call-005 contains frustration markers flagged as experimental and needs manual review.",
  },
];

export function buildAnalysisScope(callIds: string[]): AnalysisScope {
  if (callIds.length === 1) {
    const call = calls.find((item) => item.id === callIds[0]);

    return {
      kind: "single",
      callIds: [callIds[0]],
      label: call ? call.title : "Single call analysis",
    };
  }

  const group = callGroups.find(
    (item) =>
      item.callIds.length === callIds.length &&
      item.callIds.every((id) => callIds.includes(id))
  );

  return {
    kind: "group",
    callIds,
    label: group ? group.name : `${callIds.length} selected calls`,
  };
}

function buildHeadlineMetrics(scope: AnalysisScope): MetricCard[] {
  if (scope.kind === "single") {
    return [
      { id: "hm1", label: "Talk balance", value: "58 / 42", delta: "+6%", trend: "up" },
      { id: "hm2", label: "Hesitation index", value: "0.71", experimental: true, confidence: "medium" },
      { id: "hm3", label: "Overlap rate", value: "7.3%", delta: "+2%", trend: "up" },
      { id: "hm4", label: "Emotion variance", value: "0.46", experimental: true, confidence: "low" },
    ];
  }

  return [
    { id: "ghm1", label: "Grouped calls", value: String(scope.callIds.length) },
    { id: "ghm2", label: "Avg hesitation", value: "0.62", experimental: true, confidence: "medium" },
    { id: "ghm3", label: "Avg overlap", value: "5.8%", delta: "-1%", trend: "down" },
    { id: "ghm4", label: "Emotion variance", value: "0.41", experimental: true, confidence: "low" },
  ];
}

function buildBehaviorSignals(): BehaviorSignalTrack[] {
  return [
    { id: "b1", label: "Turn stability", state: "computed", score: 0.74, confidence: "high" },
    { id: "b2", label: "Interruption pressure", state: "computed", score: 0.42, confidence: "medium" },
    { id: "b3", label: "Pause density", state: "computed", score: 0.63, confidence: "high" },
  ];
}

function buildEmotionSignals(): EmotionSignalTrack[] {
  return [
    { id: "e1", label: "Calmness", state: "computed", score: 0.58, confidence: "low", experimental: true },
    { id: "e2", label: "Frustration risk", state: "computed", score: 0.34, confidence: "medium", experimental: true },
    { id: "e3", label: "Engagement", state: "not-computed", score: null, confidence: "low", experimental: true },
  ];
}

function buildEvidenceRefs(): EvidenceRef[] {
  return [
    { id: "ev-001", label: "turn_020", timestampMs: 312000, type: "turn" },
    { id: "ev-002", label: "evt_overlap_011", timestampMs: 468000, type: "event" },
    { id: "ev-003", label: "metric_hesitation_index", timestampMs: 731000, type: "metric" },
  ];
}

function buildQuestionInsights(evidenceRefs: EvidenceRef[]): QuestionInsight[] {
  return [
    {
      id: "q1",
      questionText: "What would stop you from adopting this in the next 30 days?",
      answerSpeaker: "Speaker B",
      responseLatencyMs: 2400,
      answerLengthSeconds: 22,
      hesitationIndex: 0.74,
      behaviorSummary: "Long response gap followed by two repair starts.",
      emotionSummary: "Confidence is low; mild frustration risk appears after the follow-up.",
      evidenceRefs,
    },
    {
      id: "q2",
      questionText: "How does the pricing compare to your current workflow cost?",
      answerSpeaker: "Speaker B",
      responseLatencyMs: 3100,
      answerLengthSeconds: 18,
      hesitationIndex: 0.82,
      behaviorSummary: "Longest pause in the session before answer onset.",
      emotionSummary: "Emotion markers are experimental and confidence is medium.",
      evidenceRefs,
    },
  ];
}

function buildWaveformTracks(evidenceRefs: EvidenceRef[]): WaveformTrack[] {
  return [
    {
      id: "t-speakers",
      label: "Speaker lanes",
      type: "speaker",
      items: [
        { id: "s1", label: "Speaker A", startMs: 0, endMs: 210000, tone: "default" },
        { id: "s2", label: "Speaker B", startMs: 215000, endMs: 432000, tone: "secondary" },
        { id: "s3", label: "Speaker A", startMs: 438000, endMs: 810000, tone: "default" },
      ],
    },
    {
      id: "t-pauses",
      label: "Pause windows",
      type: "pause",
      items: [
        { id: "p1", label: "Long pause", startMs: 301000, endMs: 306500, tone: "muted" },
        { id: "p2", label: "Response gap", startMs: 728000, endMs: 733500, tone: "muted" },
      ],
    },
    {
      id: "t-overlap",
      label: "Overlap windows",
      type: "overlap",
      items: [{ id: "o1", label: "Overlap", startMs: 462000, endMs: 468500, tone: "destructive" }],
    },
    {
      id: "t-questions",
      label: "Question markers",
      type: "question",
      items: [
        { id: "q1", label: "Pricing question", startMs: 724000, endMs: 730000, tone: "secondary" },
        { id: "q2", label: "Adoption blocker", startMs: 300000, endMs: 304000, tone: "secondary" },
      ],
    },
    {
      id: "t-behavior",
      label: "Behavioral signals",
      type: "behavior",
      items: [
        { id: "b1", label: "Hesitation", startMs: 300000, endMs: 320000, tone: "default" },
        { id: "b2", label: "Repair", startMs: 735000, endMs: 748000, tone: "default" },
      ],
    },
    {
      id: "t-emotion",
      label: "Emotional signals",
      type: "emotion",
      items: [
        { id: "e1", label: "Frustration risk", startMs: 736000, endMs: 755000, tone: "destructive", experimental: true },
        { id: "e2", label: "Calmness", startMs: 470000, endMs: 500000, tone: "secondary", experimental: true },
      ],
    },
    {
      id: "t-evidence",
      label: "Evidence refs",
      type: "evidence",
      items: evidenceRefs.map((item) => ({
        id: item.id,
        label: item.label,
        startMs: item.timestampMs,
        endMs: item.timestampMs + 2500,
        tone: "default",
      })),
    },
  ];
}

function buildWarnings(): ProcessingWarning[] {
  return [
    { id: "w1", level: "warning", message: "Emotion tracks are experimental and confidence drops during mixed-language spans." },
    { id: "w2", level: "info", message: "Model runs are placeholders until backend integration is wired." },
  ];
}

function buildModelRuns(): ModelRunPlaceholder[] {
  return [
    { id: "mr1", name: "ASR pipeline", version: "placeholder-v1", status: "placeholder" },
    { id: "mr2", name: "Behavior signals", version: "placeholder-v1", status: "placeholder" },
    { id: "mr3", name: "Affect plugin", version: "placeholder-v0", status: "placeholder" },
  ];
}

export function buildAnalysisDataset(scope: AnalysisScope): AnalysisDataset {
  const selectedCalls = calls.filter((call) => scope.callIds.includes(call.id));
  const evidenceRefs = buildEvidenceRefs();

  return {
    scope,
    calls: selectedCalls,
    headlineMetrics: buildHeadlineMetrics(scope),
    behaviorSignals: buildBehaviorSignals(),
    emotionSignals: buildEmotionSignals(),
    waveformTracks: buildWaveformTracks(evidenceRefs),
    questionInsights: buildQuestionInsights(evidenceRefs),
    evidenceRefs,
    processingWarnings: buildWarnings(),
    modelRuns: buildModelRuns(),
    rawJson: {
      scope,
      callIds: selectedCalls.map((call) => call.id),
      evidenceRefs,
      placeholder: true,
    },
  };
}
