from backend.models.schemas import RiskSignal
import re

class RuleThreatDetector:
    def __init__(self):
        self.threat_patterns = [
            (r"(?i)\bignore\s+(previous\s+)?instructions\b", "instruction_override"),
            (r"(?i)\bforget\s+(previous\s+)?rules\b", "instruction_override"),
            (r"(?i)reveal\s+(your\s+)?system\s+prompt", "prompt_leak"),
            (r"(?i)override\s+(all\s+)?restrictions", "policy_bypass"),
            (r"(?i)bypass\s+policy", "policy_bypass"),
            (r"(?i)act\s+as\s+(an\s+)?unrestricted\s+ai", "jailbreak")
        ]
        
    def analyze(self, prompt: str) -> RiskSignal:
        signal = RiskSignal(
            detector="rule_threat",
            executed=True,
            risk_type="none",
            detected=False,
            severity=0.0,
            confidence=1.0,
            evidence=[]
        )
        
        for pattern, risk_type in self.threat_patterns:
            if re.search(pattern, prompt):
                signal.detected = True
                signal.risk_type = risk_type
                signal.severity = 0.9
                signal.confidence = 1.0
                signal.evidence.append(f"Matched threat pattern: {pattern}")
                break
                
        return signal
