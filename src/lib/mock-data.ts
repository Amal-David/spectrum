import type {
  AnalysisDataset,
  AnalysisScope,
  BehaviorSignalTrack,
  CallGroup,
  CallRecord,
  DashboardDataset,
  EmotionSignalTrack,
  EvidenceRef,
  MetricCard,
  ModelRunPlaceholder,
  ProcessingWarning,
  QuestionInsight,
  WaveformTrack,
} from "@/lib/types"

export const demoAudioUrl = "/demo-call.wav"

export const calls: CallRecord[] = [
  {
    id: "call-001",
    title: "Mumbai pricing objections - fintech sales",
    source: "demo",
    status: "ready",
    sessionType: "sales",
    language: "Hindi + English",
    declaredLanguage: "Hindi + English",
    state: "Maharashtra",
    stateCode: "MH",
    district: "Mumbai City",
    region: "West",
    speakerCount: 2,
    durationSeconds: 1820,
    uploadedAt: "2026-04-14T09:15:00.000Z",
    reviewState: "needs-review",
    summary:
      "Pricing hesitation spikes after ROI questions, with one noisy answer start near the close.",
    audioUrl: demoAudioUrl,
    audioAsset: {
      originalUrl: demoAudioUrl,
      normalizedUrl: demoAudioUrl,
      telephonyUrl: demoAudioUrl,
    },
    qualityTier: "watch",
    trustTier: "discounted",
    businessOutcome: "converted",
    workflowId: "wf-sales-pricing",
    workflowLabel: "Pricing Discovery",
    agentLabel: "Fintech SDR Agent",
    promptVersion: "v1.8",
    qualityScore: 71,
    trustScore: 64,
    frictionScore: 68,
    avgSnrDb: 11.4,
    explainabilityFlags: ["Noisy answer onset", "Prosody discounted"],
    environmentTags: ["traffic", "street"],
    topQuestionIssue: "ROI question caused a 9.1s hesitation window",
  },
  {
    id: "call-002",
    title: "Bengaluru onboarding confusion - support",
    source: "upload",
    status: "ready",
    sessionType: "support",
    language: "Kannada + English",
    declaredLanguage: "Kannada + English",
    state: "Karnataka",
    stateCode: "KA",
    district: "Bengaluru Urban",
    region: "South",
    speakerCount: 2,
    durationSeconds: 1260,
    uploadedAt: "2026-04-14T13:45:00.000Z",
    reviewState: "unreviewed",
    summary:
      "Elevated overlap early in the call, then steady recovery after credential reset guidance.",
    audioUrl: demoAudioUrl,
    audioAsset: {
      originalUrl: demoAudioUrl,
      normalizedUrl: demoAudioUrl,
      telephonyUrl: demoAudioUrl,
    },
    qualityTier: "healthy",
    trustTier: "trusted",
    businessOutcome: "resolved",
    workflowId: "wf-support-onboarding",
    workflowLabel: "Onboarding Support",
    agentLabel: "Support Copilot Agent",
    promptVersion: "v2.0",
    qualityScore: 86,
    trustScore: 83,
    frictionScore: 39,
    avgSnrDb: 19.6,
    explainabilityFlags: [],
    environmentTags: ["typing"],
    topQuestionIssue: "Credential question created a short interruption cluster",
  },
  {
    id: "call-003",
    title: "Chennai multilingual retention check-in",
    source: "api",
    status: "ready",
    sessionType: "research",
    language: "Tamil + English",
    declaredLanguage: "Tamil + English",
    state: "Tamil Nadu",
    stateCode: "TN",
    district: "Chennai",
    region: "South",
    speakerCount: 3,
    durationSeconds: 2140,
    uploadedAt: "2026-04-15T11:10:00.000Z",
    reviewState: "reviewed",
    summary:
      "Code-switching reduces affect confidence, but turn structure and question-answer mapping remain strong.",
    audioUrl: demoAudioUrl,
    audioAsset: {
      originalUrl: demoAudioUrl,
      normalizedUrl: demoAudioUrl,
      telephonyUrl: demoAudioUrl,
    },
    qualityTier: "healthy",
    trustTier: "review",
    businessOutcome: "resolved",
    workflowId: "wf-research-retention",
    workflowLabel: "Retention Research",
    agentLabel: "Insight Agent",
    promptVersion: "v1.4",
    qualityScore: 79,
    trustScore: 58,
    frictionScore: 44,
    avgSnrDb: 17.2,
    explainabilityFlags: ["Mixed-language affect confidence"],
    environmentTags: ["fan"],
    topQuestionIssue: "Closing decision question had long silence before answer",
  },
  {
    id: "call-004",
    title: "Delhi policy escalation - collections",
    source: "upload",
    status: "ready",
    sessionType: "collections",
    language: "Hindi",
    declaredLanguage: "Hindi",
    state: "Delhi",
    stateCode: "DL",
    district: "New Delhi",
    region: "North",
    speakerCount: 2,
    durationSeconds: 980,
    uploadedAt: "2026-04-15T16:00:00.000Z",
    reviewState: "needs-review",
    summary:
      "Repeated interruptions and friction around policy exceptions caused a live transfer.",
    audioUrl: demoAudioUrl,
    audioAsset: {
      originalUrl: demoAudioUrl,
      normalizedUrl: demoAudioUrl,
      telephonyUrl: demoAudioUrl,
    },
    qualityTier: "watch",
    trustTier: "review",
    businessOutcome: "escalated",
    workflowId: "wf-collections-policy",
    workflowLabel: "Collections Recovery",
    agentLabel: "Collections Agent",
    promptVersion: "v3.1",
    qualityScore: 68,
    trustScore: 55,
    frictionScore: 82,
    avgSnrDb: 10.3,
    explainabilityFlags: ["High overlap", "Background music contamination"],
    environmentTags: ["music", "crowd"],
    topQuestionIssue: "Policy exception question caused interruption cluster",
  },
  {
    id: "call-005",
    title: "Kolkata repayment assurance - collections",
    source: "demo",
    status: "ready",
    sessionType: "collections",
    language: "Bengali + English",
    declaredLanguage: "Bengali + English",
    state: "West Bengal",
    stateCode: "WB",
    district: "Kolkata",
    region: "East",
    speakerCount: 2,
    durationSeconds: 1540,
    uploadedAt: "2026-04-16T08:25:00.000Z",
    reviewState: "needs-review",
    summary:
      "Balanced talk time but elevated uncertainty markers and high repeat-contact risk after payment-date questions.",
    audioUrl: demoAudioUrl,
    audioAsset: {
      originalUrl: demoAudioUrl,
      normalizedUrl: demoAudioUrl,
      telephonyUrl: demoAudioUrl,
    },
    qualityTier: "healthy",
    trustTier: "trusted",
    businessOutcome: "resolved",
    workflowId: "wf-collections-policy",
    workflowLabel: "Collections Recovery",
    agentLabel: "Collections Agent",
    promptVersion: "v3.1",
    qualityScore: 82,
    trustScore: 81,
    frictionScore: 57,
    avgSnrDb: 18.7,
    explainabilityFlags: [],
    environmentTags: ["office"],
    topQuestionIssue: "Promise-to-pay question showed low directness",
  },
  {
    id: "call-006",
    title: "Ahmedabad renewal intent - insurance sales",
    source: "api",
    status: "ready",
    sessionType: "sales",
    language: "Gujarati + English",
    declaredLanguage: "Gujarati + English",
    state: "Gujarat",
    stateCode: "GJ",
    district: "Ahmedabad",
    region: "West",
    speakerCount: 2,
    durationSeconds: 1325,
    uploadedAt: "2026-04-16T10:35:00.000Z",
    reviewState: "reviewed",
    summary:
      "High-quality audio and clear rapport, but one VAD false positive inflated the first response delay.",
    audioUrl: demoAudioUrl,
    audioAsset: {
      originalUrl: demoAudioUrl,
      normalizedUrl: demoAudioUrl,
      telephonyUrl: demoAudioUrl,
    },
    qualityTier: "healthy",
    trustTier: "trusted",
    businessOutcome: "converted",
    workflowId: "wf-insurance-renewal",
    workflowLabel: "Renewal Outreach",
    agentLabel: "Insurance Renewal Agent",
    promptVersion: "v2.6",
    qualityScore: 91,
    trustScore: 88,
    frictionScore: 28,
    avgSnrDb: 22.4,
    explainabilityFlags: ["Early VAD false positive"],
    environmentTags: ["vehicle"],
    topQuestionIssue: "Coverage comparison question had delayed clean-speech onset",
  },
]

export const callGroups: CallGroup[] = [
  {
    id: "group-001",
    name: "Pricing friction cluster",
    callIds: ["call-001", "call-006"],
    createdAt: "2026-04-16T07:30:00.000Z",
    purpose: "Compare hesitation, conversion, and trust around pricing or renewal questions.",
  },
  {
    id: "group-002",
    name: "Collections high-friction",
    callIds: ["call-004", "call-005"],
    createdAt: "2026-04-15T18:10:00.000Z",
    purpose: "Inspect escalation, uncertainty, and policy friction in collections flows.",
  },
]

export const dashboardDataset: DashboardDataset = {
  businessMetrics: [
    {
      id: "bm-1",
      label: "Total conversations",
      value: "18,420",
      delta: "+12.4%",
      trend: "up",
      description: "All agent-handled sessions this month.",
    },
    {
      id: "bm-2",
      label: "Successful completions",
      value: "74.8%",
      delta: "+3.2%",
      trend: "up",
      description: "Task completion across all active workflows.",
    },
    {
      id: "bm-3",
      label: "Escalation rate",
      value: "11.6%",
      delta: "-1.8%",
      trend: "down",
      description: "Calls transferred to a human or fallback queue.",
    },
    {
      id: "bm-4",
      label: "Containment rate",
      value: "68.1%",
      delta: "+2.6%",
      trend: "up",
      description: "Sessions fully handled by the agent without live assist.",
    },
    {
      id: "bm-5",
      label: "Avg resolution time",
      value: "05:42",
      delta: "-0:21",
      trend: "down",
      description: "Mean time to resolve or route to the correct outcome.",
    },
    {
      id: "bm-6",
      label: "Trusted insight coverage",
      value: "83.4%",
      delta: "+1.1%",
      trend: "up",
      description: "Share of sessions whose insight layer was not discounted.",
    },
  ],
  businessTrend: [
    { date: "Apr 10", conversations: 2260, completions: 71, escalations: 13, containmentRate: 64 },
    { date: "Apr 11", conversations: 2410, completions: 72, escalations: 12, containmentRate: 65 },
    { date: "Apr 12", conversations: 2490, completions: 73, escalations: 12, containmentRate: 66 },
    { date: "Apr 13", conversations: 2610, completions: 74, escalations: 12, containmentRate: 66 },
    { date: "Apr 14", conversations: 2760, completions: 75, escalations: 11, containmentRate: 68 },
    { date: "Apr 15", conversations: 2880, completions: 75, escalations: 11, containmentRate: 68 },
    { date: "Apr 16", conversations: 3010, completions: 76, escalations: 10, containmentRate: 69 },
  ],
  outcomeMix: [
    { label: "North", resolved: 46, escalated: 18, abandoned: 11, converted: 25 },
    { label: "South", resolved: 51, escalated: 10, abandoned: 9, converted: 30 },
    { label: "West", resolved: 49, escalated: 12, abandoned: 8, converted: 31 },
    { label: "East", resolved: 44, escalated: 14, abandoned: 12, converted: 30 },
  ],
  statePerformance: [
    { state: "Delhi", stateCode: "DL", x: 6.2, y: 8.5, callVolume: 2620, completionRate: 71, escalationRate: 16, avgSnrDb: 11.2, trustScore: 58 },
    { state: "West Bengal", stateCode: "WB", x: 8.3, y: 7.2, callVolume: 1980, completionRate: 73, escalationRate: 13, avgSnrDb: 16.8, trustScore: 76 },
    { state: "Gujarat", stateCode: "GJ", x: 4.6, y: 6.3, callVolume: 2140, completionRate: 79, escalationRate: 9, avgSnrDb: 21.4, trustScore: 87 },
    { state: "Maharashtra", stateCode: "MH", x: 4.9, y: 4.4, callVolume: 3180, completionRate: 76, escalationRate: 11, avgSnrDb: 14.6, trustScore: 69 },
    { state: "Karnataka", stateCode: "KA", x: 4.8, y: 2.8, callVolume: 2860, completionRate: 81, escalationRate: 8, avgSnrDb: 19.4, trustScore: 84 },
    { state: "Tamil Nadu", stateCode: "TN", x: 5.7, y: 1.6, callVolume: 2640, completionRate: 78, escalationRate: 9, avgSnrDb: 17.1, trustScore: 72 },
  ],
  geographySummaries: [
    { state: "Karnataka", stateCode: "KA", region: "South", callVolume: 2860, completionRate: 81, escalationRate: 8, avgSnrDb: 19.4, hesitationScore: 0.41, frictionScore: 0.33, frustrationRisk: 0.28, trustTier: "trusted" },
    { state: "Gujarat", stateCode: "GJ", region: "West", callVolume: 2140, completionRate: 79, escalationRate: 9, avgSnrDb: 21.4, hesitationScore: 0.36, frictionScore: 0.26, frustrationRisk: 0.24, trustTier: "trusted" },
    { state: "Tamil Nadu", stateCode: "TN", region: "South", callVolume: 2640, completionRate: 78, escalationRate: 9, avgSnrDb: 17.1, hesitationScore: 0.46, frictionScore: 0.41, frustrationRisk: 0.37, trustTier: "review" },
    { state: "Maharashtra", stateCode: "MH", region: "West", callVolume: 3180, completionRate: 76, escalationRate: 11, avgSnrDb: 14.6, hesitationScore: 0.54, frictionScore: 0.52, frustrationRisk: 0.44, trustTier: "discounted" },
    { state: "West Bengal", stateCode: "WB", region: "East", callVolume: 1980, completionRate: 73, escalationRate: 13, avgSnrDb: 16.8, hesitationScore: 0.58, frictionScore: 0.49, frustrationRisk: 0.46, trustTier: "trusted" },
    { state: "Delhi", stateCode: "DL", region: "North", callVolume: 2620, completionRate: 71, escalationRate: 16, avgSnrDb: 11.2, hesitationScore: 0.67, frictionScore: 0.71, frustrationRisk: 0.62, trustTier: "review" },
  ],
  languageDistribution: [
    { language: "Hindi + English", callVolume: 4420, completionRate: 75 },
    { language: "Tamil + English", callVolume: 2640, completionRate: 78 },
    { language: "Kannada + English", callVolume: 2860, completionRate: 81 },
    { language: "Bengali + English", callVolume: 1980, completionRate: 73 },
    { language: "Gujarati + English", callVolume: 2140, completionRate: 79 },
    { language: "Hindi", callVolume: 2620, completionRate: 71 },
  ],
  demographicSlices: [
    { id: "d-1", state: "Delhi", region: "North", language: "Hindi", callVolume: 2620, completionRate: 71, escalationRate: 16, qualityScore: 58, trustScore: 55, frictionScore: 71, hesitationScore: 0.67, rapportScore: 0.38, frustrationRisk: 0.62, avgSnrDb: 11.2 },
    { id: "d-2", state: "Maharashtra", region: "West", language: "Hindi + English", callVolume: 3180, completionRate: 76, escalationRate: 11, qualityScore: 69, trustScore: 64, frictionScore: 52, hesitationScore: 0.54, rapportScore: 0.58, frustrationRisk: 0.44, avgSnrDb: 14.6 },
    { id: "d-3", state: "Karnataka", region: "South", language: "Kannada + English", callVolume: 2860, completionRate: 81, escalationRate: 8, qualityScore: 84, trustScore: 83, frictionScore: 33, hesitationScore: 0.41, rapportScore: 0.72, frustrationRisk: 0.28, avgSnrDb: 19.4 },
    { id: "d-4", state: "Tamil Nadu", region: "South", language: "Tamil + English", callVolume: 2640, completionRate: 78, escalationRate: 9, qualityScore: 72, trustScore: 62, frictionScore: 41, hesitationScore: 0.46, rapportScore: 0.65, frustrationRisk: 0.37, avgSnrDb: 17.1 },
    { id: "d-5", state: "West Bengal", region: "East", language: "Bengali + English", callVolume: 1980, completionRate: 73, escalationRate: 13, qualityScore: 78, trustScore: 76, frictionScore: 49, hesitationScore: 0.58, rapportScore: 0.54, frustrationRisk: 0.46, avgSnrDb: 16.8 },
    { id: "d-6", state: "Gujarat", region: "West", language: "Gujarati + English", callVolume: 2140, completionRate: 79, escalationRate: 9, qualityScore: 88, trustScore: 87, frictionScore: 26, hesitationScore: 0.36, rapportScore: 0.76, frustrationRisk: 0.24, avgSnrDb: 21.4 },
  ],
  emotionAggregates: [
    { id: "ea-1", demographicKey: "Delhi", demographicLabel: "Delhi", emotion: "Frustration", score: 0.62, confidence: "medium", sampleSize: 2620, trustTier: "review" },
    { id: "ea-2", demographicKey: "Delhi", demographicLabel: "Delhi", emotion: "Calmness", score: 0.28, confidence: "low", sampleSize: 2620, trustTier: "review" },
    { id: "ea-3", demographicKey: "Maharashtra", demographicLabel: "Maharashtra", emotion: "Frustration", score: 0.44, confidence: "medium", sampleSize: 3180, trustTier: "discounted" },
    { id: "ea-4", demographicKey: "Maharashtra", demographicLabel: "Maharashtra", emotion: "Determination", score: 0.53, confidence: "medium", sampleSize: 3180, trustTier: "discounted" },
    { id: "ea-5", demographicKey: "Karnataka", demographicLabel: "Karnataka", emotion: "Calmness", score: 0.71, confidence: "high", sampleSize: 2860, trustTier: "trusted" },
    { id: "ea-6", demographicKey: "Karnataka", demographicLabel: "Karnataka", emotion: "Interest", score: 0.58, confidence: "high", sampleSize: 2860, trustTier: "trusted" },
    { id: "ea-7", demographicKey: "Tamil Nadu", demographicLabel: "Tamil Nadu", emotion: "Interest", score: 0.52, confidence: "medium", sampleSize: 2640, trustTier: "review" },
    { id: "ea-8", demographicKey: "Tamil Nadu", demographicLabel: "Tamil Nadu", emotion: "Anxiety", score: 0.33, confidence: "low", sampleSize: 2640, trustTier: "review" },
    { id: "ea-9", demographicKey: "West Bengal", demographicLabel: "West Bengal", emotion: "Uncertainty", score: 0.48, confidence: "medium", sampleSize: 1980, trustTier: "trusted" },
    { id: "ea-10", demographicKey: "West Bengal", demographicLabel: "West Bengal", emotion: "Frustration", score: 0.46, confidence: "medium", sampleSize: 1980, trustTier: "trusted" },
    { id: "ea-11", demographicKey: "Gujarat", demographicLabel: "Gujarat", emotion: "Calmness", score: 0.76, confidence: "high", sampleSize: 2140, trustTier: "trusted" },
    { id: "ea-12", demographicKey: "Gujarat", demographicLabel: "Gujarat", emotion: "Determination", score: 0.66, confidence: "high", sampleSize: 2140, trustTier: "trusted" },
  ],
  behaviorAggregates: [
    { id: "ba-1", demographicKey: "Delhi", demographicLabel: "Delhi", fillerDensity: 0.38, interruptionRate: 0.24, overlapRate: 0.17, responseLatencyMs: 3900, reciprocity: 0.44, engagementDrift: -0.18, directness: 0.46, hesitationScore: 0.67 },
    { id: "ba-2", demographicKey: "Maharashtra", demographicLabel: "Maharashtra", fillerDensity: 0.31, interruptionRate: 0.19, overlapRate: 0.14, responseLatencyMs: 3200, reciprocity: 0.53, engagementDrift: -0.11, directness: 0.58, hesitationScore: 0.54 },
    { id: "ba-3", demographicKey: "Karnataka", demographicLabel: "Karnataka", fillerDensity: 0.18, interruptionRate: 0.09, overlapRate: 0.07, responseLatencyMs: 2100, reciprocity: 0.71, engagementDrift: 0.06, directness: 0.75, hesitationScore: 0.41 },
    { id: "ba-4", demographicKey: "Tamil Nadu", demographicLabel: "Tamil Nadu", fillerDensity: 0.22, interruptionRate: 0.11, overlapRate: 0.09, responseLatencyMs: 2400, reciprocity: 0.63, engagementDrift: -0.03, directness: 0.68, hesitationScore: 0.46 },
    { id: "ba-5", demographicKey: "West Bengal", demographicLabel: "West Bengal", fillerDensity: 0.29, interruptionRate: 0.13, overlapRate: 0.1, responseLatencyMs: 2800, reciprocity: 0.57, engagementDrift: -0.07, directness: 0.59, hesitationScore: 0.58 },
    { id: "ba-6", demographicKey: "Gujarat", demographicLabel: "Gujarat", fillerDensity: 0.16, interruptionRate: 0.07, overlapRate: 0.06, responseLatencyMs: 1900, reciprocity: 0.77, engagementDrift: 0.11, directness: 0.81, hesitationScore: 0.36 },
  ],
  qualityTrend: [
    { date: "Apr 10", avgSnrDb: 16.2, noisySegmentRate: 14, vadFpCount: 92, vadFnCount: 71, insightDiscountRate: 21 },
    { date: "Apr 11", avgSnrDb: 16.8, noisySegmentRate: 13, vadFpCount: 85, vadFnCount: 66, insightDiscountRate: 20 },
    { date: "Apr 12", avgSnrDb: 16.6, noisySegmentRate: 13, vadFpCount: 83, vadFnCount: 64, insightDiscountRate: 19 },
    { date: "Apr 13", avgSnrDb: 17.2, noisySegmentRate: 12, vadFpCount: 78, vadFnCount: 59, insightDiscountRate: 18 },
    { date: "Apr 14", avgSnrDb: 17.9, noisySegmentRate: 11, vadFpCount: 74, vadFnCount: 54, insightDiscountRate: 17 },
    { date: "Apr 15", avgSnrDb: 18.1, noisySegmentRate: 10, vadFpCount: 68, vadFnCount: 49, insightDiscountRate: 17 },
    { date: "Apr 16", avgSnrDb: 18.4, noisySegmentRate: 10, vadFpCount: 64, vadFnCount: 46, insightDiscountRate: 16 },
  ],
  environmentTags: [
    { tag: "traffic", count: 1320 },
    { tag: "music", count: 980 },
    { tag: "fan", count: 870 },
    { tag: "typing", count: 620 },
    { tag: "crowd", count: 540 },
    { tag: "vehicle", count: 430 },
  ],
  agentPerformance: [
    { id: "ap-1", workflowLabel: "Pricing Discovery", agentLabel: "Fintech SDR Agent", promptVersion: "v1.8", campaign: "Acquisition Q2", volume: 4220, successRate: 0.77, escalationRate: 0.09, qualityScore: 74, trustScore: 68, frictionScore: 0.49 },
    { id: "ap-2", workflowLabel: "Onboarding Support", agentLabel: "Support Copilot Agent", promptVersion: "v2.0", campaign: "Self-Serve Support", volume: 5080, successRate: 0.84, escalationRate: 0.07, qualityScore: 86, trustScore: 83, frictionScore: 0.31 },
    { id: "ap-3", workflowLabel: "Collections Recovery", agentLabel: "Collections Agent", promptVersion: "v3.1", campaign: "Late Payments", volume: 3740, successRate: 0.68, escalationRate: 0.15, qualityScore: 72, trustScore: 64, frictionScore: 0.63 },
    { id: "ap-4", workflowLabel: "Retention Research", agentLabel: "Insight Agent", promptVersion: "v1.4", campaign: "Voice Research", volume: 2050, successRate: 0.79, escalationRate: 0.05, qualityScore: 78, trustScore: 61, frictionScore: 0.38 },
    { id: "ap-5", workflowLabel: "Renewal Outreach", agentLabel: "Insurance Renewal Agent", promptVersion: "v2.6", campaign: "Renewals", volume: 3330, successRate: 0.82, escalationRate: 0.06, qualityScore: 88, trustScore: 85, frictionScore: 0.27 },
  ],
  reviewQueue: [
    {
      id: "rq-1",
      title: "Delhi collections cluster needs review",
      detail: "High-volume cohort with low SNR, elevated escalation, and discounted frustration signals.",
      severity: "critical",
      href: "/analysis?callId=call-004",
    },
    {
      id: "rq-2",
      title: "Mumbai pricing objections trending up",
      detail: "Hesitation and low directness increased in the pricing workflow this week.",
      severity: "watch",
      href: "/analysis?groupId=group-001",
    },
    {
      id: "rq-3",
      title: "Tamil affect confidence dropped in multilingual flows",
      detail: "Affect reads are still present, but confidence bands widened after code-switching segments.",
      severity: "info",
      href: "/analysis?callId=call-003",
    },
  ],
}

export function buildAnalysisScope(callIds: string[]): AnalysisScope {
  if (callIds.length === 1) {
    const call = calls.find((item) => item.id === callIds[0])

    return {
      kind: "single",
      callIds: [callIds[0]],
      label: call ? call.title : "Single call analysis",
    }
  }

  const group = callGroups.find(
    (item) =>
      item.callIds.length === callIds.length &&
      item.callIds.every((id) => callIds.includes(id))
  )

  return {
    kind: "group",
    callIds,
    label: group ? group.name : `${callIds.length} selected calls`,
  }
}

function average(values: number[]) {
  return values.reduce((total, value) => total + value, 0) / values.length
}

function buildHeadlineMetrics(selectedCalls: CallRecord[]): MetricCard[] {
  return [
    {
      id: "ah-1",
      label: "Calls in scope",
      value: String(selectedCalls.length),
      delta: selectedCalls.length > 1 ? "grouped" : "single",
      trend: "neutral",
    },
    {
      id: "ah-2",
      label: "Avg SNR",
      value: `${average(selectedCalls.map((call) => call.avgSnrDb)).toFixed(1)} dB`,
      delta: "quality",
      trend: "neutral",
    },
    {
      id: "ah-3",
      label: "Friction score",
      value: `${average(selectedCalls.map((call) => call.frictionScore)).toFixed(0)}`,
      delta: "behavior",
      trend: "neutral",
    },
    {
      id: "ah-4",
      label: "Trust score",
      value: `${average(selectedCalls.map((call) => call.trustScore)).toFixed(0)}`,
      delta: "explainability",
      trend: "neutral",
    },
  ]
}

function buildQualityMetrics(selectedCalls: CallRecord[]): MetricCard[] {
  return [
    {
      id: "qm-1",
      label: "Quality tier",
      value:
        selectedCalls.length === 1
          ? selectedCalls[0].qualityTier
          : `${selectedCalls.filter((call) => call.qualityTier === "healthy").length} healthy`,
    },
    {
      id: "qm-2",
      label: "Trust tier",
      value:
        selectedCalls.length === 1
          ? selectedCalls[0].trustTier
          : `${selectedCalls.filter((call) => call.trustTier === "trusted").length} trusted`,
    },
    {
      id: "qm-3",
      label: "Environment tags",
      value: Array.from(new Set(selectedCalls.flatMap((call) => call.environmentTags)))
        .slice(0, 2)
        .join(", "),
    },
  ]
}

function buildStructureMetrics(selectedCalls: CallRecord[]): MetricCard[] {
  const baseSpeakerCount = average(selectedCalls.map((call) => call.speakerCount))

  return [
    { id: "sm-1", label: "Avg speakers", value: baseSpeakerCount.toFixed(1) },
    { id: "sm-2", label: "Longest pause", value: "09.1s", delta: "question-linked", trend: "up" },
    { id: "sm-3", label: "Interruption rate", value: "12.4%", delta: "watch", trend: "up" },
  ]
}

function buildBusinessMetrics(selectedCalls: CallRecord[]): MetricCard[] {
  const convertedCount = selectedCalls.filter((call) => call.businessOutcome === "converted").length
  const resolvedCount = selectedCalls.filter((call) => call.businessOutcome === "resolved").length

  return [
    {
      id: "bm-1",
      label: "Business outcome",
      value:
        selectedCalls.length === 1
          ? selectedCalls[0].businessOutcome
          : `${resolvedCount + convertedCount} positive`,
    },
    {
      id: "bm-2",
      label: "Workflow",
      value: Array.from(new Set(selectedCalls.map((call) => call.workflowLabel))).join(", "),
    },
    {
      id: "bm-3",
      label: "Review state",
      value: selectedCalls.some((call) => call.reviewState === "needs-review")
        ? "needs-review"
        : "reviewed",
    },
  ]
}

function buildBehaviorSignals(selectedCalls: CallRecord[]): BehaviorSignalTrack[] {
  const frictionScore = average(selectedCalls.map((call) => call.frictionScore)) / 100

  return [
    { id: "b1", label: "Friction", state: "computed", score: frictionScore, confidence: "high" },
    { id: "b2", label: "Reciprocity", state: "computed", score: 0.63, confidence: "medium" },
    { id: "b3", label: "Engagement drift", state: "computed", score: 0.44, confidence: "medium" },
    { id: "b4", label: "Filler density", state: "computed", score: 0.28, confidence: "high" },
  ]
}

function buildEmotionSignals(selectedCalls: CallRecord[]): EmotionSignalTrack[] {
  const lowConfidence = selectedCalls.some((call) =>
    call.explainabilityFlags.some((flag) => flag.toLowerCase().includes("confidence"))
  )

  return [
    { id: "e1", label: "Calmness", state: "computed", score: 0.58, confidence: lowConfidence ? "low" : "medium", experimental: true },
    { id: "e2", label: "Frustration risk", state: "computed", score: 0.42, confidence: "medium", experimental: true },
    { id: "e3", label: "Determination", state: "computed", score: 0.51, confidence: "medium", experimental: true },
  ]
}

function buildEvidenceRefs(): EvidenceRef[] {
  return [
    { id: "ev-001", label: "turn_020", timestampMs: 312000, type: "turn" },
    { id: "ev-002", label: "evt_overlap_cluster", timestampMs: 468000, type: "event" },
    { id: "ev-003", label: "metric_hesitation_spike", timestampMs: 731000, type: "metric" },
    { id: "ev-004", label: "evt_vad_fp_start", timestampMs: 742000, type: "event" },
  ]
}

function buildQuestionInsights(evidenceRefs: EvidenceRef[], selectedCalls: CallRecord[]): QuestionInsight[] {
  const call = selectedCalls[0]

  return [
    {
      id: "q1",
      questionText: "How does the pricing compare to your current workflow cost?",
      answerSpeaker: "Customer",
      responseLatencyMs: 9100,
      answerLengthSeconds: 18,
      hesitationIndex: 0.82,
      directnessScore: 0.44,
      affectTag: "uncertainty",
      qualityMask: call.explainabilityFlags,
      behaviorSummary: "Longest pause in the session before clean answer onset.",
      emotionSummary: "Frustration risk rose after the follow-up, but prosody is partially discounted.",
      evidenceRefs,
    },
    {
      id: "q2",
      questionText: "What would stop you from completing this task today?",
      answerSpeaker: "Customer",
      responseLatencyMs: 3200,
      answerLengthSeconds: 24,
      hesitationIndex: 0.58,
      directnessScore: 0.61,
      affectTag: "determination",
      qualityMask: call.explainabilityFlags,
      behaviorSummary: "Answer opened with repair starts and moderate filler density.",
      emotionSummary: "Confidence band stays medium once noise drops below the threshold.",
      evidenceRefs,
    },
  ]
}

function buildWaveformTracks(evidenceRefs: EvidenceRef[]): WaveformTrack[] {
  return [
    {
      id: "t-speakers",
      label: "Speaker turns",
      type: "speaker",
      items: [
        { id: "s1", label: "Agent", startMs: 0, endMs: 214000, tone: "default" },
        { id: "s2", label: "Customer", startMs: 216000, endMs: 452000, tone: "secondary" },
        { id: "s3", label: "Agent", startMs: 456000, endMs: 812000, tone: "default" },
      ],
    },
    {
      id: "t-pauses",
      label: "Pause windows",
      type: "pause",
      items: [
        { id: "p1", label: "Long pause", startMs: 301000, endMs: 306500, tone: "muted" },
        { id: "p2", label: "Response gap", startMs: 728000, endMs: 737100, tone: "muted" },
      ],
    },
    {
      id: "t-overlap",
      label: "Interruptions / overlaps",
      type: "overlap",
      items: [
        { id: "o1", label: "Interruption cluster", startMs: 462000, endMs: 468500, tone: "destructive" },
      ],
    },
    {
      id: "t-quality",
      label: "Low-SNR / VAD events",
      type: "quality",
      items: [
        { id: "qf1", label: "Low SNR", startMs: 724000, endMs: 731000, tone: "muted" },
        { id: "qf2", label: "VAD false positive", startMs: 739000, endMs: 742000, tone: "destructive" },
      ],
    },
    {
      id: "t-questions",
      label: "Question markers",
      type: "question",
      items: [
        { id: "q1", label: "Pricing compare", startMs: 724000, endMs: 730000, tone: "secondary" },
        { id: "q2", label: "Adoption blocker", startMs: 300000, endMs: 304000, tone: "secondary" },
      ],
    },
    {
      id: "t-behavior",
      label: "Behavior markers",
      type: "behavior",
      items: [
        { id: "b1", label: "Hesitation", startMs: 300000, endMs: 320000, tone: "default" },
        { id: "b2", label: "Low directness", startMs: 735000, endMs: 748000, tone: "default" },
      ],
    },
    {
      id: "t-emotion",
      label: "Emotion markers",
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
  ]
}

function buildWarnings(selectedCalls: CallRecord[]): ProcessingWarning[] {
  const explainabilityFlags = Array.from(
    new Set(selectedCalls.flatMap((call) => call.explainabilityFlags))
  )

  return [
    {
      id: "w1",
      level: "warning",
      message:
        explainabilityFlags[0] ??
        "Signals are confidence-banded whenever noise or overlap contaminates the onset.",
    },
    {
      id: "w2",
      level: "info",
      message:
        "Emotion tracks are soft signals and should be read alongside trust tier and sample quality.",
    },
  ]
}

function buildModelRuns(): ModelRunPlaceholder[] {
  return [
    { id: "mr1", name: "ASR pipeline", version: "placeholder-v1", status: "placeholder" },
    { id: "mr2", name: "Quality diagnostics", version: "placeholder-v1", status: "placeholder" },
    { id: "mr3", name: "Behavior signals", version: "placeholder-v1", status: "placeholder" },
    { id: "mr4", name: "Affect plugin", version: "placeholder-v0", status: "placeholder" },
  ]
}

export function buildAnalysisDataset(scope: AnalysisScope): AnalysisDataset {
  const selectedCalls = calls.filter((call) => scope.callIds.includes(call.id))
  const evidenceRefs = buildEvidenceRefs()

  return {
    scope,
    calls: selectedCalls,
    headlineMetrics: buildHeadlineMetrics(selectedCalls),
    qualityMetrics: buildQualityMetrics(selectedCalls),
    structureMetrics: buildStructureMetrics(selectedCalls),
    businessMetrics: buildBusinessMetrics(selectedCalls),
    behaviorSignals: buildBehaviorSignals(selectedCalls),
    emotionSignals: buildEmotionSignals(selectedCalls),
    waveformTracks: buildWaveformTracks(evidenceRefs),
    questionInsights: buildQuestionInsights(evidenceRefs, selectedCalls),
    evidenceRefs,
    processingWarnings: buildWarnings(selectedCalls),
    modelRuns: buildModelRuns(),
    rawJson: {
      scope,
      calls: selectedCalls.map((call) => ({
        id: call.id,
        state: call.state,
        language: call.language,
        qualityTier: call.qualityTier,
        trustTier: call.trustTier,
        businessOutcome: call.businessOutcome,
        explainabilityFlags: call.explainabilityFlags,
      })),
      evidenceRefs,
      dashboardDatasetKeys: [
        "businessMetrics",
        "geographySummaries",
        "emotionAggregates",
        "behaviorAggregates",
      ],
      placeholder: true,
    },
  }
}
