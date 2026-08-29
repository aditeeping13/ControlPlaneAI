from backend.models.schemas import AnalyzeRequest, InitialRiskDetail, InitialRiskFactors, InitialRiskFactor, RoutingPolicy
import os

def evaluate_initial_risk(request: AnalyzeRequest) -> tuple[InitialRiskDetail, RoutingPolicy]:
    # 1. Exposure (max 20)
    if request.audience == "external":
        exposure = InitialRiskFactor(score=20, max=20, reason="Customer-facing external audience")
    elif request.audience == "internal" and request.actor_role in ["employee", "manager"]:
        exposure = InitialRiskFactor(score=10, max=20, reason="Internal team/audience")
    else:
        exposure = InitialRiskFactor(score=5, max=20, reason="Single internal user")

    # 2. Data Sensitivity (max 25)
    prompt_lower = request.prompt.lower()
    if any(k in prompt_lower for k in ["aadhaar", "ssn", "password", "api_key", "secret", "credit card"]):
        data_sens = InitialRiskFactor(score=25, max=25, reason="Highly sensitive personal data or secrets detected")
    elif request.use_case in ["hr", "finance"]:
        data_sens = InitialRiskFactor(score=15, max=25, reason="Internal HR or Finance data")
    else:
        data_sens = InitialRiskFactor(score=5, max=25, reason="No highly sensitive data patterns detected")

    # 3. Business Impact (max 25)
    if request.use_case == "customer_support":
        impact = InitialRiskFactor(score=20, max=25, reason="Incorrect answer may create customer financial impact")
    elif request.use_case in ["hr", "finance"]:
        impact = InitialRiskFactor(score=25, max=25, reason="Regulated or high-impact internal decision")
    else:
        impact = InitialRiskFactor(score=5, max=25, reason="General FAQ, low business impact")

    # 4. Failure Likelihood (max 20)
    if any(k in prompt_lower for k in ["ignore", "forget", "override", "bypass"]):
        failure = InitialRiskFactor(score=20, max=20, reason="Prompt contains override or injection patterns")
    elif "policy" in prompt_lower or request.use_case == "hr" or "refund" in prompt_lower:
        failure = InitialRiskFactor(score=15, max=20, reason="Company-policy-dependent request with semantic complexity")
    else:
        failure = InitialRiskFactor(score=5, max=20, reason="Standard query pattern")

    # 5. Uncertainty (max 10)
    if request.use_case == "general_internal" and "aadhaar" not in prompt_lower:
        uncert = InitialRiskFactor(score=2, max=10, reason="Easy deterministic answer")
    else:
        uncert = InitialRiskFactor(score=10, max=10, reason="Requires verification against enterprise evidence")

    total_score = exposure.score + data_sens.score + impact.score + failure.score + uncert.score
    
    if total_score < 25:
        level = "LOW"
        tier = "ECONOMY"
        depth = "LIGHT"
    elif total_score < 50:
        level = "MEDIUM"
        tier = "STANDARD"
        depth = "STANDARD"
    elif total_score < 75:
        level = "HIGH"
        tier = "PREMIUM"
        depth = "DEEP"
    else:
        level = "CRITICAL"
        tier = "PREMIUM"
        depth = "DEEP"

    risk_detail = InitialRiskDetail(
        score=total_score,
        level=level,
        factors=InitialRiskFactors(
            exposure=exposure,
            data_sensitivity=data_sens,
            business_impact=impact,
            failure_likelihood=failure,
            uncertainty=uncert
        )
    )

    actual_model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    routing = RoutingPolicy(
        recommended_tier=tier,
        verification_depth=depth,
        routing_mode="single_model_poc",
        actual_model=actual_model
    )

    return risk_detail, routing
