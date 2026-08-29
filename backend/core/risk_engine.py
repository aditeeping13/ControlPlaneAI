from typing import List, Tuple
from backend.models.schemas import RiskSignal, RiskDetail, RiskBreakdown

CONTEXT_MODIFIERS = {
    "general_internal": 0,
    "customer_support": 4,
    "hr": 6,
    "finance": 8,
    "regulated_decision_support": 10
}

def calculate_risk(signals: List[RiskSignal], use_case: str, decision_trace: List[str]) -> RiskDetail:
    active_signals = [s for s in signals if s.executed and s.detected]
    
    if not active_signals:
        decision_trace.append("No risks detected. Base risk = 0.")
        return RiskDetail(
            score=0.0,
            level="LOW",
            breakdown=RiskBreakdown(primary_signal=0.0, secondary_contribution=0.0, overlap_bonus=0.0, business_impact_modifier=0.0),
            primary_risk=None,
            risk_factors=[]
        )

    scores = [s.severity * s.confidence * 100 for s in active_signals]
    
    primary_idx = scores.index(max(scores))
    primary_signal = active_signals[primary_idx]
    primary_score = scores[primary_idx]
    primary_risk_type = primary_signal.risk_type
    decision_trace.append(f"Primary {primary_risk_type} risk = {primary_score:.1f}.")
    
    other_scores = sum(scores) - primary_score
    secondary_score = min(15.0, 0.20 * other_scores)
    if secondary_score > 0:
        decision_trace.append(f"Secondary risks contribution = {secondary_score:.1f}.")
    
    overlap_bonus = 0.0
    pii_signals = [s for s in active_signals if s.detector == "pii_detector"]
    grounding_signals = [s for s in active_signals if s.detector == "grounding_detector"]
    
    for p_sig in pii_signals:
        for g_sig in grounding_signals:
            if p_sig.evidence and g_sig.affected_claim:
                if any(ev in g_sig.affected_claim for ev in p_sig.evidence):
                    overlap_bonus = 10.0
                    decision_trace.append(f"Cross-risk overlap bonus = {overlap_bonus:.1f}.")
                    break

    business_impact_modifier = CONTEXT_MODIFIERS.get(use_case, 0)
    if business_impact_modifier > 0:
        decision_trace.append(f"Impact modifier ({use_case}) = {business_impact_modifier}.")
    
    # The final score must mathematically match
    raw_final = primary_score + secondary_score + overlap_bonus + business_impact_modifier
    if raw_final > 100.0:
        scale = 100.0 / raw_final
        primary_score *= scale
        secondary_score *= scale
        overlap_bonus *= scale
        business_impact_modifier *= scale
            
    final_score = primary_score + secondary_score + overlap_bonus + business_impact_modifier
    decision_trace.append(f"Final risk calculated = {final_score:.1f}.")
    
    if final_score < 25:
        level = "LOW"
    elif final_score < 50:
        level = "MEDIUM"
    elif final_score < 75:
        level = "HIGH"
    else:
        level = "CRITICAL"
        
    decision_trace.append(f"Risk level evaluated as {level}.")
        
    risk_factors = [s.risk_type for s in active_signals]
    if grounding_signals:
        risk_factors.append("Grounding contradiction detected")
    if use_case in ["customer_support", "hr", "finance"]:
        risk_factors.append(f"Customer-facing interaction")
        
    breakdown = RiskBreakdown(
        primary_signal=primary_score,
        secondary_contribution=secondary_score,
        overlap_bonus=overlap_bonus,
        business_impact_modifier=business_impact_modifier
    )
    
    return RiskDetail(
        score=final_score,
        level=level,
        breakdown=breakdown,
        primary_risk=primary_risk_type,
        risk_factors=list(set(risk_factors))
    )
