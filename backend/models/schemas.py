from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class AnalyzeRequest(BaseModel):
    prompt: str
    use_case: str
    actor_role: str
    audience: str
    ai_response: Optional[str] = None
    benchmark_mode: Optional[str] = None

class RiskSignal(BaseModel):
    detector: str
    executed: bool = True
    risk_type: str = "none"
    detected: bool = False
    severity: float = 0.0
    confidence: float = 1.0
    evidence: List[str] = []
    affected_claim: Optional[str] = None
    affected_entity: Optional[str] = None
    repairable: bool = False
    metadata: Dict[str, Any] = {}
    skip_reason: Optional[str] = None

class AIJudgeOutput(BaseModel):
    detected: bool
    risk_type: str
    severity: float
    confidence: float
    reason: str
    affected_claim: str

class RiskBreakdown(BaseModel):
    primary_signal: float
    secondary_contribution: float
    overlap_bonus: float
    business_impact_modifier: float

class RiskDetail(BaseModel):
    score: float
    level: str
    breakdown: RiskBreakdown
    primary_risk: Optional[str] = None
    risk_factors: List[str]

class ExecutedCheck(BaseModel):
    detector: str

class SkippedCheck(BaseModel):
    detector: str
    reason: str

class InitialRiskFactor(BaseModel):
    score: int
    max: int
    reason: str

class InitialRiskFactors(BaseModel):
    exposure: InitialRiskFactor
    data_sensitivity: InitialRiskFactor
    business_impact: InitialRiskFactor
    failure_likelihood: InitialRiskFactor
    uncertainty: InitialRiskFactor

class InitialRiskDetail(BaseModel):
    score: int
    level: str
    factors: InitialRiskFactors

class RoutingPolicy(BaseModel):
    recommended_tier: str
    verification_depth: str
    routing_mode: str
    actual_model: str

class TelemetryData(BaseModel):
    primary_llm_calls: int
    primary_llm_calls_avoided: int = 0
    secondary_judge_calls: int
    secondary_llm_calls_avoided: int
    avoided_latency_ms: Optional[float] = None
    actual_api_cost: Optional[float] = None
    avoided_api_cost: Optional[float] = None
    latency: Dict[str, float]
    total_input_tokens: Optional[int] = None
    total_output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    provider_call_attempted: int = 0
    provider_call_succeeded: int = 0
    provider_rate_limited: int = 0
    fallback_used: int = 0
    retry_after_seconds: Optional[int] = None
    call_type_history: List[str] = []

class AnalyzeResponse(BaseModel):
    request_id: str
    input: str
    raw_ai_response: Optional[str] = None
    response_source: str
    initial_risk: InitialRiskDetail
    routing_policy: RoutingPolicy
    detector_results: List[RiskSignal]
    risk: RiskDetail
    decision: str
    decision_reason: str
    decision_trace: List[str]
    human_review_required: bool
    final_response: Optional[str] = None
    checks_executed: List[ExecutedCheck]
    checks_skipped: List[SkippedCheck]
    telemetry: TelemetryData
