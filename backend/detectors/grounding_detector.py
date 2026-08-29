import re
from typing import List
from backend.services.retrieval_service import retrieval_service
from backend.models.schemas import RiskSignal

def evaluate_grounding(claim: str) -> RiskSignal:
    results = retrieval_service.retrieve_relevant_chunks(claim, top_k=2)
    
    if not results:
        return RiskSignal(
            detector="grounding_detector",
            risk_type="hallucination",
            detected=False,
            severity=0.0,
            confidence=1.0,
            evidence=[],
            affected_claim=claim,
            metadata={"verdict": "INSUFFICIENT_EVIDENCE"}
        )
        
    combined_evidence = " ".join([res[0] for res in results])
    
    claim_numbers = set(re.findall(r'\b\d+\b', claim))
    evidence_numbers = set(re.findall(r'\b\d+\b', combined_evidence))
    
    unsupported_numbers = claim_numbers - evidence_numbers
    
    if unsupported_numbers:
        verdict = "CONTRADICTED"
        detected = True
        severity = 0.8
        confidence = 0.7
    else:
        verdict = "SUPPORTED" if claim_numbers else "UNSUPPORTED"
        detected = verdict == "UNSUPPORTED"
        severity = 0.4 if detected else 0.0
        confidence = 0.5
        
    return RiskSignal(
        detector="grounding",
        risk_type="hallucination",
        detected=detected,
        severity=severity,
        confidence=confidence,
        evidence=[res[0] for res in results],
        affected_claim=claim,
        repairable=True if verdict == "CONTRADICTED" else False,
        metadata={"verdict": verdict, "sources": list(dict.fromkeys(res[1] for res in results))}
    )
