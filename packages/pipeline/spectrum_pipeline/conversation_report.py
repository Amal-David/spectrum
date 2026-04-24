from __future__ import annotations

from statistics import mean
from typing import Any

from spectrum_core.models import (
    ContentSummary,
    ConversationReport,
    ConversationReportCategory,
    ConversationReportExecutiveSummary,
    ConversationReportFinding,
    ConversationReportSection,
    ConversationReportTrustLimit,
    Diagnostics,
    DiarizationSummary,
    EventModel,
    EvidenceRef,
    MetricSummary,
    QualitySummary,
    QuestionAnalyticsRow,
    ReportFindingSource,
    ReportSeverity,
    SignalCard,
    SpeakerRole,
    SpeakerRoleSummary,
    SpeakerSummary,
    StageStatus,
    TimeWindow,
    TurnModel,
)

DEFLECTION_TERMS = ("can't", "cannot", "unable", "not sure", "don't know", "do not know", "sorry", "unfortunately")
CLARIFICATION_TERMS = ("repeat", "clarify", "could you say", "can you say", "what do you mean", "which one")
ESCALATION_TERMS = ("agent", "representative", "human", "cancel", "complaint", "frustrated", "annoyed", "angry", "not working", "doesn't work")
UNCERTAINTY_TERMS = ("maybe", "i think", "not sure", "confused", "i don't know", "i do not know", "um", "uh")
RECOVERY_TERMS = ("sorry", "apologize", "let me", "i can help", "here's", "next step", "confirm", "fixed")

SEVERITY_RANK = {"critical": 4, "risk": 3, "watch": 2, "info": 1}


def build_conversation_report(
    *,
    session_id: str,
    metadata: dict[str, Any] | None,
    quality: QualitySummary,
    speaker_roles: SpeakerRoleSummary,
    diarization: DiarizationSummary,
    speakers: list[SpeakerSummary],
    turns: list[TurnModel],
    events: list[EventModel],
    questions: list[QuestionAnalyticsRow],
    content: ContentSummary,
    signals: list[SignalCard],
    metrics: dict[str, MetricSummary],
    diagnostics: Diagnostics,
    stage_status: list[StageStatus],
) -> ConversationReport:
    metadata = metadata or {}
    role_map = {assignment.speaker_id: assignment.speaker_role for assignment in speaker_roles.assignments}
    human_turns = [turn for turn in turns if _role_for_turn(turn, role_map) == "human"]
    ai_turns = [turn for turn in turns if _role_for_turn(turn, role_map) == "ai"]
    human_to_ai_pairs = _role_pairs(turns, role_map, "human", "ai")
    ai_to_human_pairs = _role_pairs(turns, role_map, "ai", "human")
    provider_enrichment = metadata.get("openai_report_enrichment") if isinstance(metadata.get("openai_report_enrichment"), dict) else {}

    findings: list[ConversationReportFinding] = []
    trust_limits: list[ConversationReportTrustLimit] = []

    role_confidences = [assignment.confidence for assignment in speaker_roles.assignments if assignment.speaker_role in {"human", "ai"}]
    min_role_confidence = min(role_confidences) if role_confidences else 0.0
    has_human_ai = bool(human_turns and ai_turns)

    if not has_human_ai or min_role_confidence < 0.72:
        findings.append(
            _finding(
                session_id,
                findings,
                "role_confidence",
                "Human/AI role attribution needs review",
                "risk" if not has_human_ai else "watch",
                0.82,
                "The report depends on accurate human and AI speaker roles, and this session does not have strong role confidence.",
                "Misassigned roles can invert latency, answer-quality, and human-experience conclusions.",
                "Speaker-role evidence is missing, weak, or manually unverified.",
                [EvidenceRef(kind="speaker_roles", ref_id="speaker_roles", label="role confidence")],
                {"min_role_confidence": round(min_role_confidence, 3), "human_ai_detected": has_human_ai},
                "Review the speaker role assignments before treating agent findings as final.",
            )
        )
        trust_limits.append(
            ConversationReportTrustLimit(
                key="role_confidence",
                label="Human/AI role confidence",
                severity="risk" if not has_human_ai else "watch",
                confidence=0.85,
                summary="Role confidence is not strong enough for fully trusted agent-vs-human conclusions.",
                evidence_refs=[EvidenceRef(kind="speaker_roles", ref_id="speaker_roles")],
            )
        )

    quality_caveats = sorted(set(quality.warning_flags + diagnostics.confidence_caveats + diagnostics.degraded_reasons))
    if not quality.is_usable or quality.noise_ratio > 0.35 or (quality.avg_snr_db is not None and quality.avg_snr_db < 10) or quality_caveats:
        findings.append(
            _finding(
                session_id,
                findings,
                "transcript_or_audio_risk",
                "Audio or transcript quality limits the report",
                "risk" if not quality.is_usable else "watch",
                0.78,
                "Some conversation conclusions should be treated as conditional because the recording or transcript path is degraded.",
                "Root-cause claims can be distorted when speech, timing, or diarization evidence is weak.",
                "Quality warnings, degraded provider paths, or noisy audio are present.",
                [EvidenceRef(kind="quality", ref_id="quality", label="quality posture")],
                {
                    "noise_ratio": round(quality.noise_ratio, 3),
                    "avg_snr_db": quality.avg_snr_db,
                    "caveat_count": len(quality_caveats),
                },
                "Inspect transcript alignment and speaker timing before using this report as a launch-quality diagnosis.",
            )
        )
        trust_limits.append(
            ConversationReportTrustLimit(
                key="transcript_or_audio_risk",
                label="Transcript/audio confidence",
                severity="risk" if not quality.is_usable else "watch",
                confidence=0.8,
                summary=", ".join(quality_caveats[:5]) or "Audio quality is degraded enough to affect report confidence.",
                evidence_refs=[EvidenceRef(kind="quality", ref_id="quality")],
            )
        )

    latency_pairs = [(human, ai, max(0, ai.start_ms - human.end_ms)) for human, ai in human_to_ai_pairs]
    long_latency_pairs = sorted([item for item in latency_pairs if item[2] >= 2500], key=lambda item: item[2], reverse=True)
    if long_latency_pairs:
        human, ai, latency_ms = long_latency_pairs[0]
        findings.append(
            _finding(
                session_id,
                findings,
                "agent_latency",
                "Agent response latency is visible to the human",
                "critical" if latency_ms >= 8000 else "risk",
                _confidence_from_turns(human, ai, 0.84),
                f"The AI took {latency_ms} ms to respond after a human turn.",
                "Long gaps make the agent feel broken, inattentive, or uncertain even when the eventual answer is acceptable.",
                "The agent response began materially after the human finished speaking.",
                [EvidenceRef(kind="turn", ref_id=human.turn_id, label="human turn"), EvidenceRef(kind="turn", ref_id=ai.turn_id, label="AI response")],
                {"latency_ms": latency_ms, "human_turn_words": human.word_count, "ai_turn_words": ai.word_count},
                "Replay the gap and check whether orchestration, ASR finalization, tool use, or TTS startup caused the delay.",
                time_window=TimeWindow(start_ms=human.start_ms, end_ms=ai.end_ms, label="agent latency"),
            )
        )

    wait_pairs = sorted([item for item in ai_to_human_pairs if max(0, item[1].start_ms - item[0].end_ms) >= 3000], key=lambda item: item[1].start_ms - item[0].end_ms, reverse=True)
    if wait_pairs:
        ai, human = wait_pairs[0]
        wait_ms = max(0, human.start_ms - ai.end_ms)
        findings.append(
            _finding(
                session_id,
                findings,
                "human_wait",
                "Human waited before re-engaging",
                "risk" if wait_ms >= 6000 else "watch",
                _confidence_from_turns(ai, human, 0.74),
                f"The human waited {wait_ms} ms after the AI turn before responding.",
                "A long human pause after the AI speaks can indicate confusion, cognitive load, or uncertainty about what to do next.",
                "The previous AI response may have been unclear, too long, or insufficiently directive.",
                [EvidenceRef(kind="turn", ref_id=ai.turn_id, label="AI turn"), EvidenceRef(kind="turn", ref_id=human.turn_id, label="human response")],
                {"wait_ms": wait_ms, "ai_turn_words": ai.word_count, "human_turn_words": human.word_count},
                "Review the AI turn immediately before the pause and check whether it gave the human a clear next step.",
                time_window=TimeWindow(start_ms=ai.start_ms, end_ms=human.end_ms, label="human wait"),
            )
        )

    for human, ai, latency_ms in latency_pairs:
        if _looks_like_request(human.text) and _answer_quality_risk(ai):
            findings.append(
                _finding(
                    session_id,
                    findings,
                    "answer_quality",
                    "AI answer looks weak for the human request",
                    "risk",
                    _confidence_from_turns(human, ai, 0.72),
                    "The AI response after a human request is short, uncertain, deflective, or non-committal.",
                    "The human may leave without a useful answer even if the conversation technically continued.",
                    "The agent likely failed to resolve the user intent or lacked enough context/tool support.",
                    [EvidenceRef(kind="turn", ref_id=human.turn_id, label="human request"), EvidenceRef(kind="turn", ref_id=ai.turn_id, label="AI answer")],
                    {"latency_ms": latency_ms, "ai_word_count": ai.word_count, "ai_uncertainty_markers": ai.uncertainty_markers},
                    "Check the agent prompt/tool trace for this turn and confirm whether the response addressed the user goal.",
                    time_window=TimeWindow(start_ms=human.start_ms, end_ms=ai.end_ms, label="answer quality"),
                )
            )
            break

    unresolved_turn = _last_unresolved_human_turn(turns, role_map)
    if unresolved_turn is not None:
        findings.append(
            _finding(
                session_id,
                findings,
                "intent_resolution",
                "Human intent appears unresolved near the end",
                "risk",
                _confidence_from_turn(unresolved_turn, 0.68),
                "The conversation ends with a human request, concern, or question that has no later AI resolution in the transcript.",
                "The user may have ended the call without the agent completing the task.",
                "The agent either did not answer after the final human turn or the transcript ended before resolution.",
                [EvidenceRef(kind="turn", ref_id=unresolved_turn.turn_id, label="final human intent")],
                {"turn_words": unresolved_turn.word_count, "turn_start_ms": unresolved_turn.start_ms},
                "Check whether the call ended early, the transcript missed the final answer, or the agent failed to recover.",
                time_window=TimeWindow(start_ms=unresolved_turn.start_ms, end_ms=unresolved_turn.end_ms, label="unresolved intent"),
            )
        )

    clarification_turns = [turn for turn in ai_turns if _contains_any(turn.text, CLARIFICATION_TERMS)]
    if len(clarification_turns) >= 2:
        findings.append(
            _finding(
                session_id,
                findings,
                "clarification_loop",
                "Conversation entered a clarification loop",
                "risk",
                min(0.9, mean([turn.confidence or 0.7 for turn in clarification_turns])),
                "The AI repeatedly asked the human to restate, clarify, or choose information.",
                "Repeated clarification increases user effort and can hide an upstream ASR, intent, or prompt problem.",
                "The agent likely lacked enough context or failed to ground the user's request.",
                [EvidenceRef(kind="turn", ref_id=turn.turn_id, label="clarification") for turn in clarification_turns[:3]],
                {"clarification_turn_count": len(clarification_turns)},
                "Group the clarification turns and decide whether the agent should infer, ask one better question, or route differently.",
                time_window=TimeWindow(start_ms=clarification_turns[0].start_ms, end_ms=clarification_turns[-1].end_ms, label="clarification loop"),
            )
        )

    uncertain_human_turns = [turn for turn in human_turns if turn.uncertainty_markers or turn.filler_count >= 2 or _contains_any(turn.text, UNCERTAINTY_TERMS)]
    high_hesitation_questions = [question for question in questions if question.hesitation_score >= 60]
    if uncertain_human_turns or high_hesitation_questions:
        evidence_refs = [EvidenceRef(kind="turn", ref_id=turn.turn_id, label="human uncertainty") for turn in uncertain_human_turns[:3]]
        evidence_refs.extend(EvidenceRef(kind="question", ref_id=question.question_id, label=question.affect_tag) for question in high_hesitation_questions[:2])
        first_ms = min((turn.start_ms for turn in uncertain_human_turns), default=0)
        last_ms = max((turn.end_ms for turn in uncertain_human_turns), default=0)
        findings.append(
            _finding(
                session_id,
                findings,
                "human_uncertainty",
                "Human uncertainty shows up in the conversation",
                "watch",
                0.7,
                "The human produced uncertainty markers, fillers, or hesitant responses during the call.",
                "User uncertainty is often the earliest sign that the agent's instructions or answer framing are not landing.",
                "The preceding AI turns may be underspecified, too broad, or missing the user's actual goal.",
                evidence_refs,
                {"uncertain_turn_count": len(uncertain_human_turns), "high_hesitation_question_count": len(high_hesitation_questions)},
                "Inspect the AI turns immediately before these moments and check whether the next action was obvious.",
                time_window=TimeWindow(start_ms=first_ms, end_ms=last_ms, label="human uncertainty") if uncertain_human_turns else None,
            )
        )

    interruption_events = [event for event in events if event.type in {"interruption", "overlap"} or "overlap" in event.type]
    overlap_windows = diarization.overlap_windows
    if interruption_events or overlap_windows:
        first_event = interruption_events[0] if interruption_events else None
        refs = [EvidenceRef(kind="event", ref_id=event.event_id, label=event.type) for event in interruption_events[:4]]
        refs.extend(EvidenceRef(kind="diarization", ref_id="overlap_windows", label="overlap") for _window in overlap_windows[:1])
        findings.append(
            _finding(
                session_id,
                findings,
                "interruption_overlap",
                "Turn-taking shows interruption or overlap",
                "risk" if len(interruption_events) + len(overlap_windows) >= 2 else "watch",
                0.76,
                "The call contains interruption or overlap evidence.",
                "Overlapping speech can make the human feel cut off and can degrade ASR/agent state tracking.",
                "The agent may be speaking too early, barge-in handling may be misconfigured, or diarization may be unstable.",
                refs,
                {"interruption_event_count": len(interruption_events), "overlap_window_count": len(overlap_windows)},
                "Replay overlap windows and check whether the AI started speaking before the human finished.",
                time_window=TimeWindow(start_ms=first_event.begin_ms, end_ms=first_event.end_ms, label="interruption") if first_event else overlap_windows[0] if overlap_windows else None,
            )
        )

    turn_balance_gap = _turn_balance_gap(speakers)
    if turn_balance_gap is not None and turn_balance_gap >= 0.38:
        dominant = max(speakers, key=lambda speaker: speaker.talk_ratio)
        findings.append(
            _finding(
                session_id,
                findings,
                "turn_taking",
                "Turn balance is skewed",
                "watch",
                0.66,
                "One speaker dominates the conversation timing.",
                "Large talk-balance gaps can indicate monologue, poor interruption handling, or insufficient user participation.",
                "The agent may be over-talking, or the human may be stuck explaining without resolution.",
                [EvidenceRef(kind="speaker", ref_id=dominant.speaker_id, label="dominant speaker")],
                {"talk_ratio_gap": round(turn_balance_gap, 3), "dominant_talk_ratio": round(dominant.talk_ratio, 3)},
                "Check whether the dominant speaker is the AI and whether the human had enough room to complete the task.",
            )
        )

    friction_signal = _signal(signals, "friction")
    frustration_signal = _signal(signals, "frustration_risk")
    escalation_turns = [turn for turn in human_turns if _contains_any(turn.text, ESCALATION_TERMS)]
    if escalation_turns or _signal_score(friction_signal) >= 65 or _signal_score(frustration_signal) >= 65:
        findings.append(
            _finding(
                session_id,
                findings,
                "friction_or_escalation",
                "Friction or escalation risk is present",
                "risk",
                max(_signal_confidence(friction_signal), _signal_confidence(frustration_signal), 0.68),
                "The call shows friction through escalation language, friction signals, or frustration risk.",
                "This is the highest-priority class of conversation defect because it can convert directly into churn, complaints, or failed automation.",
                "The agent likely failed to answer cleanly, made the user repeat themselves, or did not recover from an earlier issue.",
                [EvidenceRef(kind="turn", ref_id=turn.turn_id, label="escalation language") for turn in escalation_turns[:2]]
                + [EvidenceRef(kind="signal", ref_id=signal.key, label=signal.label) for signal in [friction_signal, frustration_signal] if signal],
                {
                    "friction_score": _signal_score(friction_signal),
                    "frustration_risk_score": _signal_score(frustration_signal),
                    "escalation_turn_count": len(escalation_turns),
                },
                "Start with this moment when reviewing product failures; it is the strongest candidate for user-visible harm.",
                time_window=TimeWindow(start_ms=escalation_turns[0].start_ms, end_ms=escalation_turns[0].end_ms, label="escalation") if escalation_turns else None,
            )
        )

    recovery_turns = [turn for turn in ai_turns if _contains_any(turn.text, RECOVERY_TERMS)]
    if recovery_turns:
        findings.append(
            _finding(
                session_id,
                findings,
                "agent_recovery",
                "Agent attempted recovery",
                "info",
                min(0.88, mean([turn.confidence or 0.7 for turn in recovery_turns])),
                "The AI made at least one apology, repair, confirmation, or next-step attempt after the conversation had risk signals.",
                "Recovery attempts can reduce damage, but they should be checked for whether they actually resolved the user's goal.",
                "The agent recognized uncertainty or friction and attempted to steer the call back to resolution.",
                [EvidenceRef(kind="turn", ref_id=turn.turn_id, label="recovery attempt") for turn in recovery_turns[:3]],
                {"recovery_turn_count": len(recovery_turns)},
                "Compare the recovery attempt with the user's next turn to see whether it reduced confusion or merely prolonged the call.",
                time_window=TimeWindow(start_ms=recovery_turns[0].start_ms, end_ms=recovery_turns[-1].end_ms, label="agent recovery"),
            )
        )
    elif any(finding.category in {"friction_or_escalation", "answer_quality", "intent_resolution"} for finding in findings):
        risky_refs = _first_refs(findings, {"friction_or_escalation", "answer_quality", "intent_resolution"})
        findings.append(
            _finding(
                session_id,
                findings,
                "agent_recovery",
                "No clear agent recovery after risk signals",
                "watch",
                0.62,
                "The report found risk signals but no obvious apology, repair, confirmation, or next-step recovery turn.",
                "Without recovery, a single bad turn can become the user's final impression of the agent.",
                "The agent may not have a recovery policy or may not recognize when the human is stuck.",
                risky_refs,
                {"recovery_turn_count": 0},
                "Add or inspect recovery behavior for the first high-risk finding in this report.",
            )
        )

    if provider_enrichment:
        _merge_provider_enrichment(session_id, findings, provider_enrichment)

    findings = sorted(findings, key=lambda finding: (-SEVERITY_RANK[finding.severity], -finding.confidence, finding.finding_id))
    executive_summary = _executive_summary(findings, provider_enrichment, has_human_ai, quality)
    conversation_arc = _conversation_arc(turns, role_map, findings)
    human_experience = _human_experience_section(human_turns, latency_pairs, questions, findings)
    agent_behavior = _agent_behavior_section(ai_turns, latency_pairs, findings)
    context = _report_context(metadata, turns, speakers, quality, stage_status)

    return ConversationReport(
        executive_summary=executive_summary,
        findings=findings,
        conversation_arc=conversation_arc,
        human_experience=human_experience,
        agent_behavior=agent_behavior,
        trust_limits=trust_limits or _default_trust_limits(speaker_roles, diarization, quality, diagnostics),
        context=context,
    )


def _role_for_turn(turn: TurnModel, role_map: dict[str, SpeakerRole]) -> SpeakerRole:
    return role_map.get(turn.speaker_id, turn.speaker_role)


def _role_pairs(turns: list[TurnModel], role_map: dict[str, SpeakerRole], from_role: SpeakerRole, to_role: SpeakerRole) -> list[tuple[TurnModel, TurnModel]]:
    pairs: list[tuple[TurnModel, TurnModel]] = []
    for index, turn in enumerate(turns[:-1]):
        if _role_for_turn(turn, role_map) != from_role:
            continue
        for candidate in turns[index + 1 :]:
            candidate_role = _role_for_turn(candidate, role_map)
            if candidate_role == from_role:
                break
            if candidate_role == to_role:
                pairs.append((turn, candidate))
                break
    return pairs


def _finding(
    session_id: str,
    findings: list[ConversationReportFinding],
    category: ConversationReportCategory,
    title: str,
    severity: ReportSeverity,
    confidence: float,
    claim: str,
    impact: str,
    likely_cause: str,
    evidence_refs: list[EvidenceRef],
    related_metrics: dict[str, float | int | str | bool | None],
    suggested_next_check: str,
    *,
    time_window: TimeWindow | None = None,
    source: ReportFindingSource = "deterministic",
) -> ConversationReportFinding:
    return ConversationReportFinding(
        finding_id=f"{session_id}-finding-{len(findings) + 1}",
        category=category,
        title=title,
        severity=severity,
        confidence=max(0.0, min(1.0, round(confidence, 3))),
        claim=claim,
        impact=impact,
        likely_cause=likely_cause,
        time_window=time_window,
        evidence_refs=evidence_refs,
        related_metrics=related_metrics,
        suggested_next_check=suggested_next_check,
        source=source,
    )


def _confidence_from_turns(first: TurnModel, second: TurnModel, base: float) -> float:
    turn_confidence = mean([value for value in [first.confidence, second.confidence] if value is not None] or [0.65])
    return max(0.35, min(0.94, (base * 0.7) + (turn_confidence * 0.3)))


def _confidence_from_turn(turn: TurnModel, base: float) -> float:
    return max(0.35, min(0.9, (base * 0.75) + ((turn.confidence or 0.65) * 0.25)))


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _looks_like_request(turn_text: str) -> bool:
    lowered = turn_text.strip().lower()
    return "?" in lowered or lowered.startswith(("i need", "i want", "can you", "could you", "help", "please", "how do", "what", "why", "where", "when"))


def _answer_quality_risk(turn: TurnModel) -> bool:
    text = turn.text.strip().lower()
    return turn.word_count <= 5 or turn.uncertainty_markers > 0 or _contains_any(text, DEFLECTION_TERMS)


def _last_unresolved_human_turn(turns: list[TurnModel], role_map: dict[str, SpeakerRole]) -> TurnModel | None:
    for index in range(len(turns) - 1, -1, -1):
        turn = turns[index]
        if _role_for_turn(turn, role_map) != "human":
            continue
        if not _looks_like_request(turn.text) and not _contains_any(turn.text, ESCALATION_TERMS):
            return None
        later_ai = any(_role_for_turn(candidate, role_map) == "ai" for candidate in turns[index + 1 :])
        return None if later_ai else turn
    return None


def _turn_balance_gap(speakers: list[SpeakerSummary]) -> float | None:
    if len(speakers) < 2:
        return None
    ratios = sorted([speaker.talk_ratio for speaker in speakers], reverse=True)
    return max(0.0, ratios[0] - ratios[1])


def _signal(signals: list[SignalCard], key: str) -> SignalCard | None:
    return next((signal for signal in signals if signal.key == key), None)


def _signal_score(signal: SignalCard | None) -> int:
    return signal.score if signal else 0


def _signal_confidence(signal: SignalCard | None) -> float:
    return signal.confidence if signal else 0.0


def _first_refs(findings: list[ConversationReportFinding], categories: set[str]) -> list[EvidenceRef]:
    for finding in findings:
        if finding.category in categories and finding.evidence_refs:
            return finding.evidence_refs[:3]
    return []


def _merge_provider_enrichment(session_id: str, findings: list[ConversationReportFinding], enrichment: dict[str, Any]) -> None:
    confidence = float(enrichment.get("confidence") or 0.0)
    unresolved = [str(item) for item in enrichment.get("unresolved_intents", []) if str(item).strip()]
    likely_causes = [str(item) for item in enrichment.get("likely_causes", []) if str(item).strip()]
    if unresolved:
        findings.append(
            _finding(
                session_id,
                findings,
                "intent_resolution",
                "Provider analysis found unresolved intent",
                "risk",
                max(0.45, min(confidence, 0.82)),
                unresolved[0],
                "The user goal may not be fully closed even if the transcript has a final AI turn.",
                likely_causes[0] if likely_causes else "Provider analysis flagged unresolved intent without a stronger deterministic root cause.",
                [EvidenceRef(kind="provider_analysis", ref_id="openai_report_enrichment", label="unresolved intent")],
                {"provider_confidence": round(confidence, 3)},
                "Inspect this provider claim against the cited transcript context before turning it into a product decision.",
                source="provider" if confidence < 0.72 else "hybrid",
            )
        )
    elif likely_causes and findings:
        findings[0].likely_cause = f"{findings[0].likely_cause} Provider likely cause: {likely_causes[0]}"
        findings[0].source = "hybrid"


def _executive_summary(
    findings: list[ConversationReportFinding],
    enrichment: dict[str, Any],
    has_human_ai: bool,
    quality: QualitySummary,
) -> ConversationReportExecutiveSummary:
    risk_findings = [finding for finding in findings if finding.severity in {"critical", "risk"}]
    top_risks = [finding.title for finding in risk_findings[:5]]
    if enrichment.get("overall_diagnosis"):
        diagnosis = str(enrichment["overall_diagnosis"])
    elif not has_human_ai:
        diagnosis = "This session needs role review before it can be trusted as a human-AI diagnostic."
    elif risk_findings:
        diagnosis = f"The conversation needs product review: {risk_findings[0].claim}"
    elif findings:
        diagnosis = "The conversation is inspectable and has watch-level issues, but no critical breakdown was detected."
    else:
        diagnosis = "The conversation report found no major breakdown signals in the currently available evidence."

    if enrichment.get("call_outcome"):
        call_outcome = str(enrichment["call_outcome"])
    elif not quality.is_usable:
        call_outcome = "analysis_limited"
    elif risk_findings:
        call_outcome = "needs_product_review"
    elif findings:
        call_outcome = "completed_with_watch_items"
    else:
        call_outcome = "completed_no_major_breakdown"

    confidence_values = [finding.confidence for finding in findings[:8]]
    confidence = round(mean(confidence_values), 3) if confidence_values else (0.62 if has_human_ai else 0.35)
    next_action = risk_findings[0].suggested_next_check if risk_findings else "Use the report evidence to compare this call against the next agent version."
    return ConversationReportExecutiveSummary(
        overall_diagnosis=diagnosis,
        call_outcome=call_outcome,
        top_risks=top_risks,
        confidence=confidence,
        recommended_next_action=next_action,
    )


def _conversation_arc(turns: list[TurnModel], role_map: dict[str, SpeakerRole], findings: list[ConversationReportFinding]) -> list[ConversationReportSection]:
    if not turns:
        return [
            ConversationReportSection(
                label="Conversation arc",
                summary="No turn-level transcript is available yet.",
                confidence=0.0,
                details=["Run analysis with transcript timing to populate beginning, middle, and ending sections."],
            )
        ]
    duration_ms = max(turn.end_ms for turn in turns) or 1
    sections = [("Beginning", 0, duration_ms / 3), ("Middle", duration_ms / 3, (duration_ms / 3) * 2), ("End", (duration_ms / 3) * 2, duration_ms + 1)]
    arc: list[ConversationReportSection] = []
    for label, start_ms, end_ms in sections:
        section_turns = [turn for turn in turns if turn.start_ms < end_ms and turn.end_ms >= start_ms]
        section_findings = [finding for finding in findings if finding.time_window and finding.time_window.start_ms < end_ms and finding.time_window.end_ms >= start_ms]
        human_count = sum(1 for turn in section_turns if _role_for_turn(turn, role_map) == "human")
        ai_count = sum(1 for turn in section_turns if _role_for_turn(turn, role_map) == "ai")
        risk_titles = [finding.title for finding in section_findings if finding.severity in {"critical", "risk"}]
        summary = (
            f"{label} contains {human_count} human turns and {ai_count} AI turns"
            + (f"; main risk: {risk_titles[0]}." if risk_titles else "; no major risk finding is localized here.")
        )
        arc.append(
            ConversationReportSection(
                label=label,
                summary=summary,
                confidence=0.72 if section_turns else 0.3,
                evidence_refs=[EvidenceRef(kind="turn", ref_id=turn.turn_id) for turn in section_turns[:2]],
                details=[finding.claim for finding in section_findings[:3]],
            )
        )
    return arc


def _human_experience_section(
    human_turns: list[TurnModel],
    latency_pairs: list[tuple[TurnModel, TurnModel, int]],
    questions: list[QuestionAnalyticsRow],
    findings: list[ConversationReportFinding],
) -> ConversationReportSection:
    waits = [latency for _human, _ai, latency in latency_pairs]
    uncertainty_count = sum(1 for turn in human_turns if turn.uncertainty_markers or turn.filler_count)
    high_hesitation_count = sum(1 for question in questions if question.hesitation_score >= 60)
    avg_wait = round(mean(waits)) if waits else 0
    max_wait = max(waits) if waits else 0
    relevant = [finding for finding in findings if finding.category in {"human_wait", "human_uncertainty", "intent_resolution", "friction_or_escalation"}]
    return ConversationReportSection(
        label="Human experience",
        summary=f"The human experience shows {len(relevant)} report findings, {avg_wait} ms average agent-response wait, and {max_wait} ms max wait.",
        confidence=0.76 if human_turns else 0.25,
        evidence_refs=[ref for finding in relevant[:3] for ref in finding.evidence_refs[:1]],
        details=[
            f"Human turns: {len(human_turns)}",
            f"Human turns with uncertainty/fillers: {uncertainty_count}",
            f"High-hesitation question windows: {high_hesitation_count}",
        ],
    )


def _agent_behavior_section(
    ai_turns: list[TurnModel],
    latency_pairs: list[tuple[TurnModel, TurnModel, int]],
    findings: list[ConversationReportFinding],
) -> ConversationReportSection:
    waits = [latency for _human, _ai, latency in latency_pairs]
    recovery_count = sum(1 for turn in ai_turns if _contains_any(turn.text, RECOVERY_TERMS))
    weak_answer_count = sum(1 for turn in ai_turns if _answer_quality_risk(turn))
    relevant = [finding for finding in findings if finding.category in {"agent_latency", "answer_quality", "clarification_loop", "agent_recovery", "turn_taking"}]
    return ConversationReportSection(
        label="Agent behavior",
        summary=f"Agent behavior shows {len(relevant)} report findings across {len(ai_turns)} AI turns.",
        confidence=0.76 if ai_turns else 0.25,
        evidence_refs=[ref for finding in relevant[:3] for ref in finding.evidence_refs[:1]],
        details=[
            f"Average response latency after human turns: {round(mean(waits)) if waits else 0} ms",
            f"Weak or deflective AI turns: {weak_answer_count}",
            f"Recovery-like AI turns: {recovery_count}",
        ],
    )


def _default_trust_limits(
    speaker_roles: SpeakerRoleSummary,
    diarization: DiarizationSummary,
    quality: QualitySummary,
    diagnostics: Diagnostics,
) -> list[ConversationReportTrustLimit]:
    limits = [
        ConversationReportTrustLimit(
            key="role_confidence",
            label="Human/AI roles",
            severity="info",
            confidence=round(mean([assignment.confidence for assignment in speaker_roles.assignments] or [0.0]), 3),
            summary="Human and AI role assignment is available for report interpretation.",
            evidence_refs=[EvidenceRef(kind="speaker_roles", ref_id="speaker_roles")],
        ),
        ConversationReportTrustLimit(
            key="diarization",
            label="Speaker timing",
            severity="info" if diarization.readiness_state == "ready" else "watch",
            confidence=diarization.confidence,
            summary=f"Diarization is {diarization.readiness_state}.",
            evidence_refs=[EvidenceRef(kind="diarization", ref_id="diarization")],
        ),
    ]
    if diagnostics.degraded_reasons or quality.warning_flags:
        limits.append(
            ConversationReportTrustLimit(
                key="degraded_paths",
                label="Degraded analysis paths",
                severity="watch",
                confidence=0.72,
                summary=", ".join((diagnostics.degraded_reasons + quality.warning_flags)[:5]),
                evidence_refs=[EvidenceRef(kind="diagnostics", ref_id="diagnostics")],
            )
        )
    return limits


def _report_context(
    metadata: dict[str, Any],
    turns: list[TurnModel],
    speakers: list[SpeakerSummary],
    quality: QualitySummary,
    stage_status: list[StageStatus],
) -> dict[str, str | float | int | bool | None]:
    context_keys = [
        "call_scenario",
        "agent_version",
        "prompt_version",
        "expected_user_goal",
        "expected_successful_outcome",
        "known_failure_note",
        "human_speaker_hint",
        "ai_speaker_hint",
    ]
    context: dict[str, str | float | int | bool | None] = {key: str(metadata[key]) for key in context_keys if metadata.get(key)}
    context.update(
        {
            "turn_count": len(turns),
            "speaker_count": len(speakers),
            "quality_usable": quality.is_usable,
            "stage_count": len(stage_status),
        }
    )
    return context
