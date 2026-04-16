"use client";

import { startTransition, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

type JobActivityEntry = {
  stage_key: string;
  stage_label: string;
  message: string;
  completed_at: string;
  percent_complete: number;
};

type SessionJobStatus = {
  job_id: string;
  status: "created" | "uploaded" | "queued" | "processing" | "completed" | "failed";
  stage_key: string | null;
  stage_label: string | null;
  stage_index: number;
  stage_count: number;
  percent_complete: number;
  message: string;
  eta_seconds: number;
  started_at: string | null;
  updated_at: string;
  error: string | null;
  history: JobActivityEntry[];
};

const ACTIVE_JOB_KEY = "spectrum-active-analysis";
const MAX_FILE_BYTES = 512 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = new Set(["wav", "mp3", "m4a"]);
const CLIENT_STAGE_COUNT = 15;

function clamp(value: number, minimum: number, maximum: number) {
  return Math.max(minimum, Math.min(maximum, value));
}

function fileExtension(name: string) {
  return name.split(".").pop()?.toLowerCase() ?? "";
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatSeconds(totalSeconds: number | null) {
  if (totalSeconds === null) {
    return "estimating";
  }
  const safe = Math.max(0, Math.round(totalSeconds));
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  if (minutes > 0) {
    return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
  }
  return `${seconds}s`;
}

function estimateUploadSeconds(fileSizeBytes: number) {
  const fileSizeMb = fileSizeBytes / (1024 * 1024);
  return clamp(Math.round(fileSizeMb / 8), 1, 20);
}

function estimateAnalysisSeconds(durationSec: number | null) {
  if (durationSec === null) {
    return 30;
  }
  return clamp(Math.round(6 + durationSec * 0.8), 8, 180);
}

async function detectAudioDuration(file: File) {
  const objectUrl = URL.createObjectURL(file);
  try {
    const duration = await new Promise<number | null>((resolve) => {
      const audio = document.createElement("audio");
      audio.preload = "metadata";
      audio.src = objectUrl;
      audio.onloadedmetadata = () => resolve(Number.isFinite(audio.duration) ? audio.duration : null);
      audio.onerror = () => resolve(null);
    });
    return duration;
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

function fileTitle(name: string) {
  return name.replace(/\.[^/.]+$/, "").replaceAll(/[_-]+/g, " ").trim();
}

function validateAudioFile(file: File) {
  const extension = fileExtension(file.name);
  if (!ACCEPTED_EXTENSIONS.has(extension)) {
    return "Upload a WAV, MP3, or M4A audio file.";
  }
  if (file.size > MAX_FILE_BYTES) {
    return "This demo caps uploads at 512 MB.";
  }
  return null;
}

export function AnalyzeAudioPanel() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [durationSec, setDurationSec] = useState<number | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [isInspecting, setIsInspecting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<SessionJobStatus | null>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem(ACTIVE_JOB_KEY);
    if (stored) {
      setActiveJobId(stored);
    }
  }, []);

  useEffect(() => {
    if (!activeJobId) {
      return;
    }

    let isMounted = true;
    const poll = async () => {
      const response = await fetch(`/api/sessions/${activeJobId}/status`, { cache: "no-store" });
      if (!response.ok) {
        if (isMounted) {
          setRuntimeError("Could not load live analysis progress.");
          setActiveJobId(null);
        }
        return;
      }
      const nextStatus = (await response.json()) as SessionJobStatus;
      if (!isMounted) {
        return;
      }
      setJobStatus(nextStatus);
      if (nextStatus.status === "completed") {
        window.localStorage.removeItem(ACTIVE_JOB_KEY);
        setActiveJobId(null);
        setIsSubmitting(false);
        startTransition(() => {
          router.refresh();
          router.push(`/sessions/${activeJobId}`);
        });
      }
      if (nextStatus.status === "failed") {
        window.localStorage.removeItem(ACTIVE_JOB_KEY);
        setActiveJobId(null);
        setIsSubmitting(false);
        setRuntimeError(nextStatus.error || "Analysis failed before results could be saved.");
      }
    };

    poll().catch(() => {
      setRuntimeError("Could not load live analysis progress.");
      setActiveJobId(null);
    });
    const intervalId = window.setInterval(() => {
      poll().catch(() => {
        setRuntimeError("Could not load live analysis progress.");
        setActiveJobId(null);
      });
    }, 1000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [activeJobId, router]);

  const preflightEstimate = useMemo(() => {
    if (!selectedFile) {
      return null;
    }
    return estimateUploadSeconds(selectedFile.size) + estimateAnalysisSeconds(durationSec);
  }, [durationSec, selectedFile]);

  const elapsedSeconds = useMemo(() => {
    if (!jobStatus?.started_at) {
      return null;
    }
    const startedAt = Date.parse(jobStatus.started_at);
    if (Number.isNaN(startedAt)) {
      return null;
    }
    return Math.max(0, Math.round((Date.now() - startedAt) / 1000));
  }, [jobStatus]);

  const isLocked = isSubmitting || Boolean(activeJobId);

  async function selectFile(file: File) {
    setSelectionError(null);
    setRuntimeError(null);
    const validationError = validateAudioFile(file);
    if (validationError) {
      setSelectedFile(null);
      setDurationSec(null);
      setSelectionError(validationError);
      return;
    }

    setSelectedFile(file);
    setDurationSec(null);
    setIsInspecting(true);
    try {
      setDurationSec(await detectAudioDuration(file));
    } finally {
      setIsInspecting(false);
    }
  }

  async function handleAnalyze() {
    if (!selectedFile || isLocked) {
      return;
    }

    setRuntimeError(null);
    setIsSubmitting(true);
    setJobStatus(null);

    try {
      const createResponse = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysis_mode: "full",
          metadata: {
            source_type: "direct_audio_file",
            title: fileTitle(selectedFile.name)
          }
        })
      });
      if (!createResponse.ok) {
        throw new Error("Could not create an analysis session.");
      }
      const created = (await createResponse.json()) as { job_id: string; updated_at: string };
      const jobId = created.job_id;

      setJobStatus({
        job_id: jobId,
        status: "created",
        stage_key: null,
        stage_label: "Preparing session",
        stage_index: 0,
        stage_count: CLIENT_STAGE_COUNT,
        percent_complete: 0,
        message: "Preparing your audio for upload",
        eta_seconds: preflightEstimate ?? 0,
        started_at: null,
        updated_at: created.updated_at,
        error: null,
        history: []
      });

      const uploadForm = new FormData();
      uploadForm.append("file", selectedFile);
      const uploadResponse = await fetch(`/api/sessions/${jobId}/upload`, {
        method: "POST",
        body: uploadForm
      });
      if (!uploadResponse.ok) {
        throw new Error("Could not upload the selected audio.");
      }

      setJobStatus({
        job_id: jobId,
        status: "uploaded",
        stage_key: "upload",
        stage_label: "Uploading audio",
        stage_index: 1,
        stage_count: CLIENT_STAGE_COUNT,
        percent_complete: 10,
        message: "Upload complete. Queueing the analysis pipeline.",
        eta_seconds: preflightEstimate ?? 0,
        started_at: null,
        updated_at: new Date().toISOString(),
        error: null,
        history: []
      });

      const processResponse = await fetch(`/api/sessions/${jobId}/process-async`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          metadata: {
            source_type: "direct_audio_file",
            title: fileTitle(selectedFile.name),
            duration_hint_sec: durationSec
          }
        })
      });
      if (!processResponse.ok) {
        throw new Error("Could not start the analysis job.");
      }

      const initialStatus = (await processResponse.json()) as SessionJobStatus;
      window.localStorage.setItem(ACTIVE_JOB_KEY, jobId);
      setActiveJobId(jobId);
      setJobStatus(initialStatus);
    } catch (error) {
      setRuntimeError(error instanceof Error ? error.message : "Analysis could not be started.");
      setIsSubmitting(false);
    }
  }

  const activityItems = jobStatus?.history ?? [];

  return (
    <section className="analysis-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow muted">Analyze Audio</span>
          <h2>Drag in any call clip, run analysis, and jump straight to the full evidence dashboard.</h2>
        </div>
        <span className="microcopy">Accepted formats: WAV, MP3, M4A · Max upload size: 512 MB · One active run per browser tab</span>
      </div>

      <div className="analysis-layout">
        <div
          className={`dropzone ${dragActive ? "active" : ""} ${isLocked ? "locked" : ""}`}
          onDragEnter={(event) => {
            event.preventDefault();
            if (!isLocked) setDragActive(true);
          }}
          onDragOver={(event) => {
            event.preventDefault();
            if (!isLocked) setDragActive(true);
          }}
          onDragLeave={(event) => {
            event.preventDefault();
            if (event.currentTarget.contains(event.relatedTarget as Node | null)) {
              return;
            }
            setDragActive(false);
          }}
          onDrop={(event) => {
            event.preventDefault();
            setDragActive(false);
            if (isLocked) return;
            const file = event.dataTransfer.files?.[0];
            if (file) {
              void selectFile(file);
            }
          }}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".wav,.mp3,.m4a,audio/wav,audio/mpeg,audio/mp4"
            hidden
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                void selectFile(file);
              }
            }}
          />

          <div className="dropzone-copy">
            <span className="eyebrow muted">{isLocked ? "Analysis in progress" : "Drop audio here"}</span>
            <h3>{selectedFile ? selectedFile.name : "Drop a file or browse for one"}</h3>
            <p>
              {isLocked
                ? "The panel stays locked while the current analysis is running so progress and results stay attached to one active session."
                : "Use drag and drop for a quick run, or browse to pick any WAV, MP3, or M4A file from your machine."}
            </p>
          </div>

          <div className="dropzone-actions">
            <button type="button" className="primary-link button-link" disabled={isLocked} onClick={() => inputRef.current?.click()}>
              {selectedFile ? "Choose another file" : "Browse audio"}
            </button>
            {selectedFile ? (
              <button type="button" className="secondary-link" disabled={isLocked} onClick={handleAnalyze}>
                Analyze audio
              </button>
            ) : null}
          </div>

          {selectionError ? <p className="inline-error">{selectionError}</p> : null}
          {runtimeError ? <p className="inline-error">{runtimeError}</p> : null}
        </div>

        <aside className="analysis-rail">
          <article className="analysis-card">
            <span className="sample-meta">Preflight</span>
            {selectedFile ? (
              <div className="preflight-grid">
                <div>
                  <span className="row-label">File</span>
                  <strong>{selectedFile.name}</strong>
                </div>
                <div>
                  <span className="row-label">Size</span>
                  <strong>{formatBytes(selectedFile.size)}</strong>
                </div>
                <div>
                  <span className="row-label">Duration</span>
                  <strong>{isInspecting ? "reading" : formatSeconds(durationSec)}</strong>
                </div>
                <div>
                  <span className="row-label">Estimated total</span>
                  <strong>{formatSeconds(preflightEstimate)}</strong>
                </div>
              </div>
            ) : (
              <p className="microcopy">Pick a file to see the estimated analysis time before you start.</p>
            )}
            <p className="microcopy">
              OpenAI-backed diarized transcription and human-vs-AI role analysis run automatically when a local <code>OPENAI_API_KEY</code> is configured. Otherwise the upload falls back to the local heuristic pipeline.
            </p>
          </article>

          <article className="analysis-card">
            <span className="sample-meta">Live progress</span>
            {jobStatus ? (
              <div className="progress-stack">
                <div className="progress-head">
                  <div>
                    <strong>{jobStatus.stage_label ?? "Waiting"}</strong>
                    <p>{jobStatus.message}</p>
                  </div>
                  <span className={`badge ${jobStatus.status === "failed" ? "warn" : jobStatus.status === "completed" ? "ok" : "accent"}`}>
                    {jobStatus.status}
                  </span>
                </div>

                <div className="progress-track" aria-hidden="true">
                  <div className="progress-fill" style={{ width: `${jobStatus.percent_complete}%` }} />
                </div>

                <div className="progress-meta">
                  <div>
                    <span className="row-label">Progress</span>
                    <strong>{jobStatus.percent_complete}%</strong>
                  </div>
                  <div>
                    <span className="row-label">Elapsed</span>
                    <strong>{formatSeconds(elapsedSeconds)}</strong>
                  </div>
                  <div>
                    <span className="row-label">Remaining</span>
                    <strong>{formatSeconds(jobStatus.eta_seconds)}</strong>
                  </div>
                </div>

                <div className="activity-log">
                  {activityItems.map((entry) => (
                    <div className="activity-row" key={`${entry.stage_key}-${entry.completed_at}`}>
                      <span className="activity-label">{entry.stage_label}</span>
                      <span className="microcopy">{entry.message}</span>
                    </div>
                  ))}
                  <div className="activity-row current">
                    <span className="activity-label">{jobStatus.stage_label ?? "Waiting for analysis"}</span>
                    <span className="microcopy">{jobStatus.message}</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="microcopy">Continuous progress appears here once the analysis job begins.</p>
            )}
          </article>
        </aside>
      </div>
    </section>
  );
}
