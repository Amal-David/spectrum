import Link from "next/link";
import { notFound } from "next/navigation";

import { fetchSessionBundle } from "../../../lib/api-client";
import { audioPathFor, formatMetric, formatPct, spectrogramPathFor } from "../../../lib/data";
import { SessionWorkspace } from "../../components/session-workspace";

export const dynamic = "force-dynamic";

type SessionBundle = NonNullable<Awaited<ReturnType<typeof fetchSessionBundle>>>;
type ReportFinding = SessionBundle["conversation_report"]["findings"][number];
type EvidenceRef = ReportFinding["evidence_refs"][number];

function formatCategory(value: string) {
  return value.replaceAll("_", " ");
}

function severityBadgeClass(severity: string) {
  if (severity === "critical" || severity === "risk") return "warn";
  if (severity === "info") return "ok";
  return "accent";
}

function evidenceHref(ref?: EvidenceRef) {
  if (!ref) return "#evidence-workspace";
  if (ref.kind === "turn") return `#turn-${ref.ref_id}`;
  if (ref.kind === "event") return `#event-${ref.ref_id}`;
  if (ref.kind === "question") return `#question-${ref.ref_id}`;
  return "#evidence-workspace";
}

function metricSummary(finding: ReportFinding) {
  const entries = Object.entries(finding.related_metrics).slice(0, 3);
  if (!entries.length) return null;
  return entries.map(([key, value]) => `${key.replaceAll("_", " ")} ${String(value)}`).join(" · ");
}

export default async function SessionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const bundle = await fetchSessionBundle(id);
  if (!bundle) {
    notFound();
  }

  const visibleProfileCount = bundle.profile_display.filter((field) => field.display_state === "visible" || field.display_state === "muted").length;
  const caveats = Array.from(new Set([...bundle.quality.warning_flags, ...(bundle.diagnostics.confidence_caveats ?? []), ...(bundle.diagnostics.degraded_reasons ?? [])])).slice(0, 6);
  const report = bundle.conversation_report;
  const riskFindings = report.findings.filter((finding) => finding.severity === "critical" || finding.severity === "risk");

  return (
    <main className="analytics-shell detail-shell">
      <Link href="/" className="eyebrow">
        Back to workspace
      </Link>

      <section className="analytics-hero detail-hero">
        <div className="hero-copy">
          <span className="eyebrow">Conversation Report</span>
          <h1>{bundle.session.title}</h1>
          <p>
            {report.executive_summary.overall_diagnosis}
          </p>
          <div className="badge-row">
            <span className={`badge ${riskFindings.length ? "warn" : "ok"}`}>{report.executive_summary.call_outcome.replaceAll("_", " ")}</span>
            <span className="badge">{bundle.session.duration_sec.toFixed(1)} seconds</span>
            <span className="badge accent">{bundle.session.readiness_tier ?? "blocked"}</span>
            <span className="badge">{bundle.session.dataset_id ?? "ad hoc"}</span>
          </div>
        </div>

        <div className="hero-rail">
          <article className="hero-meter">
            <span className="sample-meta">Report confidence</span>
            <strong>{formatPct(report.executive_summary.confidence)}</strong>
            <span className="microcopy">every claim carries evidence and confidence</span>
          </article>
          <article className="hero-meter">
            <span className="sample-meta">Findings</span>
            <strong>{report.findings.length}</strong>
            <span className="microcopy">{riskFindings.length} risk or critical</span>
          </article>
          <article className="hero-meter">
            <span className="sample-meta">Trust limits</span>
            <strong>{report.trust_limits.length}</strong>
            <span className="microcopy">{caveats.length ? caveats[0].replaceAll("_", " ") : "no major caveat"}</span>
          </article>
          <article className="hero-meter">
            <span className="sample-meta">Next action</span>
            <strong>{riskFindings.length ? "Review" : "Compare"}</strong>
            <span className="microcopy">{report.executive_summary.recommended_next_action}</span>
          </article>
        </div>
      </section>

      <section className="panel panel-spacious">
        <div className="section-heading">
          <div>
            <span className="eyebrow muted">Diagnostic report</span>
            <h2>Every major human-AI conversation angle in one evidence-backed read</h2>
          </div>
          <span className="microcopy">The report is the product surface. The workspace below exists to prove or challenge each claim.</span>
        </div>
        <div className="analytics-grid">
          <div className="analytics-main">
            <section className="panel panel-spacious">
              <span className="eyebrow muted">Executive summary</span>
              <div className="stack compact" style={{ marginTop: 12 }}>
                <div className="info-row">
                  <strong>{report.executive_summary.call_outcome.replaceAll("_", " ")}</strong>
                  <span className="microcopy">{report.executive_summary.overall_diagnosis}</span>
                </div>
                <div className="info-row">
                  <strong>Recommended next action</strong>
                  <span className="microcopy">{report.executive_summary.recommended_next_action}</span>
                </div>
                {report.executive_summary.top_risks.length ? (
                  <div className="info-row">
                    <strong>Top risks</strong>
                    <span className="microcopy">{report.executive_summary.top_risks.join(" · ")}</span>
                  </div>
                ) : null}
              </div>
            </section>

            <section className="panel panel-spacious">
              <span className="eyebrow muted">Comprehensive findings</span>
              <div className="stack compact" style={{ marginTop: 12 }}>
                {report.findings.length ? (
                  report.findings.map((finding) => (
                    <a className="info-row report-finding-row" href={evidenceHref(finding.evidence_refs[0])} key={finding.finding_id}>
                      <div className="badge-row">
                        <span className={`badge ${severityBadgeClass(finding.severity)}`}>{finding.severity}</span>
                        <span className="badge">{formatCategory(finding.category)}</span>
                        <span className="badge accent">{formatPct(finding.confidence)}</span>
                        <span className="badge">{finding.source}</span>
                      </div>
                      <strong>{finding.title}</strong>
                      <span className="microcopy">{finding.claim}</span>
                      <span className="microcopy">{finding.impact}</span>
                      <span className="microcopy">Likely cause: {finding.likely_cause}</span>
                      <span className="microcopy">Next check: {finding.suggested_next_check}</span>
                      {metricSummary(finding) ? <span className="microcopy">{metricSummary(finding)}</span> : null}
                    </a>
                  ))
                ) : (
                  <div className="empty-state">No findings were generated for this session. Rebuild the analysis to populate the report.</div>
                )}
              </div>
            </section>
          </div>

          <aside className="analytics-side">
            <section className="panel panel-spacious">
              <span className="eyebrow muted">Report sections</span>
              <div className="stack compact" style={{ marginTop: 12 }}>
                <div className="info-row">
                  <strong>{report.human_experience.label}</strong>
                  <span className="microcopy">{report.human_experience.summary}</span>
                </div>
                <div className="info-row">
                  <strong>{report.agent_behavior.label}</strong>
                  <span className="microcopy">{report.agent_behavior.summary}</span>
                </div>
                {report.conversation_arc.map((section) => (
                  <div className="info-row" key={section.label}>
                    <strong>{section.label}</strong>
                    <span className="microcopy">{section.summary}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="panel panel-spacious">
              <span className="eyebrow muted">Trust limits</span>
              <div className="stack compact" style={{ marginTop: 12 }}>
                {report.trust_limits.length ? (
                  report.trust_limits.map((limit) => (
                    <div className="info-row" key={limit.key}>
                      <strong>{limit.label}</strong>
                      <span className={`badge ${severityBadgeClass(limit.severity)}`}>{limit.severity}</span>
                      <span className="microcopy">{limit.summary}</span>
                    </div>
                  ))
                ) : (
                  <span className="microcopy">No active trust limits were reported for this session.</span>
                )}
              </div>
            </section>

            <section className="panel panel-spacious">
              <span className="eyebrow muted">Run context</span>
              <div className="stack compact" style={{ marginTop: 12 }}>
                <div className="info-row">
                  <strong>Language and region</strong>
                  <span className="microcopy">{bundle.session.language ?? "unknown"} · {bundle.session.region ?? "region unknown"}</span>
                </div>
                <div className="info-row">
                  <strong>Speech ratio</strong>
                  <span className="microcopy">{formatPct(bundle.quality.speech_ratio)} · average SNR {formatMetric(bundle.quality.avg_snr_db, "dB")}</span>
                </div>
                <div className="info-row">
                  <strong>Profile coverage</strong>
                  <span className="microcopy">{visibleProfileCount} confidence-gated fields visible or muted below</span>
                </div>
              </div>
            </section>
          </aside>
        </div>
      </section>

      <SessionWorkspace audioSrc={audioPathFor(id)} bundle={bundle} jobId={id} spectrogramSrc={spectrogramPathFor(id)} />
    </main>
  );
}
