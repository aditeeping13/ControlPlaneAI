import time
import uuid
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.models.schemas import AnalyzeRequest, AnalyzeResponse, RiskSignal, TelemetryData, ExecutedCheck, SkippedCheck
from backend.core.initial_risk import evaluate_initial_risk
from backend.core.router import create_verification_plan, execute_verification_plan
from backend.core.risk_engine import calculate_risk
from backend.core.decision_engine import evaluate_decision
from backend.services.llm_service import generate_response, generate_corrected_response
from backend.services.audit_service import log_audit

app = FastAPI(title="ControlPlane.ai MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory historical averages for telemetry (Note: This is strictly in-memory and resets on restart)
historical_latencies = {
    "rule_threat": [],
    "pii": [],
    "grounding": [],
    "ai_judge": [],
    "primary_llm": []
}
historical_tokens = {
    "ai_judge": []
}

def get_average(history_list):
    if not history_list:
        return None
    return sum(history_list) / len(history_list)

COST_PER_TOKEN = 0.000002

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    latency_tracker = {}
    
    # 1. Initial Risk & Routing Policy
    t0 = time.time()
    initial_risk, routing_policy = evaluate_initial_risk(request)
    latency_tracker["initial_risk_latency"] = (time.time() - t0) * 1000
    
    # 2. Verification Plan
    t1 = time.time()
    plan = create_verification_plan(request, routing_policy.verification_depth)
    
    if request.benchmark_mode == "benchmark_baseline":
        plan.rule_threat = True
        plan.pii = True
        
        prompt_lower = request.prompt.lower()
        policy_keywords = ["refund", "policy", "expense", "rules", "guidelines", "hours"]
        if request.use_case in ["customer_support", "hr", "finance"] or any(k in prompt_lower for k in policy_keywords):
            plan.grounding = True
            plan.grounding_reason = "Benchmark baseline forced grounding (applicable)."
        else:
            plan.grounding = False
            plan.grounding_reason = "No policy keywords or relevant use-case detected (inapplicable)."
            
        plan.ai_judge = True
        plan.ai_judge_reason = "Always-On Verification Baseline (executes on all generated responses)."
        
        plan.benchmark_mode = "benchmark_baseline"
        
    latency_tracker["routing_latency"] = (time.time() - t1) * 1000
    
    # 3. Cheap Preflight Hard-Stop
    t_pre = time.time()
    preflight_signals = []
    preflight_checks_executed = []
    exec_latencies = {}
    hard_stop_triggered = False
    
    from backend.detectors.rule_threat_detector import RuleThreatDetector
    from backend.detectors.pii_detector import detect_pii
    
    if plan.rule_threat:
        start_rt = time.time()
        rule_detector = RuleThreatDetector()
        rule_signal = rule_detector.analyze(request.prompt)
        exec_latencies["rule_threat_preflight"] = (time.time() - start_rt) * 1000
        preflight_signals.append(rule_signal)
        preflight_checks_executed.append("rule_threat")
        if rule_signal.detected and request.benchmark_mode != "benchmark_baseline":
            hard_stop_triggered = True
            
    if plan.pii and not hard_stop_triggered:
        start_pii = time.time()
        pii_signals = detect_pii(request.prompt)
        exec_latencies["pii_preflight"] = (time.time() - start_pii) * 1000
        preflight_signals.extend(pii_signals)
        preflight_checks_executed.append("pii")
        critical_pii = any(s.detected and s.severity >= 0.9 for s in pii_signals)
        if critical_pii and request.benchmark_mode != "benchmark_baseline":
            hard_stop_triggered = True

    latency_tracker["preflight_latency"] = (time.time() - t_pre) * 1000

    ai_response = request.ai_response
    primary_llm_calls = 0
    primary_tokens = 0
    primary_llm_calls_avoided = 0

    if hard_stop_triggered:
        # Avoid generation!
        primary_llm_calls_avoided = 1 if not request.ai_response else 0
        response_source = "primary_llm_skipped"
        latency_tracker["primary_llm_latency"] = 0.0
        
        # Build immediate decision context
        signals = preflight_signals
        checks_executed = [ExecutedCheck(detector=c) for c in preflight_checks_executed]
        checks_skipped = []
        if plan.grounding:
            checks_skipped.append(SkippedCheck(detector="grounding", reason="Critical deterministic preflight violation established before generation."))
        if plan.ai_judge:
            checks_skipped.append(SkippedCheck(detector="ai_judge", reason="Critical deterministic preflight violation established before generation."))
            
        decision_trace = ["Critical deterministic preflight violation established before generation."]
        latency_tracker["detection_total_latency"] = latency_tracker["preflight_latency"]
        
        # We don't need to run `execute_verification_plan` since we hard stopped.
    else:
        # 4. Primary LLM Generation
        t2 = time.time()
        if not ai_response:
            ai_response, primary_tokens = generate_response(request.prompt, request.use_case)
            
            is_demo_safe = os.environ.get("DEMO_SAFE_MODE", "true").lower() == "true"
            if isinstance(ai_response, dict) and ai_response.get("error_type") == "RATE_LIMITED" and is_demo_safe:
                response_source = "fallback_rate_limited"
                retry_after = ai_response.get("retry_after_seconds")
                ai_response = "Placeholder response: Gemini rate limit exceeded. Please use demo scenarios or try again later."
                primary_llm_calls = 0
            elif isinstance(ai_response, dict) and ai_response.get("error_type") == "RATE_LIMITED":
                response_source = "primary_llm_error"
                ai_response = "Error: Gemini rate limit exceeded."
                primary_llm_calls = 1
            else:
                response_source = "primary_llm"
                primary_llm_calls = 1
        else:
            response_source = "supplied_ai_response"
            
        latency_tracker["primary_llm_latency"] = (time.time() - t2) * 1000 if response_source == "primary_llm" else 0.0
        
        # 5. Execute Verification Plan (normal post-generation)
        t3 = time.time()
        signals, checks_executed, checks_skipped, decision_trace, exec_lats = execute_verification_plan(request, ai_response, plan)
        for k, v in exec_lats.items():
            exec_latencies[k] = v
        latency_tracker["detection_total_latency"] = (time.time() - t3) * 1000
    
    # 5. Risk Fusion
    t4 = time.time()
    risk_detail = calculate_risk(signals, request.use_case, decision_trace)
    latency_tracker["risk_fusion_latency"] = (time.time() - t4) * 1000
    
    # 6. Decision Engine
    t5 = time.time()
    decision, decision_reason, human_review_required = evaluate_decision(signals, risk_detail, decision_trace)
    
    final_response = ai_response
    if decision == "EDIT":
        evidence = ""
        for s in signals:
            if s.executed and s.detected and s.detector == "grounding" and s.evidence:
                evidence = " ".join(s.evidence)
                break
        t6 = time.time()
        final_response = generate_corrected_response(ai_response, evidence)
        latency_tracker["correction_latency"] = (time.time() - t6) * 1000
    elif decision == "BLOCK":
        final_response = "Response blocked due to policy violations."
    elif decision == "REVIEW":
        final_response = "Response pending human review."
        
    latency_tracker["decision_engine_latency"] = (time.time() - t5) * 1000
    latency_tracker["total_latency"] = (time.time() - start_time) * 1000
    
    # Update dynamic history
    for k, v in exec_latencies.items():
        if k in historical_latencies:
            historical_latencies[k].append(v)
            if len(historical_latencies[k]) > 100:  # Keep last 100
                historical_latencies[k].pop(0)
                
    if latency_tracker.get("primary_llm_latency", 0) > 0 and response_source == "primary_llm":
        historical_latencies["primary_llm"].append(latency_tracker["primary_llm_latency"])
        if len(historical_latencies["primary_llm"]) > 100:
            historical_latencies["primary_llm"].pop(0)

    for s in signals:
        if s.detector == "ai_judge" and "tokens" in s.metadata and s.metadata["tokens"] > 0:
            historical_tokens["ai_judge"].append(s.metadata["tokens"])
            if len(historical_tokens["ai_judge"]) > 100:
                historical_tokens["ai_judge"].pop(0)

    # Telemetry Calculations
    secondary_judge_calls = 1 if any(c.detector == "ai_judge" for c in checks_executed) else 0
    avoided_judge = 1 if (not plan.ai_judge) or any(c.detector == "ai_judge" for c in checks_skipped) else 0
    
    avoided_latency = 0.0
    has_full_latency_history = True
    for c in checks_skipped:
        avg_lat = get_average(historical_latencies.get(c.detector, []))
        if avg_lat is not None:
            avoided_latency += avg_lat
        else:
            has_full_latency_history = False
            
    if primary_llm_calls_avoided > 0:
        avg_llm_lat = get_average(historical_latencies.get("primary_llm", []))
        if avg_llm_lat is not None:
            avoided_latency += avg_llm_lat
        else:
            has_full_latency_history = False
            
    total_tokens = 0
    total_input_tokens = 0
    total_output_tokens = 0
    
    if isinstance(primary_tokens, dict):
        total_tokens += primary_tokens.get("total", 0)
        total_input_tokens += primary_tokens.get("input", 0)
        total_output_tokens += primary_tokens.get("output", 0)
    else:
        total_tokens += primary_tokens

    for s in signals:
        if s.detector == "ai_judge" and "token_dict" in s.metadata:
            td = s.metadata["token_dict"]
            if isinstance(td, dict):
                total_tokens += td.get("total", 0)
                total_input_tokens += td.get("input", 0)
                total_output_tokens += td.get("output", 0)
        elif s.detector == "ai_judge" and "tokens" in s.metadata:
            total_tokens += s.metadata["tokens"]
            
    actual_api_cost = total_tokens * COST_PER_TOKEN if primary_llm_calls > 0 else 0.0
    
    avoided_cost = 0.0
    has_full_cost_history = True
    if avoided_judge > 0:
        avg_tok = get_average(historical_tokens.get("ai_judge", []))
        if avg_tok is not None:
            avoided_cost += avg_tok * COST_PER_TOKEN
        else:
            has_full_cost_history = False
    
    provider_call_attempted = 0
    provider_call_succeeded = 0
    provider_rate_limited = 0
    fallback_used = 1 if response_source == "fallback_rate_limited" else 0
    retry_after_seconds = None
    call_type_history = []
    
    if response_source in ["primary_llm", "fallback_rate_limited"]:
        provider_call_attempted += 1
        call_type_history.append("primary_generation")
        if response_source == "primary_llm":
            provider_call_succeeded += 1
        elif response_source == "fallback_rate_limited":
            provider_rate_limited += 1
            if 'retry_after' in locals() and retry_after is not None:
                retry_after_seconds = retry_after
                
    for s in signals:
        if s.detector == "ai_judge" and s.executed:
            provider_call_attempted += 1
            call_type_history.append("ai_judge")
            if s.metadata.get("status") == "RATE_LIMITED":
                provider_rate_limited += 1
                if s.metadata.get("retry_after") is not None:
                    retry_after_seconds = s.metadata.get("retry_after")
            elif s.metadata.get("status") == "SUCCESS":
                provider_call_succeeded += 1
                
    telemetry = TelemetryData(
        primary_llm_calls=primary_llm_calls,
        primary_llm_calls_avoided=primary_llm_calls_avoided,
        secondary_judge_calls=secondary_judge_calls,
        secondary_llm_calls_avoided=avoided_judge,
        avoided_latency_ms=avoided_latency if has_full_latency_history and (len(checks_skipped) > 0 or primary_llm_calls_avoided > 0) else None,
        actual_api_cost=actual_api_cost if actual_api_cost > 0 else None,
        avoided_api_cost=avoided_cost if has_full_cost_history and avoided_judge > 0 else None,
        latency=latency_tracker,
        total_input_tokens=total_input_tokens if total_input_tokens > 0 else None,
        total_output_tokens=total_output_tokens if total_output_tokens > 0 else None,
        total_tokens=total_tokens if total_tokens > 0 else None,
        provider_call_attempted=provider_call_attempted,
        provider_call_succeeded=provider_call_succeeded,
        provider_rate_limited=provider_rate_limited,
        fallback_used=fallback_used,
        retry_after_seconds=retry_after_seconds,
        call_type_history=call_type_history
    )
    
    # Format Response
    response = AnalyzeResponse(
        request_id=request_id,
        input=request.prompt,
        raw_ai_response=ai_response,
        response_source=response_source,
        initial_risk=initial_risk,
        routing_policy=routing_policy,
        detector_results=signals,
        risk=risk_detail,
        decision=decision,
        decision_reason=decision_reason,
        decision_trace=decision_trace,
        human_review_required=human_review_required,
        final_response=final_response,
        checks_executed=checks_executed,
        checks_skipped=checks_skipped,
        telemetry=telemetry
    )
    
    # Audit Logging
    log_audit({
        "request_id": request_id,
        "prompt": request.prompt,
        "decision": decision,
        "latency_ms": latency_tracker["total_latency"]
    })
    
    return response
