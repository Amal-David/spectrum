import Link from "next/link";

import { fetchDatasets, fetchSessionIndex } from "../lib/api-client";
import { loadBenchmarkSnapshot } from "../lib/benchmark-client";
import { loadCohortDistributions, loadCohortSessions, loadCohortSummary, loadCohortTrends } from "../lib/cohort-client";
import { formatMetric, type DashboardFilters } from "../lib/data";
import { AnalyzeAudioPanel } from "./components/analyze-audio-panel";

export const dynamic = "force-dynamic";

function singleParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function stageCoverageLabel(readyCount: number, total: number) {
  if (!total) return "No imported sessions";
  return `${readyCount}/${total} sessions`;
}

function kpiValue(kpis: Array<{ key: string; label: string; value: number; unit?: string | null }>, key: string) {
  return kpis.find((kpi) => kpi.key === key);
}

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export default async function HomePage({ searchParams }: PageProps) {
  const resolvedSearchParams = (await searchParams) ?? {};
  const filters: DashboardFilters = {
    sourceType: singleParam(resolvedSearchParams.source_type) ?? "all",
    analysisMode: singleParam(resolvedSearchParams.analysis_mode) ?? "all",
    language: singleParam(resolvedSearchParams.language) ?? "all",
    durationBand: singleParam(resolvedSearchParams.duration_band) ?? "all",
    qualityBand: singleParam(resolvedSearchParams.quality_band) ?? "all",
    readinessTier: singleParam(resolvedSearchParams.readiness_tier) ?? "all",
    rolePresence: singleParam(resolvedSearchParams.role_presence) ?? "all",
  };

  let apiError: string | null = null;
  let sessionIndex = [] as Awaited<ReturnType<typeof fetchSessionIndex>>;
  let datasets = [] as Awaited<ReturnType<typeof fetchDatasets>>;
  let cohortSummary = { kpis: [], phase_summaries: [], dominant_emotions: [], runs: [] } as Awaited<ReturnType<typeof loadCohortSummary>>;
  let cohortTrends = [] as Awaited<ReturnType<typeof loadCohortTrends>>;
  let cohortDistributions = [] as Awaited<ReturnType<typeof loadCohortDistributions>>;
  let benchmarks = { registry: [], results: [] } as Awaited<ReturnType<typeof loadBenchmarkSnapshot>>;

  try {
    [sessionIndex, datasets, cohortSummary, cohortTrends, cohortDistributions, benchmarks] = await Promise.all([
      fetchSessionIndex(),
      fetchDatasets(),
      loadCohortSummary(filters),
      loadCohortTrends(filters),
      loadCohortDistributions(filters),
      loadBenchmarkSnapshot(),
    ]);
  } catch {
    apiError = "The dashboard could not reach the Spectrum API. Start it with `make dev` or `pnpm api:dev` to load live sessions.";
  }

  const recentRuns = cohortSummary.runs.slice(0, 6);
  const sessionIndexById = new Map(sessionIndex.map((row) => [row.session_id, row]));
  const sourceOptions = Array.from(new Set(sessionIndex.map((bundle) => bundle.source_type))).sort();
  const languageOptions = Array.from(new Set(sessionIndex.map((bundle) => bundle.language ?? "unknown"))).sort();
  const analysisOptions = Array.from(new Set(sessionIndex.map((bundle) => bundle.analysis_mode))).sort();
  const defaultCompareIds = recentRuns.slice(0, 2).map((run) => run.session_id).join(",");
  const runCount = kpiValue(cohortSummary.kpis, "run_count");
  const usableRunRate = kpiValue(cohortSummary.kpis, "usable_run_rate");
  const averageSnr = kpiValue(cohortSummary.kpis, "avg_snr_db");
  const topReadiness = cohortDistributions.find((distribution) => distribution.key === "readiness_mix")?.items[0];

  return (
    <main className="analytics-shell">
      <section className="analytics-hero">
        <div className="hero-copy">
          <span className="eyebrow">Spectrum</span>
          <h1>Turn one human-AI voice call into a comprehensive conversation report.</h1>
          <p>
            Spectrum starts with the report: what happened, where the agent experience broke, what evidence supports each claim, and
            what to inspect next. Bundles, cohorts, and benchmarks are the infrastructure underneath.
          </p>
          <div className="hero-actions">
            <Link href={recentRuns[0] ? `/sessions/${recentRuns[0].session_id}` : "#quickstart"} className="primary-link">
              Open latest session
            </Link>
            <Link href={defaultCompareIds ? `/compare?ids=${defaultCompareIds}` : "/compare"} className="filter-toggle active">
              Compare two runs
            </Link>
          </div>
        </div>

        <div className="hero-rail">
          <article className="hero-meter">
            <span className="sample-meta">Runs in workspace</span>
            <strong>{runCount ? formatMetric(runCount.value) : "0"}</strong>
            <span className="microcopy">Every run becomes one diagnostic report plus one durable bundle.</span>
          </article>
          <article className="hero-meter">
            <span className="sample-meta">Usable-run rate</span>
            <strong>{usableRunRate ? formatMetric(usableRunRate.value, usableRunRate.unit) : "0%"}</strong>
            <span className="microcopy">Degraded calls still get trust limits instead of vague dashboards.</span>
          </article>
          <article className="hero-meter">
            <span className="sample-meta">Average SNR</span>
            <strong>{averageSnr ? formatMetric(averageSnr.value, averageSnr.unit) : "Unknown"}</strong>
            <span className="microcopy">Quality posture affects which report claims are safe to trust.</span>
          </article>
          <article className="hero-meter">
            <span className="sample-meta">Top readiness tier</span>
            <strong>{topReadiness?.label ?? "No runs yet"}</strong>
            <span className="microcopy">Readiness tells the report what can and cannot be concluded.</span>
          </article>
        </div>
      </section>

      <section className="panel panel-spacious" id="quickstart">
        <div className="section-heading">
          <div>
            <span className="eyebrow muted">First 10 minutes</span>
            <h2>One blessed report workflow</h2>
          </div>
          <span className="microcopy">If Spectrum feels useful here, the rest of the platform becomes easier to trust.</span>
        </div>
        <div className="analytics-grid" style={{ gap: 18 }}>
          <div className="panel panel-spacious">
            <span className="sample-meta">Quickstart</span>
            <pre
              style={{
                marginTop: 12,
                padding: "16px 18px",
                borderRadius: 18,
                background: "rgba(18, 41, 67, 0.95)",
                color: "#f7efe1",
                fontSize: "0.95rem",
                lineHeight: 1.7,
                overflowX: "auto",
              }}
            >{`make bootstrap\nmake demo\nmake dev\nspectrum analyze examples/sample.wav --open`}</pre>
            <p className="microcopy" style={{ marginTop: 12 }}>
              `make demo` seeds importable sessions, while `spectrum analyze` creates a report-backed bundle from one local recording and opens the session view.
            </p>
          </div>
          <div className="panel panel-spacious">
            <span className="sample-meta">What one report gives you</span>
            <div className="stack compact" style={{ marginTop: 12 }}>
              <div className="info-row">
                <strong>Conversation diagnosis</strong>
                <span className="microcopy">Outcome, top risks, likely causes, confidence, and recommended next checks.</span>
              </div>
              <div className="info-row">
                <strong>Evidence-linked findings</strong>
                <span className="microcopy">Latency, unresolved intent, answer quality, interruptions, uncertainty, and recovery attempts.</span>
              </div>
              <div className="info-row">
                <strong>Human + agent perspectives</strong>
                <span className="microcopy">Separate sections for human experience, agent behavior, and beginning/middle/end arc.</span>
              </div>
              <div className="info-row">
                <strong>Trust limits</strong>
                <span className="microcopy">Role confidence, transcript quality, diarization readiness, and audio caveats.</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <AnalyzeAudioPanel />

      {apiError ? <section className="empty-state">{apiError}</section> : null}

      <section className="panel panel-spacious">
        <div className="section-heading">
          <div>
            <span className="eyebrow muted">Recent sessions</span>
            <h2>Analyze one file, then read the conversation report</h2>
          </div>
          <span className="microcopy">The report is primary. Cohorts and benchmarks come from report fields later.</span>
        </div>

        <form className="filter-bar" method="get">
          <select className="filter-select" defaultValue={filters.sourceType} name="source_type">
            <option value="all">All source types</option>
            {sourceOptions.map((sourceType) => (
              <option key={sourceType} value={sourceType}>
                {sourceType}
              </option>
            ))}
          </select>
          <select className="filter-select" defaultValue={filters.analysisMode} name="analysis_mode">
            <option value="all">All analysis modes</option>
            {analysisOptions.map((analysisMode) => (
              <option key={analysisMode} value={analysisMode}>
                {analysisMode}
              </option>
            ))}
          </select>
          <select className="filter-select" defaultValue={filters.language} name="language">
            <option value="all">All languages</option>
            {languageOptions.map((language) => (
              <option key={language} value={language}>
                {language}
              </option>
            ))}
          </select>
          <select className="filter-select" defaultValue={filters.readinessTier} name="readiness_tier">
            <option value="all">All readiness tiers</option>
            <option value="full">Full</option>
            <option value="partial">Partial</option>
            <option value="transcript_only">Transcript only</option>
            <option value="blocked">Blocked</option>
          </select>
          <select className="filter-select" defaultValue={filters.qualityBand} name="quality_band">
            <option value="all">All quality bands</option>
            <option value="clean">Clean</option>
            <option value="watch">Watch</option>
            <option value="risky">Risky</option>
          </select>
          <select className="filter-select" defaultValue={filters.rolePresence} name="role_presence">
            <option value="all">All role mixes</option>
            <option value="human_ai">Human + AI</option>
            <option value="human_only">Human only</option>
            <option value="ai_only">AI only</option>
            <option value="unknown">Unknown</option>
          </select>
          <button className="filter-toggle active" type="submit">
            Apply filters
          </button>
          <Link className="filter-toggle" href="/">
            Clear
          </Link>
        </form>

        <div className="ribbon-grid" style={{ marginTop: 18 }}>
          {cohortSummary.kpis.slice(0, 5).map((kpi) => (
            <article className="ribbon-card" key={kpi.key}>
              <span className="sample-meta">{kpi.label}</span>
              <strong>{formatMetric(kpi.value, kpi.unit)}</strong>
            </article>
          ))}
        </div>

        <div className="session-grid" style={{ marginTop: 18 }}>
          {recentRuns.length ? (
            recentRuns.map((run) => {
              const indexed = sessionIndexById.get(run.session_id);
              return (
                <Link href={`/sessions/${run.session_id}`} className="session-card" key={run.session_id}>
                  <div className="badge-row">
                    <span className={`badge ${run.usable ? "ok" : "warn"}`}>{run.usable ? "usable" : "review"}</span>
                    <span className="badge">{run.analysis_mode}</span>
                    <span className="badge accent">{run.readiness_tier}</span>
                  </div>
                  <h3>{run.title}</h3>
                  <p className="sample-meta">
                    {run.dataset_id ?? "ad hoc"} · {run.language ?? "unknown"} · {run.duration_sec.toFixed(1)} sec
                  </p>
                  <div className="session-card-metrics">
                    <div>
                      <span className="row-label">Average SNR</span>
                      <strong>{formatMetric(indexed?.quality.avg_snr_db ?? null, "dB")}</strong>
                    </div>
                    <div>
                      <span className="row-label">Noise ratio</span>
                      <strong>{formatMetric(indexed?.quality.noise_ratio ?? null)}</strong>
                    </div>
                    <div>
                      <span className="row-label">Top signal</span>
                      <strong>{run.top_signal ?? "Pending"}</strong>
                    </div>
                    <div>
                      <span className="row-label">Role posture</span>
                      <strong>{run.human_present && run.ai_present ? "human + ai" : run.human_present ? "human" : run.ai_present ? "ai" : "unknown"}</strong>
                    </div>
                  </div>
                </Link>
              );
            })
          ) : (
            <div className="empty-state">No sessions match the current filters. Clear the filters or analyze a fresh file.</div>
          )}
        </div>
      </section>

      <section className="panel panel-spacious">
        <div className="section-heading">
          <div>
            <span className="eyebrow muted">Advanced</span>
            <h2>Cohorts, datasets, and benchmarks</h2>
          </div>
          <span className="microcopy">These stay available, but they are now intentionally secondary to the session loop.</span>
        </div>
        <div className="analytics-grid">
          <div className="analytics-main">
            <section className="panel panel-spacious">
              <span className="eyebrow muted">Cohort trendline</span>
              <h2>Current workspace drift</h2>
              <div className="table-shell" style={{ marginTop: 12 }}>
                <table className="analytics-table">
                  <thead>
                    <tr>
                      <th>Bucket</th>
                      <th>Runs</th>
                      <th>Usable</th>
                      <th>Avg SNR</th>
                      <th>Hesitation</th>
                      <th>Friction</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cohortTrends.length ? (
                      cohortTrends.map((trend) => (
                        <tr key={trend.bucket}>
                          <td><strong>{trend.bucket}</strong></td>
                          <td>{trend.run_count}</td>
                          <td>{formatMetric(trend.usable_run_rate, "%")}</td>
                          <td>{formatMetric(trend.avg_snr_db, "dB")}</td>
                          <td>{Math.round(trend.hesitation_avg)}</td>
                          <td>{Math.round(trend.friction_avg)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={6}>
                          <div className="empty-state">Import demo data or analyze a few sessions to populate cohort trends.</div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="panel panel-spacious">
              <span className="eyebrow muted">Dataset health</span>
              <h2>Imported coverage</h2>
              <div className="table-shell" style={{ marginTop: 12 }}>
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
          </div>

          <aside className="analytics-side">
            <section className="panel panel-spacious">
              <span className="eyebrow muted">Distribution mix</span>
              <h2>Readiness and evidence</h2>
              <div className="alert-grid" style={{ marginTop: 12 }}>
                {cohortDistributions.slice(0, 4).map((distribution) => (
                  <article className="alert-card" key={distribution.key}>
                    <span className="badge accent">{distribution.label}</span>
                    <div className="badge-row">
                      {distribution.items.slice(0, 5).map((item) => (
                        <span className="badge" key={`${distribution.key}-${item.key}`}>
                          {item.label} {item.value}
                        </span>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="panel panel-spacious">
              <span className="eyebrow muted">Benchmarks</span>
              <h2>Coverage snapshot</h2>
              <div className="table-shell" style={{ marginTop: 12 }}>
                <table className="analytics-table">
                  <thead>
                    <tr>
                      <th>Dataset</th>
                      <th>Status</th>
                      <th>Snapshot</th>
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
                          <td>
                            <span className={`badge ${entry.status === "ready" ? "ok" : "warn"}`}>{entry.status}</span>
                          </td>
                          <td>
                            <div className="badge-row">
                              {matching.slice(0, 2).map((result) => (
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
        </div>
      </section>
    </main>
  );
}
