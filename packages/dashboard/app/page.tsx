import Link from "next/link";

import { formatMetric, formatPct, loadDashboardSnapshot } from "../lib/data";
import { AnalyzeAudioPanel } from "./components/analyze-audio-panel";

function stageCoverageLabel(readyCount: number, total: number) {
  if (!total) return "No imported sessions";
  return `${readyCount}/${total} sessions`;
}

export default function HomePage() {
  const snapshot = loadDashboardSnapshot();
  const { bundles, datasets, totals, cohorts, benchmarks } = snapshot;
  const defaultCompareIds = bundles.slice(0, 2).map((bundle) => bundle.session.session_id).join(",");
  const cleanRuns = bundles.filter((bundle) => bundle.quality.noise_ratio < 0.2).length;
  const watchRuns = bundles.filter((bundle) => bundle.quality.noise_ratio >= 0.2 && bundle.quality.noise_ratio < 0.35).length;
  const riskyRuns = bundles.filter((bundle) => bundle.quality.noise_ratio >= 0.35).length;

  return (
    <main className="analytics-shell">
      <section className="analytics-hero">
        <div className="hero-copy">
          <span className="eyebrow">Spectrum Analytics Workspace</span>
          <h1>Google Analytics for audio sessions, grounded in turns, quality, and behavioral evidence.</h1>
          <p>
            Every imported call lands in one normalized bundle: audio artifacts, quality gates, structure, transcript context,
            question analytics, and signal cards with explainability masks.
          </p>
          <div className="hero-actions">
            <Link href={defaultCompareIds ? `/compare?ids=${defaultCompareIds}` : "/compare"} className="primary-link">
              Open Compare
            </Link>
            <span className="microcopy">Import demo-pack or dataset samples through the API, then review them here without rerunning analysis.</span>
          </div>
        </div>

        <div className="hero-rail">
          <article className="hero-meter">
            <span className="sample-meta">Total runs</span>
            <strong>{totals.runs}</strong>
            <span className="microcopy">Synthetic + downloaded sessions in one workspace</span>
          </article>
          <article className="hero-meter">
            <span className="sample-meta">Usable runs</span>
            <strong>{totals.usableRuns}</strong>
            <span className="microcopy">Quality gate passing now</span>
          </article>
          <article className="hero-meter">
            <span className="sample-meta">Datasets</span>
            <strong>{totals.datasetCount}</strong>
            <span className="microcopy">Manifest coverage + import health</span>
          </article>
          <article className="hero-meter">
            <span className="sample-meta">Average SNR</span>
            <strong>{totals.avgSNR.toFixed(1)} dB</strong>
            <span className="microcopy">Waveform-estimated baseline across imported runs</span>
          </article>
        </div>
      </section>

      <AnalyzeAudioPanel />

      <section className="panel panel-spacious">
        <div className="section-heading">
          <div>
            <span className="eyebrow muted">Cohort Dashboard</span>
            <h2>Product-ops baseline across saved bundles</h2>
          </div>
          <span className="microcopy">Default filters: all dates, all sources, all languages, all readiness tiers.</span>
        </div>
        <div className="badge-row">
          <span className="badge accent">All date windows</span>
          <span className="badge">All source types</span>
          <span className="badge">All analysis modes</span>
          <span className="badge">All languages</span>
          <span className="badge">All duration bands</span>
          <span className="badge">All quality bands</span>
        </div>
        <div className="ribbon-grid" style={{ marginTop: 18 }}>
          {cohorts.kpis.map((kpi) => (
            <article className="ribbon-card" key={kpi.key}>
              <span className="sample-meta">{kpi.label}</span>
              <strong>{formatMetric(kpi.value, kpi.unit)}</strong>
            </article>
          ))}
        </div>
      </section>

      <section className="ribbon-grid">
        <article className="ribbon-card">
          <span className="sample-meta">Quality distribution</span>
          <div className="quality-bars">
            <div>
              <strong>{cleanRuns}</strong>
              <span className="microcopy">clean</span>
            </div>
            <div>
              <strong>{watchRuns}</strong>
              <span className="microcopy">watch</span>
            </div>
            <div>
              <strong>{riskyRuns}</strong>
              <span className="microcopy">risky</span>
            </div>
          </div>
        </article>
        <article className="ribbon-card">
          <span className="sample-meta">Source mix</span>
          <strong>{bundles.filter((bundle) => bundle.session.source_type === "materialized_audio_dataset").length} downloaded sessions</strong>
          <span className="microcopy">{bundles.filter((bundle) => bundle.session.source_type === "demo_pack_zip").length} demo-pack narratives</span>
        </article>
        <article className="ribbon-card">
          <span className="sample-meta">Behavioral moments</span>
          <strong>{bundles.reduce((sum, bundle) => sum + bundle.questions.length, 0)} questions mapped</strong>
          <span className="microcopy">{bundles.reduce((sum, bundle) => sum + bundle.events.length, 0)} events attached to the timeline</span>
        </article>
        <article className="ribbon-card">
          <span className="sample-meta">Adapter posture</span>
          <strong>Hybrid optional stack</strong>
          <span className="microcopy">FFmpeg-first, optional ASR / diarization / environment enrichments</span>
        </article>
      </section>

      <section className="analytics-grid">
        <div className="analytics-main">
          <section className="panel panel-spacious">
            <div className="section-heading">
              <div>
                <span className="eyebrow muted">Overview</span>
                <h2>Cohort trendline</h2>
              </div>
              <span className="microcopy">Daily bundle rollups keep human hesitation, friction, rapport, and frustration in one scan line.</span>
            </div>
            <div className="table-shell">
              <table className="analytics-table">
                <thead>
                  <tr>
                    <th>Bucket</th>
                    <th>Runs</th>
                    <th>Usable</th>
                    <th>Avg SNR</th>
                    <th>Hesitation</th>
                    <th>Friction</th>
                    <th>Rapport</th>
                    <th>Frustration</th>
                  </tr>
                </thead>
                <tbody>
                  {cohorts.trends.length ? (
                    cohorts.trends.map((trend) => (
                      <tr key={trend.bucket}>
                        <td><strong>{trend.bucket}</strong></td>
                        <td>{trend.run_count}</td>
                        <td>{formatMetric(trend.usable_run_rate, "%")}</td>
                        <td>{formatMetric(trend.avg_snr_db, "dB")}</td>
                        <td>{Math.round(trend.hesitation_avg)}</td>
                        <td>{Math.round(trend.friction_avg)}</td>
                        <td>{Math.round(trend.rapport_avg)}</td>
                        <td>{Math.round(trend.frustration_avg)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={8}><div className="empty-state">Import or bootstrap a few sessions to populate cohort trends.</div></td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel panel-spacious">
            <div className="section-heading">
              <div>
                <span className="eyebrow muted">Distributions</span>
                <h2>Cohort mixes and long-call drift</h2>
              </div>
              <span className="microcopy">Quality bands, source mix, duration mix, dominant human emotions, and first/middle/final third summaries.</span>
            </div>
            <div className="alert-grid">
              {cohorts.distributions.map((distribution) => (
                <article className="alert-card" key={distribution.key}>
                  <span className="badge accent">{distribution.label}</span>
                  <div className="badge-row">
                    {distribution.items.slice(0, 6).map((item) => (
                      <span className="badge" key={`${distribution.key}-${item.key}`}>
                        {item.label} {item.value}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
            <div className="table-shell" style={{ marginTop: 18 }}>
              <table className="analytics-table">
                <thead>
                  <tr>
                    <th>Phase</th>
                    <th>Hesitation</th>
                    <th>Friction</th>
                    <th>Rapport</th>
                    <th>Frustration</th>
                    <th>Dominant emotion</th>
                  </tr>
                </thead>
                <tbody>
                  {cohorts.phase_summaries.map((phase) => (
                    <tr key={phase.phase}>
                      <td><strong>{phase.phase.replaceAll("_", " ")}</strong></td>
                      <td>{Math.round(phase.hesitation_avg)}</td>
                      <td>{Math.round(phase.friction_avg)}</td>
                      <td>{Math.round(phase.rapport_avg)}</td>
                      <td>{Math.round(phase.frustration_avg)}</td>
                      <td>{phase.dominant_emotion}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel panel-spacious">
            <div className="section-heading">
              <div>
                <span className="eyebrow muted">Acquisition</span>
                <h2>Dataset health and ingestion readiness</h2>
              </div>
              <span className="microcopy">Shows what is downloaded, what is blocked, and how much of each dataset is already imported.</span>
            </div>
            <div className="table-shell">
              <table className="analytics-table">
                <thead>
                  <tr>
                    <th>Dataset</th>
                    <th>Status</th>
                    <th>Languages</th>
                    <th>Imported</th>
                    <th>Stage coverage</th>
                  </tr>
                </thead>
                <tbody>
                  {datasets.map((dataset) => {
                    const readyStageCount = Object.values(dataset.stage_completeness).reduce((sum, value) => sum + value, 0);
                    return (
                      <tr key={dataset.dataset_id}>
                        <td>
                          <strong>{dataset.title}</strong>
                          <div className="microcopy">{dataset.dataset_id}</div>
                        </td>
                        <td>
                          <span className={`badge ${dataset.health_status === "ready" ? "ok" : "warn"}`}>{dataset.health_status}</span>
                          {dataset.health_detail ? <div className="microcopy">{dataset.health_detail}</div> : null}
                        </td>
                        <td>{dataset.language_labels.length ? dataset.language_labels.join(", ") : "Unknown"}</td>
                        <td>
                          <strong>{dataset.imported_count}</strong>
                          <div className="microcopy">of {dataset.sample_count} available samples</div>
                        </td>
                        <td>{stageCoverageLabel(readyStageCount, dataset.imported_count || dataset.sample_count)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel panel-spacious">
            <div className="section-heading">
              <div>
                <span className="eyebrow muted">Sessions</span>
                <h2>Explorer</h2>
              </div>
              <span className="microcopy">Session cards bias toward operational scanability instead of landing-page copy.</span>
            </div>
            <div className="session-grid">
              {bundles.map((bundle) => (
                <Link href={`/sessions/${bundle.session.session_id}`} className="session-card" key={bundle.session.session_id}>
                  <div className="badge-row">
                    <span className={`badge ${bundle.quality.is_usable ? "ok" : "warn"}`}>{bundle.quality.is_usable ? "usable" : "review"}</span>
                    <span className="badge">{bundle.session.analysis_mode}</span>
                    <span className="badge accent">{bundle.session.source_type}</span>
                  </div>
                  <h3>{bundle.session.title}</h3>
                  <p className="sample-meta">
                    {bundle.session.dataset_id ?? "ad hoc"} · {bundle.session.language ?? "unknown"} · {bundle.session.duration_sec.toFixed(1)} sec
                  </p>
                  <div className="session-card-metrics">
                    <div>
                      <span className="row-label">Quality</span>
                      <strong>{formatMetric(bundle.quality.avg_snr_db, "dB")}</strong>
                    </div>
                    <div>
                      <span className="row-label">Noise ratio</span>
                      <strong>{formatMetric(bundle.quality.noise_ratio, "ratio")}</strong>
                    </div>
                    <div>
                      <span className="row-label">Questions</span>
                      <strong>{bundle.questions.length}</strong>
                    </div>
                    <div>
                      <span className="row-label">Top signal</span>
                      <strong>{bundle.signals[0]?.label ?? "Pending"}</strong>
                    </div>
                  </div>
                  <div className="badge-row">
                    {bundle.signals.slice(0, 3).map((signal) => (
                      <span key={signal.key} className={`badge ${signal.status === "risk" ? "warn" : signal.status === "healthy" ? "ok" : ""}`}>
                        {signal.label} {signal.score}
                      </span>
                    ))}
                  </div>
                </Link>
              ))}
            </div>
          </section>
        </div>

        <aside className="analytics-side">
          <section className="panel panel-spacious">
            <span className="eyebrow muted">Quality</span>
            <h2>Interpretation rules</h2>
            <div className="stack compact">
              <div className="info-row">
                <strong>Low SNR guard</strong>
                <span className="microcopy">Prosody-heavy signals are downweighted once average SNR falls below 10 dB.</span>
              </div>
              <div className="info-row">
                <strong>Noisy answer starts</strong>
                <span className="microcopy">Noise spikes and low-SNR windows discount hesitation instead of overcalling emotional hesitation.</span>
              </div>
              <div className="info-row">
                <strong>VAD explainability</strong>
                <span className="microcopy">False positives and negatives stay visible as events, not hidden inside summary scores.</span>
              </div>
            </div>
          </section>

          <section className="panel panel-spacious">
            <span className="eyebrow muted">Signals</span>
            <h2>Current workspace mix</h2>
            <div className="signal-list">
              {["hesitation", "friction", "rapport", "frustration_risk"].map((key) => {
                const values = bundles.flatMap((bundle) => bundle.signals.filter((signal) => signal.key === key).map((signal) => signal.score));
                const average = values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
                return (
                  <div className="signal-row" key={key}>
                    <span className="row-label">{key.replaceAll("_", " ")}</span>
                    <strong>{average.toFixed(0)}</strong>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="panel panel-spacious">
            <span className="eyebrow muted">Compare</span>
            <h2>Side-by-side drilldown</h2>
            <p className="microcopy" style={{ marginTop: 10 }}>
              Compare two sessions or cohorts by quality, hesitation, overlap, engagement drift, and friction.
            </p>
            <Link href={defaultCompareIds ? `/compare?ids=${defaultCompareIds}` : "/compare"} className="primary-link inline">
              Launch compare view
            </Link>
          </section>

          <section className="panel panel-spacious">
            <span className="eyebrow muted">Behavior</span>
            <h2>Topic coverage</h2>
            <div className="badge-row">
              {Array.from(new Set(bundles.flatMap((bundle) => bundle.content.topic_labels))).slice(0, 12).map((topic) => (
                <span className="badge" key={topic}>
                  {topic}
                </span>
              ))}
            </div>
          </section>

          <section className="panel panel-spacious">
            <span className="eyebrow muted">Audience</span>
            <h2>Language mix</h2>
            <div className="stack compact">
              {bundles.slice(0, 5).map((bundle) => (
                <div className="info-row" key={bundle.session.session_id}>
                  <strong>{bundle.session.title}</strong>
                  <span className="microcopy">
                    {bundle.profile.lang_mix.label} · speech {formatPct(bundle.quality.speech_ratio)} · {bundle.session.speaker_count} speakers
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section className="panel panel-spacious">
            <span className="eyebrow muted">Benchmarks</span>
            <h2>Capability and quality coverage</h2>
            <div className="table-shell">
              <table className="analytics-table">
                <thead>
                  <tr>
                    <th>Dataset</th>
                    <th>Status</th>
                    <th>Tasks</th>
                    <th>Current metric snapshot</th>
                  </tr>
                </thead>
                <tbody>
                  {benchmarks.registry.map((entry) => {
                    const matching = benchmarks.results.filter((result) => result.dataset_id === entry.dataset_id);
                    return (
                      <tr key={entry.benchmark_id}>
                        <td>
                          <strong>{entry.title}</strong>
                          <div className="microcopy">{entry.dataset_id}</div>
                        </td>
                        <td><span className={`badge ${entry.status === "ready" ? "ok" : "warn"}`}>{entry.status}</span></td>
                        <td>{entry.tasks.map((task) => task.label).join(", ")}</td>
                        <td>
                          <div className="badge-row">
                            {matching.slice(0, 3).map((result) => (
                              <span className="badge" key={result.benchmark_id}>
                                {result.task_type}: {result.metrics[0] ? formatMetric(result.metrics[0].value) : result.status}
                              </span>
                            ))}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
