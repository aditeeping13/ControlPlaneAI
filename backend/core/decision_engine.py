from typing import List, Tuple
from backend.models.schemas import RiskSignal, RiskDetail

HARD_STOPS = ["api_key", "aadhaar", "credit_card", "bank_account"]

def evaluate_decision(
    signals: List[RiskSignal], 
    risk: RiskDetail, 
    decision_trace: List[str]
) -> Tuple[str, str, bool]:
    
    # 1. Hard Stops
    for signal in signals:
        if signal.executed and signal.detected:
            if signal.detector == "pii" and signal.affected_entity in HARD_STOPS and signal.confidence > 0.8:
                decision_trace.append(f"Hard stop violation: High-confidence {signal.affected_entity} exposure.")
                decision_trace.append("Action selected = BLOCK.")
                return "BLOCK", f"Hard stop violation: High-confidence {signal.affected_entity} exposure", False
            if signal.detector == "rule_threat":
                decision_trace.append(f"Hard stop violation: Rule/Threat detected ({signal.risk_type}).")
                decision_trace.append("Action selected = BLOCK.")
                return "BLOCK", f"Rule/Threat violation: {signal.risk_type}", False
                
    if risk.level == "CRITICAL":
        decision_trace.append("Critical risk score threshold met.")
        decision_trace.append("Action selected = BLOCK.")
        return "BLOCK", "Risk score is critical", False
        
    # Check for EDIT
    grounding_contradictions = [s for s in signals if s.executed and s.detected and s.detector == "grounding" and s.metadata.get("verdict") == "CONTRADICTED"]
    
    if grounding_contradictions:
        conf = max(s.confidence for s in grounding_contradictions)
        if conf >= 0.8:
            conf_str = "high confidence"
        elif conf >= 0.6:
            conf_str = "moderate confidence"
        else:
            conf_str = "low confidence"
            
        decision_trace.append(f"Contradiction has {conf_str}, authoritative evidence is available, and the response is repairable.")
        decision_trace.append("Action selected = EDIT.")
        return "EDIT", "Authoritative evidence contradicts the AI response. Safely repairable.", False
        
    # Check for REVIEW
    ai_judge_signals = [s for s in signals if s.executed and s.detected and s.detector == "ai_judge"]
    
    if risk.level == "HIGH":
        decision_trace.append("High risk score without repairability requires human review.")
        decision_trace.append("Action selected = REVIEW.")
        return "REVIEW", "High risk score requires human review", True
        
    ai_judge_failed = any(s.metadata.get("status") in ["FAILED_REQUIRED_CHECK", "RATE_LIMITED"] for s in signals if s.detector == "ai_judge")
    if ai_judge_failed:
        has_rate_limit = any(s.metadata.get("status") == "RATE_LIMITED" for s in signals if s.detector == "ai_judge")
        if has_rate_limit:
            decision_trace.append("Required semantic verification could not be completed because the LLM provider was rate-limited. Escalated for human review.")
        else:
            decision_trace.append("Required semantic verification could not be completed. Escalated for human review.")
        decision_trace.append("Action selected = REVIEW.")
        return "REVIEW", "Required semantic verification could not be completed.", True
        
    if ai_judge_signals:
        decision_trace.append("Potential bias or semantic violation detected.")
        decision_trace.append("Action selected = REVIEW.")
        return "REVIEW", "Potential bias or semantic violation detected", True
        
    for s in signals:
        if s.executed and s.detected and s.severity > 0.5 and s.confidence < 0.8:
            decision_trace.append(f"Moderate confidence risk ({s.risk_type}) requires review.")
            decision_trace.append("Action selected = REVIEW.")
            return "REVIEW", f"Moderate confidence risk ({s.risk_type}) requires review", True
            
    # Default
    decision_trace.append("No significant risks requiring intervention.")
    decision_trace.append("Action selected = ALLOW.")
    return "ALLOW", "Low risk and no hard-stop violation", False
