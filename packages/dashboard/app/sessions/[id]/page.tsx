import Link from "next/link";
import { notFound } from "next/navigation";

import { fetchSessionBundle } from "../../../lib/api-client";
import { audioPathFor, formatMetric, formatPct, spectrogramPathFor } from "../../../lib/data";
import { SessionWorkspace } from "../../components/session-workspace";

export const dynamic = "force-dynamic";

function topMoments(bundle: NonNullable<Awaited<ReturnType<typeof fetchSessionBundle>>>) {
  if (bundle.questions.length) {
    return bundle.questions.slice(0, 3).map((question) => ({
      label: question.question_text,
      detail: `${Math.round(question.response_latency_ms)} ms response latency · hesitation ${Math.round(question.hesitation_score)}`,
    }));
  }
  if (bundle.events.length) {
    return bundle.events.slice(0, 3).map((event) => ({
      label: event.label ?? event.type.replaceAll("_", " "),
      detail: `${Math.round(event.begin_ms)} ms to ${Math.round(event.end_ms)} ms · ${event.severity}`,
    }));
  }
  return [
    {
      label: "Transcript-first review",
      detail: "This session has no mapped question moments yet, so transcript, cues, and quality posture stay primary.",
    },
  ];
}

function topTakeaways(bundle: NonNullable<Awaited<ReturnType<typeof fetchSessionBundle>>>) {
  const takeaways = bundle.signals.slice(0, 3).map((signal) => ({
    label: signal.label,
    detail: `${signal.score}/100 · ${signal.evidence_class?.replaceAll("_", " ") ?? "heuristic backed"}`,
    summary: signal.summary,
  }));
  if (takeaways.length) {
    return takeaways;
  }
  return [
    {
      label: "Signals still forming",
      detail: "No headline signals are available yet.",
      summary: "The session bundle still exposes transcript, readiness, timing, and quality posture for review.",
    },
  ];
}

export default async function SessionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const bundle = await fetchSessionBundle(id);
  if (!bundle) {
    notFound();
  }

  const visibleProfileCount = bundle.profile_display.filter((field) => field.display_state === "visible" || field.display_state === "muted").length;
  const caveats = Array.from(new Set([...bundle.quality.warning_flags, ...(bundle.diagnostics.confidence_caveats ?? []), ...(bundle.diagnostics.degraded_reasons ?? [])])).slice(0, 6);

  return (
    <main className="analytics-shell detail-shell">
      <Link href="/" className="eyebrow">
        Back to workspace
      </Link>

      <section className="analytics-hero detail-hero">
        <div className="hero-copy">
          <span className="eyebrow">{bundle.session.analysis_mode}</span>
          <h1>{bundle.session.title}</h1>
          <p>
            {bundle.session.dataset_id ?? "ad hoc"} · {bundle.session.language ?? "unknown"} · {bundle.session.region ?? "region unknown"} ·{" "}
            {bundle.session.duration_sec.toFixed(1)} seconds
          </p>
          <div className="badge-row">
            <span className={`badge ${bundle.quality.is_usable ? "ok" : "warn"}`}>{bundle.quality.is_usable ? "usable" : "needs review"}</span>
            <span className="badge">{bundle.environment.primary}</span>
            <span className="badge accent">{bundle.session.readiness_tier ?? "blocked"}</span>
            <span className="badge accent">{bundle.content.view_summary.highlighted_sentence_count} emotion spans</span>
          </div>
        </div>

        <div className="hero-rail">
          <article className="hero-meter">
            <span className="sample-meta">Speech ratio</span>
            <strong>{formatPct(bundle.quality.speech_ratio)}</strong>
            <span className="microcopy">noise ratio {bundle.quality.noise_ratio.toFixed(2)}</span>
          </article>
          <article className="hero-meter">
            <span className="sample-meta">Average SNR</span>
            <strong>{formatMetric(bundle.quality.avg_snr_db, "dB")}</strong>
            <span className="microcopy">{bundle.quality.warning_flags.join(", ") || "No active quality warning"}</span>
          </article>
          <article className="hero-meter">
            <span className="sample-meta">Transcript affect</span>
            <strong>{bundle.content.view_summary.highlighted_sentence_count}</strong>
            <span className="microcopy">{bundle.content.view_summary.token_overlay_count} word overlays</span>
          </article>
          <article className="hero-meter">
            <span className="sample-meta">Profile coverage</span>
            <strong>{visibleProfileCount}</strong>
            <span className="microcopy">confidence-gated fields visible now</span>
          </article>
        </div>
      </section>

      <section className="panel panel-spacious">
        <div className="section-heading">
          <div>
            <span className="eyebrow muted">Summary</span>
            <h2>What happened, what matters, and how much to trust it</h2>
          </div>
          <span className="microcopy">This page stays session-first: the important takeaways come before the deep analytics workspace.</span>
        </div>
        <div className="analytics-grid">
          <div className="analytics-main">
            <section className="panel panel-spacious">
              <span className="eyebrow muted">Top takeaways</span>
              <div className="stack compact" style={{ marginTop: 12 }}>
                {topTakeaways(bundle).map((takeaway) => (
                  <div className="info-row" key={takeaway.label}>
                    <strong>{takeaway.label}</strong>
                    <span className="microcopy">{takeaway.detail}</span>
                    <span className="microcopy">{takeaway.summary}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="panel panel-spacious">
              <span className="eyebrow muted">Top moments</span>
              <div className="stack compact" style={{ marginTop: 12 }}>
                {topMoments(bundle).map((moment) => (
                  <div className="info-row" key={moment.label}>
                    <strong>{moment.label}</strong>
                    <span className="microcopy">{moment.detail}</span>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <aside className="analytics-side">
            <section className="panel panel-spacious">
              <span className="eyebrow muted">Trust and coverage</span>
              <div className="stack compact" style={{ marginTop: 12 }}>
                <div className="info-row">
                  <strong>Readiness tier</strong>
                  <span className="microcopy">{bundle.session.readiness_tier ?? "blocked"}</span>
                </div>
                <div className="info-row">
                  <strong>Speaker timing</strong>
                  <span className="microcopy">{bundle.diarization.readiness_state}</span>
                </div>
                <div className="info-row">
                  <strong>Profile coverage</strong>
                  <span className="microcopy">
                    {bundle.profile_coverage.model_backed_fields.length} model-backed · {bundle.profile_coverage.hidden_fields.length} hidden
                  </span>
                </div>
                <div className="info-row">
                  <strong>Signal evidence</strong>
                  <span className="microcopy">
                    {bundle.signals.filter((signal) => signal.evidence_class === "benchmark_backed").length} benchmark-backed of {bundle.signals.length}
                  </span>
                </div>
              </div>
            </section>

            <section className="panel panel-spacious">
              <span className="eyebrow muted">Main caveats</span>
              <div className="badge-row" style={{ marginTop: 12 }}>
                {caveats.length ? (
                  caveats.map((caveat) => (
                    <span className="badge warn" key={caveat}>
                      {caveat}
                    </span>
                  ))
                ) : (
                  <span className="microcopy">No active degraded-mode caveats for this session.</span>
                )}
              </div>
            </section>
          </aside>
        </div>
      </section>

      <SessionWorkspace audioSrc={audioPathFor(id)} bundle={bundle} jobId={id} spectrogramSrc={spectrogramPathFor(id)} />
    </main>
  );
}
