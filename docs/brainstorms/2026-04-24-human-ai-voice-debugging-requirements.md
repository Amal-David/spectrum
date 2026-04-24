---
date: 2026-04-24
topic: human-ai-voice-debugging
---

# Human-to-AI Voice Call Debugging

## Problem Frame

Spectrum has strong infrastructure: audio ingestion, transcripts, diarization, speaker roles, question analytics, behavioral signals, evidence references, bundles, comparisons, cohorts, and benchmarks. The product problem is that those primitives currently surface as generic "conversation analytics" and "session bundle" machinery, so a product owner still has to translate raw signals into the thing they care about: where a human-to-AI voice call broke, why it likely broke, and what to inspect next.

The primary wedge should be debugging human-to-AI voice calls through a comprehensive report for every conversation. The user is a product, engineering, or operations person building a voice agent. They do not need an emotion dashboard first. They need a post-call diagnostic report that turns a recording into evidence-backed findings across multiple angles: user waited here, agent interrupted there, question went unanswered, role attribution is uncertain, the agent caused friction after this turn, the conversation arc changed here, and the run regressed against another agent version.

The longer-term open-source direction still fits: Spectrum can become the infrastructure layer for conversation analytics. But the first product experience should be a focused debugger, not a generic analytics workbench.

## Current App Diagnosis

- The homepage and README emphasize portable session bundles, voice analytics, emotional intelligence, cohorts, datasets, and benchmarks before they make the human-to-AI debugging loop obvious.
- The upload flow accepts audio but does not ask for agent context: scenario, agent version, success criteria, expected outcome, human/AI role hints, or known failure hypothesis.
- The session detail page has the right raw primitives, but the first read is still summary, emotion spans, trust coverage, questions, signals, and timeline rather than "here are the agent-experience breakdowns."
- The workspace exposes role filtering, role assignment, question analytics, event timelines, transcript evidence, confidence, and readiness. These are excellent ingredients, but they are arranged like an analyst console instead of a voice-agent debugger.
- The compare view compares two session bundles. For the chosen wedge, it should compare two agent runs or versions and answer which one has worse human wait, interruption, unresolved intent, hesitation, or friction.
- The benchmark runner can measure model outputs, confidence, and latency, but a product person needs it translated into product decisions: which provider is good enough for which debug finding, what it misses, and what user-facing claims we can safely make.
- The demo data has some AI/human examples, but there is no canonical "broken AI voice call" demo that immediately shows the aha moment.

## Requirements

- R1. The top-level product positioning should say Spectrum helps teams debug human-to-AI voice calls, with "open-source conversation analytics infrastructure" framed as the platform underneath.
- R2. The first-run flow should guide a user from one recording to a call debug report in under two minutes, without requiring them to understand bundles, cohorts, benchmarks, or provider internals.
- R3. The upload/import flow should optionally collect voice-agent context: call scenario, agent or prompt version, expected outcome, success/failure notes, and human/AI speaker hints.
- R4. Each analyzed human-to-AI session should produce a first-class comprehensive conversation report with executive summary, conversation arc, human experience, agent behavior, findings, severity, confidence, evidence references, likely causes, trust limits, and suggested next inspections.
- R5. Debug findings should prioritize behaviorally observable issues over inferred emotion: long user wait, agent latency, interruption, overlap, unanswered user intent, repeated clarification, user hesitation, escalation language, low-confidence role attribution, and transcript/diarization uncertainty.
- R6. The session overview should lead with "what broke and why it matters" before generic summary, emotion spans, profile attributes, or raw signal cards.
- R7. Every debug finding should be evidence-first: clicking a finding should jump to the transcript/audio moment, show the human/AI turns around it, and explain which signals contributed.
- R8. The workspace should default to human-to-AI debugging language: human turns, AI turns, breakdowns, questions, transcript, evidence, and confidence. Emotion and demographics should be demoted or hidden unless directly relevant and confidence-gated.
- R9. Manual role assignment should remain prominent because incorrect human/AI attribution breaks the debugger. Role confidence should be explained as a product trust issue, not only a data quality metric.
- R10. The compare experience should be reframed around agent versions or runs: "Which run was better for the human, and why?" It should highlight changes in wait time, interruption, unresolved questions, friction, hesitation, and debug findings.
- R11. Model/provider benchmarks should generate product-facing scorecards in addition to raw metrics. The scorecard should answer which provider supports which user-facing debug capabilities, what it misses, expected latency/cost tradeoffs, and whether the output is safe for a launch claim.
- R12. Spectrum should include at least one canonical broken human-to-AI demo call with known expected findings so the first product experience is self-explanatory.
- R13. The public docs should converge on one story: "debug voice-agent calls from evidence-backed conversation telemetry." Avoid leading with emotional intelligence, broad call-center QA, or generic audio analysis.
- R14. The underlying session bundle should remain the portable infrastructure artifact, but the product UI should expose a smaller, opinionated debug layer on top.
- R15. Trust/readiness should be translated into product terms: "safe to compare," "safe to inspect timing," "speaker roles need review," "transcript too uncertain for root-cause claims."

## Success Criteria

- A new user can open the demo or upload one call and answer "where did the voice-agent experience break?" in under two minutes.
- The first screen, upload panel, session overview, and README all clearly identify human-to-AI voice-call debugging as the primary workflow.
- A canonical demo call produces a comprehensive, useful, evidence-linked conversation report without manual interpretation.
- The benchmark summary helps a product person decide whether SenseVoiceSmall, emotion2vec, OpenAI-backed analysis, or a local fallback should power specific debug features.
- Compare mode can tell a product owner which of two agent runs regressed and cite the top evidence.
- Emotion is no longer the headline promise; it is treated as an optional, confidence-gated supporting signal.
- Infrastructure-minded users can still see and reuse bundles, API outputs, and evidence primitives without the core UI becoming infrastructure-first.

## Scope Boundaries

- Post-call debugging first; real-time call monitoring is not part of this pass.
- Human-to-AI voice calls first; support QA, interview analysis, coaching, and generic meeting analytics are secondary use cases.
- Evidence-backed behavioral telemetry first; broad emotion classification, personality inference, age, gender, accent, or demographics should not be core product promises.
- A comprehensive first taxonomy is acceptable, but every claim must stay evidence-linked and confidence-scored.
- Product-facing scorecards first; do not over-optimize provider benchmarking around academic metrics that do not map to user decisions.
- Local/open-source infrastructure remains important, but the initial user journey should not require users to understand the full architecture.

## Key Decisions

- Primary wedge: Human-to-AI voice-call debugging. This is narrower and more compelling than generic conversation analytics, and it uses the strongest existing primitives.
- Product layer over infrastructure layer: Keep session bundles as the durable substrate, but introduce a more opinionated debug report for the UI and docs.
- Behavior over emotion: Voice-agent teams can act on waits, interruptions, unresolved intents, and failed answers more directly than on broad emotion labels.
- Demo as product proof: A canonical broken call is not nice-to-have; it is the fastest way to make the product legible to builders and product teams.
- Benchmarks must answer product questions: Provider comparisons should say what Spectrum can safely ship, not only which model returned labels faster.

## Dependencies / Assumptions

- Existing diarization, role assignment, question analytics, transcript evidence, signal cards, and compare infrastructure are sufficient to support a first product-quality debugger without rebuilding the entire pipeline.
- The initial report should be comprehensive rather than conservative, while still making confidence and evidence limits explicit.
- Users building AI voice agents will accept post-call analysis if the report is actionable and evidence-linked.
- Open-source positioning is strongest if the infrastructure remains visible through bundles, APIs, and schemas, while the default UI stays task-focused.

## Product Gaps To Close First

- Positioning gap: The product currently sounds like an analytics platform; it needs to sound like a debugger for voice-agent failures.
- Input gap: The app does not know enough about the call scenario or agent version to explain failures in product language.
- Output gap: The app has signals and events, but not a product-facing debug finding object.
- Navigation gap: The session UI requires too much synthesis before the user reaches the "aha."
- Demo gap: There is no single demo path that proves the primary workflow.
- Benchmark gap: Provider summaries need to map model behavior to launch decisions and UX confidence, not just labels and latency.

## Recommended First Slice

- Reposition the homepage, upload panel, and README around "debug a human-to-AI voice call."
- Add a lightweight agent-context step to upload/import.
- Add a comprehensive diagnostic report generated from existing primitives and provider enrichment where available.
- Rework the session overview so the debug report is the first thing users see.
- Add a canonical broken voice-agent demo call and expected findings.
- Upgrade the benchmark scorecard so a product owner can decide which model/provider belongs in Spectrum first.

## Alternatives Considered

- Generic conversation analytics: Preserves breadth but makes the product hard to understand and weakens prioritization.
- Emotion intelligence: Interesting as a signal, but too fuzzy and risky as the headline promise.
- Support QA: A viable adjacent market, but less aligned with the human-to-AI role machinery and open-source infrastructure story.
- Infrastructure-first open source: Strategically important, but too abstract as the first product experience.

## Outstanding Questions

### Resolve Before Planning

- None. The first taxonomy should be comprehensive and include timing, turn-taking, intent resolution, answer quality, uncertainty, friction, recovery, role confidence, and transcript/audio risk.

### Deferred to Planning

- [Affects R3][Technical] Where should call scenario, agent version, and success criteria live in the session metadata and import path?
- [Affects R4][Technical] Should debug findings be generated only from deterministic primitives first, or should provider analysis contribute likely-cause explanations when confidence is high?
- [Affects R10][Technical] Which compare metrics are already reliable enough to show as agent-version regressions?
- [Affects R12][Product/data] Which local or synthetic recording should become the canonical broken voice-agent demo?

## Next Steps

Resolve the debug taxonomy question, then move to structured implementation planning.
