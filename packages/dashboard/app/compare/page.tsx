import Link from "next/link";

import { compareSessionBundles, formatMetric, loadSessionBundles } from "../../lib/data";

export default async function ComparePage({
  searchParams
}: {
  searchParams: Promise<{ ids?: string }>;
}) {
  const params = await searchParams;
  const fallbackBundles = loadSessionBundles().slice(0, 2);
  const bundles = params.ids ? compareSessionBundles(params.ids.split(",").filter(Boolean)) : fallbackBundles;

  return (
    <main className="analytics-shell compare-shell">
      <Link href="/" className="eyebrow">
        Back to workspace
      </Link>

      <section className="analytics-hero detail-hero">
        <div className="hero-copy">
          <span className="eyebrow">Compare</span>
          <h1>Quality, hesitation, overlap, and friction side by side.</h1>
          <p>Use this view to inspect how two sessions diverge across quality gates, question behavior, and proxy signal cards.</p>
        </div>
      </section>

      <section className="panel panel-spacious">
        <div className="compare-grid">
          {bundles.length ? (
            bundles.map((bundle) => (
              <article className="compare-card" key={bundle.session.session_id}>
                <div className="badge-row">
                  <span className={`badge ${bundle.quality.is_usable ? "ok" : "warn"}`}>{bundle.quality.is_usable ? "usable" : "review"}</span>
                  <span className="badge">{bundle.session.analysis_mode}</span>
                </div>
                <h2>{bundle.session.title}</h2>
                <p className="sample-meta">
                  {bundle.session.dataset_id ?? "ad hoc"} · {bundle.session.language ?? "unknown"} · {bundle.session.duration_sec.toFixed(1)} sec
                </p>

                <div className="metric-stack">
                  <div className="metric-row">
                    <span className="row-label">Average SNR</span>
                    <strong>{formatMetric(bundle.quality.avg_snr_db, "dB")}</strong>
                  </div>
                  <div className="metric-row">
                    <span className="row-label">Noise ratio</span>
                    <strong>{formatMetric(bundle.quality.noise_ratio, "ratio")}</strong>
                  </div>
                  <div className="metric-row">
                    <span className="row-label">Questions</span>
                    <strong>{bundle.questions.length}</strong>
                  </div>
                  <div className="metric-row">
                    <span className="row-label">Interruptions</span>
                    <strong>{bundle.events.filter((event) => event.type === "interruption").length}</strong>
                  </div>
                </div>

                <div className="signal-list">
                  {bundle.signals.map((signal) => (
                    <div className="signal-row" key={signal.key}>
                      <span className="row-label">{signal.label}</span>
                      <strong>{signal.score}</strong>
                    </div>
                  ))}
                </div>

                <Link href={`/sessions/${bundle.session.session_id}`} className="primary-link inline">
                  Open session detail
                </Link>
              </article>
            ))
          ) : (
            <div className="empty-state">No comparable sessions yet. Import or bootstrap a few runs first.</div>
          )}
        </div>
      </section>
    </main>
  );
}
