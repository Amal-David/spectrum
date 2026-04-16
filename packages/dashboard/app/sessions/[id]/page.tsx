import Link from "next/link";
import { notFound } from "next/navigation";

import { audioPathFor, formatMetric, formatPct, loadSessionBundle, spectrogramPathFor } from "../../../lib/data";
import { SessionWorkspace } from "../../components/session-workspace";

export default async function SessionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const bundle = loadSessionBundle(id);
  if (!bundle) {
    notFound();
  }

  const visibleProfileCount = bundle.profile_display.filter((field) => field.display_state === "visible" || field.display_state === "muted").length;

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
            <span className="badge accent">{bundle.content.view_summary.highlighted_sentence_count} emotion spans</span>
            {bundle.environment.tags.slice(0, 2).map((tag) => (
              <span className="badge accent" key={tag}>
                {tag}
              </span>
            ))}
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

      <SessionWorkspace audioSrc={audioPathFor(id)} bundle={bundle} jobId={id} spectrogramSrc={spectrogramPathFor(id)} />
    </main>
  );
}
