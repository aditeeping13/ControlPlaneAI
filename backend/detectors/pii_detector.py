import re
from typing import List
from backend.models.schemas import RiskSignal

PII_PATTERNS = {
    "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "phone": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
    "api_key": r"(?i)(?:key|api|token|secret)[=:]\s*[\"']?([a-zA-Z0-9_\-]{16,})[\"']?",
    "bank_account": r"(?i)(?:account|acct|acc)(?:\s*number|#)?[:\s]*(\d{8,18})"
}

def detect_pii(text: str) -> List[RiskSignal]:
    signals = []
    
    if not text:
        return [RiskSignal(detector="pii", executed=True, detected=False, severity=0.0, confidence=1.0, evidence=[])]
        
    for entity_type, pattern in PII_PATTERNS.items():
        matches = re.finditer(pattern, text)
        for match in matches:
            matched_text = match.group(0)
            
            severity = 0.5
            if entity_type in ["aadhaar", "credit_card", "api_key", "bank_account"]:
                severity = 1.0 
            elif entity_type in ["email", "phone"]:
                severity = 0.7

            signal = RiskSignal(
                detector="pii",
                risk_type="pii_exposure",
                detected=True,
                severity=severity,
                confidence=0.9,
                evidence=[matched_text],
                affected_entity=entity_type,
                repairable=True
            )
            signals.append(signal)
            
    if not signals:
        signals.append(RiskSignal(
            detector="pii",
            executed=True,
            detected=False,
            severity=0.0,
            confidence=1.0,
            evidence=[]
        ))
            
    return signals
