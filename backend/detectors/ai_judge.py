from typing import List
from backend.models.schemas import RiskSignal, AIJudgeOutput
from backend.services.llm_service import evaluate_semantic_risk as llm_eval

def evaluate_semantic_risk(prompt: str, ai_response: str) -> List[RiskSignal]:
    signals = []
    
    parsed_data, tokens = llm_eval(prompt, ai_response)
    # tokens is now a dict like {"total": x, "input": y, "output": z}
    total_tokens = tokens.get("total", 0) if isinstance(tokens, dict) else tokens
    
    original_parsed = parsed_data
    if parsed_data:
        try:
            judge_output = AIJudgeOutput(**parsed_data)
            if judge_output.detected:
                signals.append(RiskSignal(
                    detector="ai_judge",
                    risk_type=judge_output.risk_type,
                    detected=judge_output.detected,
                    severity=judge_output.severity,
                    confidence=judge_output.confidence,
                    evidence=[judge_output.reason],
                    affected_claim=judge_output.affected_claim,
                    repairable=False,
                    metadata={"reason": judge_output.reason, "tokens": total_tokens, "token_dict": tokens}
                ))
        except Exception:
            parsed_data = None
            
    if not signals:
        status = "SUCCESS"
        if parsed_data is None:
            status = "ERROR"
        if isinstance(original_parsed, dict):
            if original_parsed.get("status") == "RATE_LIMITED":
                status = "RATE_LIMITED"
            elif original_parsed.get("status") == "PROVIDER_UNAVAILABLE":
                status = "PROVIDER_UNAVAILABLE"
            
        signals.append(RiskSignal(
            detector="ai_judge",
            executed=True,
            detected=False,
            severity=0.0,
            confidence=1.0,
            evidence=[],
            metadata={
                "tokens": total_tokens,
                "token_dict": tokens,
                "status": status,
                "retry_after": original_parsed.get("retry_after_seconds") if isinstance(original_parsed, dict) else None
            }
        ))
        
    return signals
