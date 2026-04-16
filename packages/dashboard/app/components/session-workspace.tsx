"use client";

import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import type { SessionBundle } from "../../lib/data";

type SessionWorkspaceProps = {
  jobId: string;
  audioSrc: string;
  spectrogramSrc: string;
  bundle: SessionBundle;
};

type ViewMode = "waveform" | "spectrogram" | "digital";
type RoleView = "human" | "all" | "ai";
type MomentsView = "cues" | "questions" | "signals" | "events";
type TrackViewItem = {
  item_id: string;
  label: string;
  shortLabel: string;
  start_ms: number;
  end_ms: number;
  tone: string;
  speaker_id?: string | null;
  confidence?: number | null;
  evidence_refs: SessionBundle["timeline_tracks"][number]["items"][number]["evidence_refs"];
  count: number;
};

type TrackView = SessionBundle["timeline_tracks"][number] & {
  dense: boolean;
  items_for_view: TrackViewItem[];
  top_labels: Array<{ label: string; count: number }>;
};

function formatMs(value: number) {
  return `${Math.round(value)} ms`;
}

function formatClock(valueMs: number) {
  const totalSeconds = Math.max(0, Math.round(valueMs / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

function formatPct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatMetric(value: string | number | boolean | null, unit?: string | null) {
  if (value === null || value === undefined) return "Unknown";
  if (typeof value === "number") {
    const formatted = Number.isInteger(value) ? `${value}` : value.toFixed(2);
    return unit ? `${formatted} ${unit}` : formatted;
  }
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return unit ? `${value} ${unit}` : value;
}

function emotionTone(label: string) {
  switch (label) {
    case "joy":
      return "emotion-joy";
    case "anger":
    case "disgust":
      return "emotion-anger";
    case "sadness":
    case "fear":
      return "emotion-sad";
    case "surprise":
      return "emotion-surprise";
    case "calm":
      return "emotion-calm";
    default:
      return "emotion-neutral";
  }
}

function trackTone(tone: string) {
  switch (tone) {
    case "positive":
      return "track-tone-positive";
    case "warning":
      return "track-tone-warning";
    case "accent":
      return "track-tone-accent";
    default:
      return "track-tone-default";
  }
}

function evidenceLabel(evidenceClass: string | undefined) {
  switch (evidenceClass) {
    case "benchmark_backed":
      return "benchmark-backed";
    case "model_backed":
      return "model-backed";
    case "metadata_backed":
      return "metadata-backed";
    default:
      return "heuristic-backed";
  }
}

function attributionLabel(attributionState: string | undefined) {
  switch (attributionState) {
    case "strong":
      return "speaker-attributed";
    case "muted":
      return "timing only";
    default:
      return "unassigned";
  }
}

function markText(text: string, query: string) {
  if (!query.trim()) return text;
  const parts = text.split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"));
  return parts.map((part, index) =>
    part.toLowerCase() === query.toLowerCase() ? <mark key={`${part}-${index}`}>{part}</mark> : part
  );
}

function waveformPath(peaks: number[], width: number, height: number) {
  if (!peaks.length) {
    return `M0 ${height / 2} L${width} ${height / 2}`;
  }
  const middle = height / 2;
  const upper = peaks.map((peak, index) => {
    const x = peaks.length === 1 ? 0 : (index / (peaks.length - 1)) * width;
    const y = middle - peak * (height / 2 - 4);
    return `${x} ${y}`;
  });
  const lower = [...peaks].reverse().map((peak, reverseIndex) => {
    const index = peaks.length - 1 - reverseIndex;
    const x = peaks.length === 1 ? 0 : (index / (peaks.length - 1)) * width;
    const y = middle + peak * (height / 2 - 4);
    return `${x} ${y}`;
  });
  return `M ${upper.join(" L ")} L ${lower.join(" L ")} Z`;
}

function linePath(samples: Array<{ timestamp_ms: number; value: number }>, width: number, height: number) {
  if (!samples.length) {
    return "";
  }
  const minValue = Math.min(...samples.map((sample) => sample.value));
  const maxValue = Math.max(...samples.map((sample) => sample.value));
  const span = Math.max(1e-6, maxValue - minValue);
  return samples
    .map((sample, index) => {
      const x = samples.length === 1 ? 0 : (index / (samples.length - 1)) * width;
      const y = height - ((sample.value - minValue) / span) * (height - 12) - 6;
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");
}

function segmentStyle(start: number, end: number, duration: number) {
  return {
    left: `${(start / duration) * 100}%`,
    width: `${Math.max(2.5, ((end - start) / duration) * 100)}%`,
  };
}

function normalizeTrackLabel(label: string) {
  return label.trim().toLowerCase();
}

function shortTrackLabel(label: string) {
  const lowered = normalizeTrackLabel(label);
  switch (lowered) {
    case "energy spike":
      return "energy";
    case "pitch spike":
      return "pitch";
    case "hesitation":
      return "hes.";
    case "speaker_overlap":
      return "overlap";
    default:
      return label.length > 16 ? `${label.slice(0, 14)}…` : label;
  }
}

function buildTrackView(track: SessionBundle["timeline_tracks"][number]) {
  const dense = track.type === "prosody" || track.items.length > 24;
  const sortedItems = [...track.items].sort((left, right) => left.start_ms - right.start_ms || left.end_ms - right.end_ms);
  const labelCounts = new Map<string, number>();
  sortedItems.forEach((item) => {
    const key = normalizeTrackLabel(item.label);
    labelCounts.set(key, (labelCounts.get(key) ?? 0) + 1);
  });

  if (!dense) {
    return {
      ...track,
      dense,
      items_for_view: sortedItems.map((item) => ({
        ...item,
        shortLabel: shortTrackLabel(item.label),
        count: 1,
      })),
      top_labels: Array.from(labelCounts.entries())
        .sort((left, right) => right[1] - left[1])
        .slice(0, 3)
        .map(([label, count]) => ({ label, count })),
    } satisfies TrackView;
  }

  const clusters: TrackViewItem[] = [];
  const mergeGapMs = track.type === "prosody" ? 850 : 500;
  for (const item of sortedItems) {
    const previous = clusters.at(-1);
    const shortLabel = shortTrackLabel(item.label);
    const sameTone = previous?.tone === item.tone;
    const sameLabel = previous?.shortLabel === shortLabel;
    const closeEnough = previous ? item.start_ms - previous.end_ms <= mergeGapMs : false;
    if (previous && sameTone && sameLabel && closeEnough) {
      previous.end_ms = Math.max(previous.end_ms, item.end_ms);
      previous.count += 1;
      previous.label = previous.count > 1 ? `${previous.shortLabel} ×${previous.count}` : previous.shortLabel;
      previous.evidence_refs = [...previous.evidence_refs, ...item.evidence_refs].slice(0, 3);
      previous.confidence = Math.max(previous.confidence ?? 0, item.confidence ?? 0);
      continue;
    }
    clusters.push({
      ...item,
      shortLabel,
      label: shortLabel,
      count: 1,
    });
  }

  return {
    ...track,
    dense,
    items_for_view: clusters,
    top_labels: Array.from(labelCounts.entries())
      .sort((left, right) => right[1] - left[1])
      .slice(0, 4)
      .map(([label, count]) => ({ label, count })),
  } satisfies TrackView;
}

function buildCueCards(cues: SessionBundle["nonverbal_cues"]) {
  const visible = cues
    .filter((cue) => cue.display_state !== "hidden")
    .sort((left, right) => left.start_ms - right.start_ms || left.end_ms - right.end_ms);
  const grouped: Array<SessionBundle["nonverbal_cues"][number] & { count: number }> = [];
  for (const cue of visible) {
    const previous = grouped.at(-1);
    const canMerge =
      previous &&
      previous.type === cue.type &&
      previous.family === cue.family &&
      cue.start_ms - previous.end_ms <= 1200;
    if (canMerge) {
      previous.end_ms = Math.max(previous.end_ms, cue.end_ms);
      previous.confidence = Math.max(previous.confidence, cue.confidence);
      previous.count += 1;
      continue;
    }
    grouped.push({ ...cue, count: 1 });
  }
  return grouped.slice(0, 12);
}

function sampleTrackItems(items: TrackViewItem[], limit: number) {
  if (items.length <= limit) return items;
  const sampled: TrackViewItem[] = [];
  const seen = new Set<string>();
  for (let index = 0; index < limit; index += 1) {
    const itemIndex = Math.round((index / Math.max(1, limit - 1)) * (items.length - 1));
    const item = items[itemIndex];
    if (!item || seen.has(item.item_id)) continue;
    sampled.push(item);
    seen.add(item.item_id);
  }
  return sampled;
}

export function SessionWorkspace({ jobId, audioSrc, spectrogramSrc, bundle }: SessionWorkspaceProps) {
  const router = useRouter();
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const waveformRef = useRef<HTMLDivElement | null>(null);
  const [currentTimeSec, setCurrentTimeSec] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [speakerFilter, setSpeakerFilter] = useState("all");
  const [emotionFilter, setEmotionFilter] = useState("all");
  const [confidenceFilter, setConfidenceFilter] = useState("all");
  const [questionOnly, setQuestionOnly] = useState(false);
  const [showHiddenProfile, setShowHiddenProfile] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("waveform");
  const [roleView, setRoleView] = useState<RoleView>(bundle.speaker_roles.primary_human_speaker_id ? "human" : "all");
  const [momentsView, setMomentsView] = useState<MomentsView>("cues");
  const [roleAssignments, setRoleAssignments] = useState<Record<string, "human" | "ai" | "unknown">>(() =>
    Object.fromEntries(bundle.speaker_roles.assignments.map((assignment) => [assignment.speaker_id, assignment.speaker_role])),
  );
  const [isSavingRoles, setIsSavingRoles] = useState(false);
  const [zoom, setZoom] = useState(1.4);
  const [hoverMs, setHoverMs] = useState<number | null>(null);
  const [expandedTracks, setExpandedTracks] = useState<Record<string, boolean>>({});
  const [showAllProfile, setShowAllProfile] = useState(false);
  const [showAllMoments, setShowAllMoments] = useState(false);
  const [showAllSegments, setShowAllSegments] = useState(false);
  const deferredSearch = useDeferredValue(searchQuery.trim().toLowerCase());
  const durationMs = Math.max(1, Math.round(bundle.session.duration_sec * 1000));
  const readinessTier = bundle.session.readiness_tier ?? "blocked";
  const transcriptionDecision = bundle.diagnostics.provider_decisions?.find((decision) => decision.kind === "transcription");
  const diarizationDecision = bundle.diagnostics.provider_decisions?.find((decision) => decision.kind === "diarization");
  const currentTimeMs = Math.round(currentTimeSec * 1000);
  const waveformWidth = Math.max(960, Math.round(Math.max(bundle.waveform.bucket_count, bundle.waveform.peaks.length, 320) * zoom * 2.6));
  const emotionOptions = bundle.content.view_summary.emotion_labels.length ? bundle.content.view_summary.emotion_labels : ["unlabeled"];
  const speakerOptions = Array.from(
    new Set(
      [
        ...bundle.content.sentences.map((sentence) => sentence.speaker_id),
        ...bundle.diarization.segments.map((segment) => segment.speaker_id),
      ].filter(Boolean),
    ),
  );
  const profileFields = showHiddenProfile
    ? bundle.profile_display
    : bundle.profile_display.filter((field) => field.display_state === "visible" || field.display_state === "muted");
  const questionTurnIds = new Set(bundle.questions.flatMap((question) => [question.question_turn_id, question.answer_turn_id]));
  const trackViews = useMemo(() => bundle.timeline_tracks.map((track) => buildTrackView(track)), [bundle.timeline_tracks]);
  const cueCards = useMemo(() => buildCueCards(bundle.nonverbal_cues), [bundle.nonverbal_cues]);
  const previewProfileFields = showAllProfile ? profileFields : profileFields.slice(0, 4);
  const previewSegments = showAllSegments ? bundle.diarization.segments : bundle.diarization.segments.slice(0, 5);
  const visibleCues = cueCards.filter((cue) => cue.display_state !== "hidden");
  const visibleVocalCues = bundle.nonverbal_cues.filter((cue) => cue.family === "vocal_sound" && cue.display_state !== "hidden");
  const visibleSignals = bundle.signals;
  const visibleQuestions = bundle.questions;
  const visibleEvents = bundle.events;
  const attributionLimited = visibleVocalCues.some((cue) => (cue.attribution_state ?? "unassigned") !== "strong");
  const transcriptReadyWithoutSentenceAlignment = Boolean(bundle.content.transcript.trim()) && !bundle.content.sentences.length;
  const profileCoverage = bundle.profile_coverage;
  const speakerRoleMap = useMemo(
    () => Object.fromEntries(bundle.speaker_roles.assignments.map((assignment) => [assignment.speaker_id, assignment.speaker_role])),
    [bundle.speaker_roles.assignments],
  );
  const cueMap = useMemo(() => {
    return new Map(
      bundle.content.sentences.map((sentence) => [
        sentence.sentence_id,
        bundle.nonverbal_cues.filter(
          (cue) =>
            cue.display_state !== "hidden" &&
            cue.start_ms <= sentence.end_ms &&
            cue.end_ms >= sentence.start_ms,
        ),
      ]),
    );
  }, [bundle.content.sentences, bundle.nonverbal_cues]);
  const filteredSentences = bundle.content.sentences.filter((sentence) => {
    const resolvedRole = sentence.speaker_role ?? speakerRoleMap[sentence.speaker_id] ?? "unknown";
    if (roleView === "human" && resolvedRole !== "human") return false;
    if (roleView === "ai" && resolvedRole !== "ai") return false;
    if (speakerFilter !== "all" && sentence.speaker_id !== speakerFilter) return false;
    if (emotionFilter !== "all" && sentence.emotion_label !== emotionFilter) return false;
    if (confidenceFilter === "high" && sentence.display_state !== "visible") return false;
    if (confidenceFilter === "medium" && sentence.display_state === "hidden") return false;
    if (questionOnly && !questionTurnIds.has(sentence.turn_id)) return false;
    if (deferredSearch && !sentence.text.toLowerCase().includes(deferredSearch)) return false;
    return true;
  });

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const onTimeUpdate = () => setCurrentTimeSec(audio.currentTime);
    audio.addEventListener("timeupdate", onTimeUpdate);
    return () => audio.removeEventListener("timeupdate", onTimeUpdate);
  }, []);

  const seekToMs = (timestampMs: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = Math.max(0, timestampMs / 1000);
    void audio.play().catch(() => undefined);
  };

  const timestampFromPointer = (clientX: number, bounds: DOMRect, scrollLeft: number, renderWidth: number) => {
    const offsetX = scrollLeft + clientX - bounds.left;
    const ratio = Math.max(0, Math.min(1, offsetX / renderWidth));
    return Math.round(ratio * durationMs);
  };

  const seekFromPointer = (clientX: number, bounds: DOMRect, scrollLeft: number, renderWidth: number) => {
    seekToMs(timestampFromPointer(clientX, bounds, scrollLeft, renderWidth));
  };

  const hoverFromPointer = (clientX: number, bounds: DOMRect, scrollLeft: number, renderWidth: number) => {
    setHoverMs(timestampFromPointer(clientX, bounds, scrollLeft, renderWidth));
  };

  const activeSentenceId = bundle.content.sentences.find(
    (sentence) => currentTimeMs >= sentence.start_ms && currentTimeMs <= sentence.end_ms,
  )?.sentence_id;
  const currentX = (currentTimeMs / durationMs) * waveformWidth;
  const hoverX = hoverMs === null ? null : (hoverMs / durationMs) * waveformWidth;
  const waveformPeaks = bundle.waveform.peaks.length
    ? bundle.waveform.peaks
    : Array.from({ length: 240 }, (_, index) => 0.18 + Math.abs(Math.sin(index / 8)) * 0.42);

  async function updateRoleAssignment(speakerId: string, speakerRole: "human" | "ai" | "unknown") {
    const previousAssignments = roleAssignments;
    const nextAssignments = { ...roleAssignments, [speakerId]: speakerRole };
    setRoleAssignments(nextAssignments);
    setIsSavingRoles(true);
    try {
      const response = await fetch(`/api/sessions/${jobId}/roles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assignments: nextAssignments }),
      });
      if (!response.ok) {
        throw new Error("Could not update speaker roles.");
      }
      router.refresh();
    } catch (_error) {
      setRoleAssignments(previousAssignments);
    } finally {
      setIsSavingRoles(false);
    }
  }

  function toggleTrackExpansion(trackId: string) {
    setExpandedTracks((current) => ({ ...current, [trackId]: !current[trackId] }));
  }

  function renderMomentsPanel() {
    if (momentsView === "cues") {
      const items = showAllMoments ? visibleCues : visibleCues.slice(0, 5);
      if (!visibleCues.length) {
        return <div className="empty-state compact">No timestamped non-verbal cues are available for this session yet.</div>;
      }
      return (
        <>
          <div className="stack compact">
            {items.map((cue) => (
              <button className="question-card compact-card" key={cue.cue_id} onClick={() => seekToMs(cue.start_ms)} type="button">
                <strong>{cue.count > 1 ? `${cue.label} ×${cue.count}` : cue.label}</strong>
                <span className="microcopy">
                  {formatClock(cue.start_ms)} to {formatClock(cue.end_ms)} · {cue.source} · {Math.round(cue.confidence * 100)}%
                </span>
                <div className="badge-row">
                  <span className={`badge cue-badge ${trackTone(cue.family === "vocal_sound" ? "accent" : "warning")}`}>{cue.family}</span>
                  <span className="badge">{attributionLabel(cue.attribution_state)}</span>
                  {cue.speaker_id ? <span className="badge">{cue.speaker_id}</span> : null}
                </div>
              </button>
            ))}
          </div>
          {visibleCues.length > 5 ? (
            <button className="load-more-button" onClick={() => setShowAllMoments((current) => !current)} type="button">
              {showAllMoments ? "Show fewer tagged moments" : `View ${visibleCues.length - 5} more tagged moments`}
            </button>
          ) : null}
        </>
      );
    }

    if (momentsView === "questions") {
      const items = showAllMoments ? visibleQuestions : visibleQuestions.slice(0, 4);
      if (!visibleQuestions.length) {
        return <div className="empty-state compact">No question windows were mapped for this session.</div>;
      }
      return (
        <>
          <div className="stack compact">
            {items.map((question) => (
              <button
                className="question-card compact-card"
                key={question.question_id}
                onClick={() => {
                  const turn = bundle.turns.find((item) => item.turn_id === question.question_turn_id);
                  if (turn) seekToMs(turn.start_ms);
                }}
                type="button"
              >
                <strong>{question.question_text}</strong>
                <span className="microcopy">
                  {formatMs(question.response_latency_ms)} · hesitation {question.hesitation_score} · directness {question.directness_score}
                </span>
                <div className="badge-row">
                  <span className="badge accent">{question.affect_tag}</span>
                  <span className="microcopy">{question.explainability_mask.join(", ") || "clean interpretation"}</span>
                </div>
              </button>
            ))}
          </div>
          {visibleQuestions.length > 4 ? (
            <button className="load-more-button" onClick={() => setShowAllMoments((current) => !current)} type="button">
              {showAllMoments ? "Show fewer questions" : `View ${visibleQuestions.length - 4} more questions`}
            </button>
          ) : null}
        </>
      );
    }

    if (momentsView === "signals") {
      const items = showAllMoments ? visibleSignals : visibleSignals.slice(0, 4);
      return (
        <>
          <div className="signal-card-grid compact-grid rail-signal-grid">
            {items.map((signal) => (
              <article className={`signal-card ${signal.status}`} key={signal.key}>
                <div className="badge-row">
                  <span className="badge accent">{signal.label}</span>
                  <span className={`badge ${signal.status === "risk" ? "warn" : signal.status === "healthy" ? "ok" : ""}`}>{signal.status}</span>
                  <span className="badge">{evidenceLabel(signal.evidence_class)}</span>
                </div>
                <strong>{signal.score}/100</strong>
                <p>{signal.summary}</p>
                <div className="microcopy">{signal.explainability_mask.join(", ") || "no active explainability mask"}</div>
              </article>
            ))}
          </div>
          {visibleSignals.length > 4 ? (
            <button className="load-more-button" onClick={() => setShowAllMoments((current) => !current)} type="button">
              {showAllMoments ? "Show fewer signals" : `View ${visibleSignals.length - 4} more signals`}
            </button>
          ) : null}
        </>
      );
    }

    const items = showAllMoments ? visibleEvents : visibleEvents.slice(0, 5);
    return (
      <>
        <div className="stack compact">
          {items.map((event) => (
            <button className="info-row event-row compact-card" key={event.event_id} onClick={() => seekToMs(event.begin_ms)} type="button">
              <strong>{event.type}</strong>
              <span className="microcopy">
                {formatClock(event.begin_ms)} to {formatClock(event.end_ms)} · {event.severity}
              </span>
              <span className="microcopy">{event.detail ?? "No detail attached."}</span>
            </button>
          ))}
        </div>
        {visibleEvents.length > 5 ? (
          <button className="load-more-button" onClick={() => setShowAllMoments((current) => !current)} type="button">
            {showAllMoments ? "Show fewer events" : `View ${visibleEvents.length - 5} more events`}
          </button>
        ) : null}
      </>
    );
  }

  return (
    <section className="detail-layout workspace-layout">
      <div className="detail-main workspace-main">
        <section className="panel panel-spacious inspector-panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow muted">Audio Inspector</span>
              <h2>Diarized waveform, non-verbal cues, and transcript timing</h2>
            </div>
            <span className="microcopy">
              Waveform is the primary surface. Spectrogram is for inspection, and digital view exposes the continuous prosody readouts.
            </span>
          </div>

          {readinessTier === "blocked" ? (
            <div className="gate-banner">
              <strong>Transcript extraction is blocked for this upload.</strong>
              <span className="microcopy">
                {bundle.diarization.notes.join(" ") || "Quality and waveform inspection may still be available, but the current provider stack did not produce a usable transcript."}
                {transcriptionDecision ? ` Transcript path: ${transcriptionDecision.provider_key.replaceAll("_", " ")}.` : ""}
              </span>
            </div>
          ) : null}

          {readinessTier === "transcript_only" || (bundle.diarization.readiness_state === "blocked" && readinessTier !== "blocked") ? (
            <div className="gate-banner">
              <strong>Transcript and quality analysis are ready. Speaker-attributed cues are limited for this upload.</strong>
              <span className="microcopy">
                {bundle.diarization.notes.join(" ") || "The local transcript is still trustworthy, but speaker lanes and vocal-cue attribution need stronger diarization."}
                {transcriptionDecision ? ` Transcript provider: ${transcriptionDecision.provider_key.replaceAll("_", " ")}.` : ""}
              </span>
            </div>
          ) : null}

          {readinessTier === "partial" || (bundle.diarization.readiness_state === "fallback" && readinessTier !== "blocked") || attributionLimited ? (
            <div className="gate-banner fallback">
              <strong>{attributionLimited ? "Cue timing is available, but speaker attribution stays limited." : "Using limited speaker coverage for this upload."}</strong>
              <span className="microcopy">
                {bundle.diarization.notes.join(" ") || "Transcript and timing are available now; speaker attribution remains provisional until stronger diarization is configured."}
                {attributionLimited ? " Vocal cue timing remains visible, but attribution is muted unless diarization is strong enough." : ""}
                {diarizationDecision ? ` Diarization path: ${diarizationDecision.provider_key.replaceAll("_", " ")}.` : ""}
              </span>
            </div>
          ) : null}

          <audio ref={audioRef} className="audio-player" controls preload="metadata" src={audioSrc} />

          <div className="inspector-toolbar">
            <div className="mode-toggle">
              {(["waveform", "spectrogram", "digital"] as const).map((mode) => (
                <button
                  key={mode}
                  className={`filter-toggle ${viewMode === mode ? "active" : ""}`}
                  onClick={() => setViewMode(mode)}
                  type="button"
                >
                  {mode === "waveform" ? "Waveform" : mode === "spectrogram" ? "Spectrogram" : "Digital"}
                </button>
              ))}
            </div>
            <label className="zoom-control">
              <span className="microcopy">Zoom</span>
              <input max={4} min={1} onChange={(event) => setZoom(Number(event.target.value))} step={0.2} type="range" value={zoom} />
            </label>
            <div className="badge-row">
              <span className="badge accent">Now {formatClock(currentTimeMs)}</span>
              <span className="badge">{hoverMs === null ? "Hover for timestamp" : `Hover ${formatClock(hoverMs)}`}</span>
              <span className="badge">
                {bundle.speaker_roles.primary_human_speaker_id ? `Human focus ${bundle.speaker_roles.primary_human_speaker_id}` : "Human role pending"}
              </span>
            </div>
          </div>

          <div className="media-surface-shell">
            {viewMode === "waveform" ? (
              <div
                className="waveform-surface"
                onClick={(event) =>
                  seekFromPointer(
                    event.clientX,
                    event.currentTarget.getBoundingClientRect(),
                    event.currentTarget.scrollLeft,
                    waveformWidth,
                  )
                }
                onMouseLeave={() => setHoverMs(null)}
                onMouseMove={(event) =>
                  hoverFromPointer(
                    event.clientX,
                    event.currentTarget.getBoundingClientRect(),
                    event.currentTarget.scrollLeft,
                    waveformWidth,
                  )
                }
                ref={waveformRef}
              >
                <svg className="waveform-svg" style={{ width: `${waveformWidth}px` }} viewBox={`0 0 ${waveformWidth} 220`}>
                  <path className="waveform-area" d={waveformPath(waveformPeaks, waveformWidth, 220)} />
                  <line className="waveform-playhead" x1={currentX} x2={currentX} y1={0} y2={220} />
                  {hoverX !== null ? <line className="waveform-hover" x1={hoverX} x2={hoverX} y1={0} y2={220} /> : null}
                </svg>
              </div>
            ) : null}

            {viewMode === "spectrogram" ? (
              bundle.spectrogram.readiness_state === "ready" ? (
                <div
                  className="spectrogram-surface"
                  onClick={(event) =>
                    seekFromPointer(
                      event.clientX,
                      event.currentTarget.getBoundingClientRect(),
                      event.currentTarget.scrollLeft,
                      waveformWidth,
                    )
                  }
                  onMouseLeave={() => setHoverMs(null)}
                  onMouseMove={(event) =>
                    hoverFromPointer(
                      event.clientX,
                      event.currentTarget.getBoundingClientRect(),
                      event.currentTarget.scrollLeft,
                      waveformWidth,
                    )
                  }
                  ref={waveformRef}
                >
                  <img alt="Session spectrogram" className="spectrogram-image" src={spectrogramSrc} style={{ width: `${waveformWidth}px` }} />
                  <div className="spectrogram-playhead" style={{ left: `${(currentTimeMs / durationMs) * 100}%` }} />
                </div>
              ) : (
                <div className="empty-state">Spectrogram rendering is not available for this session.</div>
              )
            ) : null}

            {viewMode === "digital" ? (
              <div className="digital-surface">
                <div className="digital-grid">
                  <article className="digital-card">
                    <span className="eyebrow muted">Diarization</span>
                    <strong>{bundle.diarization.readiness_state}</strong>
                    <span className="microcopy">{bundle.diarization.notes.join(", ") || "speaker lanes aligned"}</span>
                  </article>
                  <article className="digital-card">
                    <span className="eyebrow muted">Non-verbal cues</span>
                    <strong>{bundle.nonverbal_cues.filter((cue) => cue.display_state !== "hidden").length}</strong>
                    <span className="microcopy">visible or muted cues on the timeline</span>
                  </article>
                  <article className="digital-card">
                    <span className="eyebrow muted">Waveform buckets</span>
                    <strong>{bundle.waveform.bucket_count}</strong>
                    <span className="microcopy">{bundle.waveform.sample_count} normalized samples decimated</span>
                  </article>
                </div>
                <div className="prosody-grid">
                  {bundle.prosody_tracks.map((track) => (
                    <article className="prosody-card" key={track.key}>
                      <div className="prosody-head">
                        <strong>{track.label}</strong>
                        <span className="microcopy">
                          {track.display_state} · {track.unit}
                        </span>
                      </div>
                      {track.samples.length ? (
                        <svg className="prosody-svg" viewBox="0 0 640 140">
                          <path className="prosody-line" d={linePath(track.samples, 640, 140)} />
                        </svg>
                      ) : (
                        <div className="empty-state compact">No continuous samples available.</div>
                      )}
                      <span className="microcopy">{track.notes.join(" ")}</span>
                    </article>
                  ))}
                </div>
              </div>
            ) : null}
          </div>

          <div className="minimap-shell">
            <svg
              className="minimap-svg"
              onClick={(event) => seekFromPointer(event.clientX, event.currentTarget.getBoundingClientRect(), 0, event.currentTarget.clientWidth)}
              viewBox="0 0 1000 70"
            >
              <path className="minimap-area" d={waveformPath(waveformPeaks, 1000, 70)} />
              <line className="waveform-playhead" x1={(currentTimeMs / durationMs) * 1000} x2={(currentTimeMs / durationMs) * 1000} y1={0} y2={70} />
            </svg>
          </div>

          <div className="track-stack">
            {trackViews.map((track) => (
              <div className="track-row" key={track.track_id}>
                <div className="track-meta">
                  <strong>{track.label}</strong>
                  <span className="microcopy">
                    {track.items.length} items · {track.status}
                  </span>
                  {track.top_labels.length ? (
                    <div className="badge-row track-summary">
                      {track.top_labels.map((entry) => (
                        <span className="badge" key={`${track.track_id}-${entry.label}`}>
                          {shortTrackLabel(entry.label)} ×{entry.count}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
                <div className="track-content">
                  {track.status === "blocked" && !track.items.length ? (
                    <div className="track-gate">{track.notes.join(" ") || "This lane is gated for the current session."}</div>
                  ) : !track.items_for_view.length ? (
                    <div className="track-empty">
                      {track.track_id === "speaker-lanes" && bundle.diarization.readiness_state === "fallback"
                        ? "Speaker lanes are provisional for this upload. Transcript timing is still available, but speaker attribution needs stronger diarization."
                        : track.notes.join(" ") || "No aligned items are available for this lane yet."}
                    </div>
                  ) : (
                    <>
                      <div className={`track-lane ${track.dense ? "dense" : ""}`}>
                        {(expandedTracks[track.track_id]
                          ? track.items_for_view
                          : sampleTrackItems(track.items_for_view, track.dense ? 18 : 12)
                        ).map((item) => (
                          <button
                            key={item.item_id}
                            aria-label={`${item.label} from ${formatClock(item.start_ms)} to ${formatClock(item.end_ms)}`}
                            className={`track-chip ${trackTone(item.tone)} ${track.dense ? "compact" : ""}`}
                            onClick={() => seekToMs(item.start_ms)}
                            style={segmentStyle(item.start_ms, item.end_ms || item.start_ms + 220, durationMs)}
                            title={`${item.label} · ${formatClock(item.start_ms)} to ${formatClock(item.end_ms)}`}
                            type="button"
                          >
                            {track.dense ? "" : item.label}
                          </button>
                        ))}
                      </div>
                      {track.items_for_view.length > (track.dense ? 18 : 12) ? (
                        <div className="track-actions">
                          <button className="load-more-button subtle" onClick={() => toggleTrackExpansion(track.track_id)} type="button">
                            {expandedTracks[track.track_id]
                              ? `Collapse ${track.label.toLowerCase()}`
                              : `View ${track.items_for_view.length - (track.dense ? 18 : 12)} more ${track.label.toLowerCase()} items`}
                          </button>
                        </div>
                      ) : null}
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel panel-spacious transcript-panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow muted">Transcript Inspector</span>
              <h2>Entire transcript with sentence emotion and cue overlays</h2>
            </div>
            <span className="microcopy">
              Search, filter, then jump to a sentence, cue, speaker segment, or question moment on the shared timeline.
            </span>
          </div>

          <div className="filter-bar">
            <input
              aria-label="Search transcript"
              className="filter-input"
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search the transcript"
              type="search"
              value={searchQuery}
            />
            <select aria-label="Filter by speaker" className="filter-select" onChange={(event) => setSpeakerFilter(event.target.value)} value={speakerFilter}>
              <option value="all">All speakers</option>
              {speakerOptions.map((speaker) => (
                <option key={speaker} value={speaker}>
                  {speaker}
                </option>
              ))}
            </select>
            <select aria-label="Filter by emotion" className="filter-select" onChange={(event) => setEmotionFilter(event.target.value)} value={emotionFilter}>
              <option value="all">All emotions</option>
              {emotionOptions.map((emotion) => (
                <option key={emotion} value={emotion}>
                  {emotion}
                </option>
              ))}
            </select>
            <select aria-label="Filter by confidence" className="filter-select" onChange={(event) => setConfidenceFilter(event.target.value)} value={confidenceFilter}>
              <option value="all">All confidence bands</option>
              <option value="high">Visible only</option>
              <option value="medium">Visible + muted</option>
            </select>
            <button className={`filter-toggle ${questionOnly ? "active" : ""}`} onClick={() => setQuestionOnly((current) => !current)} type="button">
              Question-linked only
            </button>
            <div className="mode-toggle role-toggle">
              {([
                ["human", "Human only"],
                ["all", "Human + AI"],
                ["ai", "AI context"],
              ] as const).map(([value, label]) => (
                <button
                  key={value}
                  className={`filter-toggle ${roleView === value ? "active" : ""}`}
                  onClick={() => setRoleView(value)}
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="transcript-list transcript-sentence-list">
            {filteredSentences.length ? (
              filteredSentences.map((sentence) => {
                const tokenMap = bundle.content.tokens.filter((token) => token.sentence_id === sentence.sentence_id);
                const sentenceCues = cueMap.get(sentence.sentence_id) ?? [];
                const active = activeSentenceId === sentence.sentence_id;
                return (
                  <button
                    key={sentence.sentence_id}
                    className={`sentence-card ${emotionTone(sentence.emotion_label)} ${sentence.display_state} ${active ? "active" : ""}`}
                    onClick={() => seekToMs(sentence.start_ms)}
                    type="button"
                  >
                    <div className="sentence-card-head">
                      <div className="badge-row">
                        <span className="badge">{sentence.speaker_id}</span>
                        <span className="badge">{sentence.speaker_role ?? speakerRoleMap[sentence.speaker_id] ?? "unknown"}</span>
                        {sentence.display_state !== "hidden" ? <span className={`badge accent ${emotionTone(sentence.emotion_label)}`}>{sentence.emotion_label}</span> : null}
                        <span className="badge">{sentence.source}</span>
                        {sentenceCues.slice(0, 3).map((cue) => (
                          <span className={`badge cue-badge ${trackTone(cue.family === "vocal_sound" ? "accent" : "warning")}`} key={cue.cue_id}>
                            {cue.label}
                          </span>
                        ))}
                      </div>
                      <span className="microcopy">
                        {formatClock(sentence.start_ms)} to {formatClock(sentence.end_ms)} · confidence {Math.round(sentence.confidence * 100)}%
                      </span>
                    </div>
                    <p className="sentence-copy">
                      {tokenMap.length
                        ? tokenMap.map((token) => (
                            <span key={token.token_id} className={`token-chip ${emotionTone(token.emotion_label)} ${token.display_state}`}>
                              {markText(`${token.word} `, deferredSearch)}
                            </span>
                          ))
                        : markText(sentence.text, deferredSearch)}
                    </p>
                    <div className="sentence-card-foot">
                      <span className="microcopy">{sentence.sentiment_label ?? "no sentiment label"}</span>
                      <span className="microcopy">{sentence.explainability_mask.join(", ") || "clean interpretation"}</span>
                    </div>
                  </button>
                );
              })
            ) : (
              <div className="empty-state">
                {bundle.content.sentences.length
                  ? "No transcript sentences match the current filters."
                  : transcriptReadyWithoutSentenceAlignment
                    ? "The transcript is present, but sentence timing or alignment is still missing for this session. The waveform and readiness banners above reflect the strongest currently trustworthy layer."
                    : "Transcript timing or sentence alignment is not available for this session yet. Use the quality and readiness banners above as the source of truth for what is currently trustworthy."}
              </div>
            )}
          </div>
        </section>
      </div>

      <aside className="detail-side workspace-side">
        <section className="panel panel-spacious">
          <div className="section-heading">
            <div>
              <span className="eyebrow muted">Session Controls</span>
              <h2>Human-first controls and profile coverage</h2>
            </div>
            <span className="microcopy">
              Auto-detection keeps the human in the primary lane. Adjust a speaker if the upload was classified incorrectly.
            </span>
          </div>
          <div className="summary-grid rail-summary-grid">
            <article className="summary-card">
              <span className="eyebrow muted">Primary human</span>
              <strong>{bundle.speaker_roles.primary_human_speaker_id ?? "unassigned"}</strong>
              <span className="microcopy">default focus for emotion, hesitation, and behavior scores</span>
            </article>
            <article className="summary-card">
              <span className="eyebrow muted">Primary AI</span>
              <strong>{bundle.speaker_roles.primary_ai_speaker_id ?? "unassigned"}</strong>
              <span className="microcopy">kept visible as context, but excluded from headline human metrics</span>
            </article>
          </div>
          <div className="stack compact rail-section-stack">
            <div className="subpanel">
              <div className="subpanel-head">
                <strong>Speaker roles</strong>
                <span className="microcopy">{bundle.speakers.length} speakers</span>
              </div>
              <div className="stack compact">
                {bundle.speakers.map((speaker) => {
                  const assignment = bundle.speaker_roles.assignments.find((item) => item.speaker_id === speaker.speaker_id);
                  const activeRole = roleAssignments[speaker.speaker_id] ?? speaker.speaker_role ?? "unknown";
                  return (
                    <div className="profile-row role-row" key={speaker.speaker_id}>
                      <div>
                        <strong>{speaker.speaker_id}</strong>
                        <div className="microcopy">
                          {(assignment?.source ?? speaker.role_source ?? "unavailable")} · {Math.round((assignment?.confidence ?? speaker.role_confidence ?? 0) * 100)}%
                        </div>
                      </div>
                      <div className="profile-value">
                        <select
                          aria-label={`Role override for ${speaker.speaker_id}`}
                          className="filter-select"
                          disabled={isSavingRoles}
                          onChange={(event) => void updateRoleAssignment(speaker.speaker_id, event.target.value as "human" | "ai" | "unknown")}
                          value={activeRole}
                        >
                          <option value="human">Human</option>
                          <option value="ai">AI</option>
                          <option value="unknown">Unknown</option>
                        </select>
                        <span className="microcopy">{assignment?.notes.join(", ") || "manual override available"}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="subpanel">
              <div className="subpanel-head">
                <strong>Voice profile</strong>
                <div className="subpanel-actions">
                  <button className={`filter-toggle compact-toggle ${showHiddenProfile ? "active" : ""}`} onClick={() => setShowHiddenProfile((current) => !current)} type="button">
                    {showHiddenProfile ? "Hide muted" : "Show hidden"}
                  </button>
                </div>
              </div>
              <div className="info-row compact-row">
                <strong>Visible fields</strong>
                <span className="microcopy">
                  {bundle.profile_display.filter((field) => field.display_state === "visible" || field.display_state === "muted").length} of {bundle.profile_display.length}
                </span>
              </div>
              <div className="summary-grid rail-summary-grid">
                <article className="summary-card">
                  <span className="eyebrow muted">Model-backed</span>
                  <strong>{profileCoverage.model_backed_fields.length}</strong>
                  <span className="microcopy">fields supported by configured local models</span>
                </article>
                <article className="summary-card">
                  <span className="eyebrow muted">Metadata-only</span>
                  <strong>{profileCoverage.metadata_only_fields.length}</strong>
                  <span className="microcopy">trusted benchmark or metadata-backed fields</span>
                </article>
                <article className="summary-card">
                  <span className="eyebrow muted">Hidden / unavailable</span>
                  <strong>{profileCoverage.hidden_fields.length + profileCoverage.unavailable_fields.length}</strong>
                  <span className="microcopy">withheld because evidence or adapters are not strong enough</span>
                </article>
              </div>
              <div className="stack compact">
                {previewProfileFields.map((field) => (
                  <div className="profile-row" key={field.key}>
                    <div>
                      <strong>{field.label}</strong>
                      <div className="microcopy">
                        {field.source} · {field.display_state} · confidence {Math.round(field.confidence * 100)}%
                      </div>
                    </div>
                    <div className="profile-value">
                      <span className={`badge ${field.display_state === "visible" ? "ok" : field.display_state === "muted" ? "accent" : ""}`}>{field.value}</span>
                      <span className="microcopy">{field.warning_flags.join(", ") || field.summary || "no extra caveat"}</span>
                    </div>
                  </div>
                ))}
              </div>
              {profileFields.length > 4 ? (
                <button className="load-more-button" onClick={() => setShowAllProfile((current) => !current)} type="button">
                  {showAllProfile ? "Show fewer profile fields" : `View ${profileFields.length - 4} more profile fields`}
                </button>
              ) : null}
            </div>
            {bundle.speaker_roles.notes.length ? <p className="microcopy">{bundle.speaker_roles.notes.join(" ")}</p> : null}
          </div>
        </section>

        <section className="panel panel-spacious">
          <div className="section-heading">
            <div>
              <span className="eyebrow muted">Moments</span>
              <h2>Tagged moments, questions, and signals</h2>
            </div>
            <span className="microcopy">Switch the rail between key cue sets instead of rendering every ledger at once.</span>
          </div>
          <div className="segmented-control" role="tablist" aria-label="Moments view">
            {([
              ["cues", `Tagged moments (${visibleCues.length})`],
              ["questions", `Questions (${visibleQuestions.length})`],
              ["signals", `Signals (${visibleSignals.length})`],
              ["events", `Event ledger (${visibleEvents.length})`],
            ] as const).map(([value, label]) => (
              <button
                key={value}
                className={`segmented-button ${momentsView === value ? "active" : ""}`}
                onClick={() => {
                  setMomentsView(value);
                  setShowAllMoments(false);
                }}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>
          <div className="rail-panel-body">{renderMomentsPanel()}</div>
        </section>

        <section className="panel panel-spacious">
          <div className="section-heading">
            <div>
              <span className="eyebrow muted">Coverage</span>
              <h2>Diarization, audience, and diagnostics</h2>
            </div>
            <span className="microcopy">Operational detail is available on demand so the workspace stays readable.</span>
          </div>
          <div className="summary-grid rail-summary-grid">
            <article className="summary-card">
              <span className="eyebrow muted">Speaker coverage</span>
              <strong>{bundle.diarization.readiness_state}</strong>
              <span className="microcopy">{bundle.diarization.notes.join(", ") || "speaker lanes ready"}</span>
            </article>
            <article className="summary-card">
              <span className="eyebrow muted">Tagged cues</span>
              <strong>{visibleCues.length}</strong>
              <span className="microcopy">visible or muted non-verbal cues available on the timeline</span>
            </article>
            <article className="summary-card">
              <span className="eyebrow muted">Questions</span>
              <strong>{bundle.questions.length}</strong>
              <span className="microcopy">mapped question-answer windows with hesitation and affect notes</span>
            </article>
            <article className="summary-card">
              <span className="eyebrow muted">Cue attribution</span>
              <strong>{visibleVocalCues.length ? `${Math.round((visibleVocalCues.filter((cue) => cue.attribution_state === "strong").length / visibleVocalCues.length) * 100)}%` : "0%"}</strong>
              <span className="microcopy">share of visible vocal cues with strong speaker attribution</span>
            </article>
            <article className="summary-card">
              <span className="eyebrow muted">Benchmark-backed signals</span>
              <strong>{bundle.signals.filter((signal) => signal.evidence_class === "benchmark_backed").length}</strong>
              <span className="microcopy">headline signals grounded in benchmark-backed evidence</span>
            </article>
          </div>

          <details className="details-block" open>
            <summary>Speaker segments</summary>
            <div className="stack compact details-content">
              {previewSegments.length ? (
                previewSegments.map((segment) => (
                  <button className="info-row event-row compact-card" key={segment.segment_id} onClick={() => seekToMs(segment.start_ms)} type="button">
                    <strong>{segment.label ?? segment.speaker_id}</strong>
                    <span className="microcopy">
                      {formatClock(segment.start_ms)} to {formatClock(segment.end_ms)} · {Math.round(segment.confidence * 100)}%
                    </span>
                  </button>
                ))
              ) : (
                <div className="empty-state compact">
                  {bundle.diarization.readiness_state === "fallback"
                    ? "Speaker segmentation is provisional for this upload. Transcript timing is still available while diarization remains limited."
                    : "No speaker segments are available for this session."}
                </div>
              )}
              {bundle.diarization.segments.length > 5 ? (
                <button className="load-more-button" onClick={() => setShowAllSegments((current) => !current)} type="button">
                  {showAllSegments ? "Show fewer speaker segments" : `View ${bundle.diarization.segments.length - 5} more speaker segments`}
                </button>
              ) : null}
            </div>
          </details>

          <details className="details-block">
            <summary>Session summary metrics</summary>
            <div className="metric-stack details-content">
              {Object.entries(bundle.metrics).map(([key, metric]) => (
                <div className="metric-row" key={key}>
                  <span className="row-label">{metric.name}</span>
                  <strong>{formatMetric(metric.value, metric.unit)}</strong>
                </div>
              ))}
            </div>
          </details>

          <details className="details-block">
            <summary>Audience and speakers</summary>
            <div className="stack compact details-content">
              {bundle.speakers.map((speaker) => (
                <div className="info-row compact-row" key={speaker.speaker_id}>
                  <strong>{speaker.role ? `${speaker.role} · ${speaker.speaker_id}` : speaker.speaker_id}</strong>
                  <span className="microcopy">
                    talk {formatPct(speaker.talk_ratio)} · avg turn {formatMs(speaker.avg_turn_ms)} · interruptions {speaker.interruption_count}
                  </span>
                </div>
              ))}
            </div>
          </details>

          <details className="details-block">
            <summary>Adapters and stage posture</summary>
            <div className="stack compact details-content">
              {bundle.stage_status.map((stage) => (
                <div className="info-row compact-row" key={stage.key}>
                  <strong>{stage.label}</strong>
                  <span className="microcopy">
                    {stage.status} · {stage.caveats.join(", ") || stage.summary}
                  </span>
                </div>
              ))}
              {bundle.diagnostics.adapters.slice(0, 8).map((adapter) => (
                <div className="info-row compact-row" key={adapter.key}>
                  <strong>{adapter.name}</strong>
                  <span className="microcopy">
                    {adapter.category} · {adapter.available ? "available" : "not installed"} · {adapter.license_class ?? "license unknown"}
                  </span>
                </div>
              ))}
            </div>
          </details>
        </section>
      </aside>
    </section>
  );
}
