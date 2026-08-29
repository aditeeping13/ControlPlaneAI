from typing import List, Tuple, Dict
from pydantic import BaseModel
from backend.models.schemas import AnalyzeRequest, RiskSignal, ExecutedCheck, SkippedCheck, RoutingPolicy
from backend.detectors.pii_detector import detect_pii
from backend.detectors.grounding_detector import evaluate_grounding
from backend.detectors.ai_judge import evaluate_semantic_risk
from backend.detectors.rule_threat_detector import RuleThreatDetector
import time

class VerificationPlan(BaseModel):
    rule_threat: bool
    pii: bool
    grounding: bool
    ai_judge: bool
    grounding_reason: str = ""
    ai_judge_reason: str = ""
    benchmark_mode: str = ""

def create_verification_plan(request: AnalyzeRequest, depth: str) -> VerificationPlan:
    plan = VerificationPlan(rule_threat=True, pii=True, grounding=False, ai_judge=False)
    
    prompt_lower = request.prompt.lower()
    policy_keywords = ["refund", "policy", "expense", "rules", "guidelines", "hours"]
    
    # Grounding Relevance
    if request.use_case in ["customer_support", "hr", "finance"] or any(k in prompt_lower for k in policy_keywords):
        plan.grounding = True
        plan.grounding_reason = "Policy keywords or relevant use-case detected."
    else:
        plan.grounding_reason = "No policy keywords or relevant use-case detected."
        
    # AI Judge Relevance
    bias_keywords = ["gender", "race", "age", "candidate", "hire", "promotion", "female", "women", "men", "male", "maternity"]
    if depth in ["STANDARD", "DEEP"]:
        if request.use_case == "hr" or any(k in prompt_lower for k in bias_keywords):
            plan.ai_judge = True
            plan.ai_judge_reason = "Semantic ambiguity or HR bias context detected."
        else:
            plan.ai_judge_reason = "No semantic-risk trigger detected."
    else:
        plan.ai_judge_reason = f"AI Judge skipped for Verification Depth: {depth}."
        
    return plan

def execute_verification_plan(request: AnalyzeRequest, ai_response: str, plan: VerificationPlan) -> Tuple[List[RiskSignal], List[ExecutedCheck], List[SkippedCheck], List[str], Dict[str, float]]:
    signals = []
    checks_executed = []
    checks_skipped = []
    decision_trace = []
    latencies = {}
    
    combined_text = request.prompt + " " + ai_response
    early_stop_triggered = False
    
    # 1. Rule / Threat Detector
    if plan.rule_threat:
        start = time.time()
        rule_detector = RuleThreatDetector()
        rule_signal = rule_detector.analyze(request.prompt)
        latencies["rule_threat"] = (time.time() - start) * 1000
        
        signals.append(rule_signal)
        checks_executed.append(ExecutedCheck(detector="rule_threat"))
        
        if rule_signal.detected:
            decision_trace.append("Rule/Threat detector found violation.")
            if plan.benchmark_mode != "benchmark_baseline":
                early_stop_triggered = True
        else:
            decision_trace.append("Rule/Threat detector clear.")
            
    # 2. PII Detector
    if plan.pii and not early_stop_triggered:
        start = time.time()
        pii_signals = detect_pii(combined_text)
        latencies["pii"] = (time.time() - start) * 1000
        
        signals.extend(pii_signals)
        checks_executed.append(ExecutedCheck(detector="pii"))
        
        critical_pii = any(s.detected and s.severity >= 0.9 for s in pii_signals)
        if critical_pii:
            decision_trace.append("PII detector found critical exposure (hard stop).")
            if plan.benchmark_mode != "benchmark_baseline":
                early_stop_triggered = True
        elif any(s.detected for s in pii_signals):
            decision_trace.append("PII detector found potential exposure.")
        else:
            decision_trace.append("PII detector clear.")
    elif early_stop_triggered:
        checks_skipped.append(SkippedCheck(detector="pii", reason="Early stop triggered by previous critical violation."))
        signals.append(RiskSignal(detector="pii", executed=False, skip_reason="Early stop triggered by previous critical violation."))

    # 3. Grounding Detector
    if plan.grounding and not early_stop_triggered:
        start = time.time()
        grounding_signal = evaluate_grounding(ai_response)
        latencies["grounding"] = (time.time() - start) * 1000
        
        signals.append(grounding_signal)
        checks_executed.append(ExecutedCheck(detector="grounding"))
        
        verdict = grounding_signal.metadata.get('verdict', 'unknown')
        if verdict == "CONTRADICTED":
            decision_trace.append("Grounding detector found authoritative contradiction.")
        else:
            decision_trace.append(f"Grounding detector evaluated claim: {verdict}.")
    else:
        reason = "Early stop triggered by previous critical violation." if early_stop_triggered else plan.grounding_reason
        checks_skipped.append(SkippedCheck(detector="grounding", reason=reason))
        signals.append(RiskSignal(detector="grounding", executed=False, skip_reason=reason))
        
    # 4. AI-as-Judge
    if plan.ai_judge and not early_stop_triggered:
        start = time.time()
        judge_signals = evaluate_semantic_risk(request.prompt, ai_response)
        latencies["ai_judge"] = (time.time() - start) * 1000
        
        signals.extend(judge_signals)
        checks_executed.append(ExecutedCheck(detector="ai_judge"))
        
        has_rate_limit = any(s.metadata.get("status") == "RATE_LIMITED" for s in judge_signals)
        has_error = any(s.metadata.get("status") == "ERROR" for s in judge_signals)
        
        if has_rate_limit:
            decision_trace.append("Required semantic verification could not be completed because the LLM provider was rate-limited. Escalated for human review.")
        elif has_error:
            for s in judge_signals:
                if s.metadata.get("status") == "ERROR":
                    s.metadata["status"] = "FAILED_REQUIRED_CHECK"
            decision_trace.append("AI judge execution failed or returned malformed output.")
        elif any(s.detected for s in judge_signals):
            decision_trace.append("AI judge found potential semantic risk.")
        else:
            decision_trace.append("AI judge clear.")
    else:
        reason = "Early stop triggered by previous critical violation." if early_stop_triggered else plan.ai_judge_reason
        checks_skipped.append(SkippedCheck(detector="ai_judge", reason=reason))
        signals.append(RiskSignal(detector="ai_judge", executed=False, skip_reason=reason))

    return signals, checks_executed, checks_skipped, decision_trace, latencies
