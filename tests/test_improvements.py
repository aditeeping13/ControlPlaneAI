import pytest
import os
os.environ["GEMINI_API_KEY"] = ""

from fastapi.testclient import TestClient
from backend.main import app
from backend.detectors.ai_judge import evaluate_semantic_risk
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_judge_required_failure_escalates_to_review():
    with patch("backend.core.router.evaluate_semantic_risk") as mock_judge:
        from backend.models.schemas import RiskSignal
        mock_judge.return_value = [RiskSignal(
            detector="ai_judge",
            executed=True,
            detected=False,
            severity=0.0,
            confidence=1.0,
            evidence=[],
            metadata={"tokens": 0, "status": "ERROR"}
        )]
        
        payload = {
            "prompt": "Is this candidate suitable for engineering? She is female.",
            "use_case": "hr",
            "actor_role": "hr_manager",
            "audience": "internal",
            "ai_response": "She is female, so she might not be a good fit for engineering."
        }
        response = client.post("/analyze", json=payload)
        data = response.json()
        
        assert data["decision"] == "REVIEW"
        assert "Required semantic verification could not be completed. Escalated for human review." in data["decision_trace"]

def test_judge_optional_skip_remains_valid():
    payload = {
        "prompt": "What is the capital of France?",
        "use_case": "general_internal",
        "actor_role": "employee",
        "audience": "internal",
        "ai_response": "Paris"
    }
    response = client.post("/analyze", json=payload)
    data = response.json()
    
    assert data["decision"] == "ALLOW"
    assert any(s["detector"] == "ai_judge" for s in data["checks_skipped"])

def test_aadhaar_preflight_blocks_before_primary_llm():
    payload = {
        "prompt": "Here is Rahul's Aadhaar: 1234 5678 9012",
        "use_case": "general_internal",
        "actor_role": "employee",
        "audience": "internal"
    }
    response = client.post("/analyze", json=payload)
    data = response.json()
    
    assert data["decision"] == "BLOCK"
    assert "Critical deterministic preflight violation established before generation." in data["decision_trace"]
    assert data["response_source"] == "primary_llm_skipped"
    assert data["telemetry"]["primary_llm_calls"] == 0
    assert data["telemetry"]["primary_llm_calls_avoided"] == 1

def test_credential_hard_stop_skips_primary_llm():
    payload = {
        "prompt": "Here is the API key: key=abcdefghijklmnopq",
        "use_case": "general_internal",
        "actor_role": "employee",
        "audience": "internal"
    }
    response = client.post("/analyze", json=payload)
    data = response.json()
    
    assert data["decision"] == "BLOCK"
    assert "Critical deterministic preflight violation established before generation." in data["decision_trace"]
    assert data["telemetry"]["primary_llm_calls_avoided"] == 1

def test_normal_low_risk_query_reaches_primary_llm():
    payload = {
        "prompt": "What is 2+2?",
        "use_case": "general_internal",
        "actor_role": "employee",
        "audience": "internal"
    }
    response = client.post("/analyze", json=payload)
    data = response.json()
    
    assert data["decision"] == "ALLOW"
    assert data["response_source"] == "primary_llm"
    assert data["telemetry"]["primary_llm_calls"] == 1
    assert data["telemetry"]["primary_llm_calls_avoided"] == 0

def test_benchmark_baseline_executes_all_applicable_checks():
    payload = {
        "prompt": "What is our refund policy?",
        "use_case": "customer_support",
        "actor_role": "employee",
        "audience": "external",
        "benchmark_mode": "benchmark_baseline"
    }
    response = client.post("/analyze", json=payload)
    data = response.json()
    
    checks_executed = [c["detector"] for c in data["checks_executed"]]
    assert "rule_threat" in checks_executed
    assert "pii" in checks_executed
    assert "grounding" in checks_executed
    assert "ai_judge" in checks_executed

def test_benchmark_baseline_executes_judge_when_applicable():
    payload = {
        "prompt": "Should we hire older candidates?",
        "use_case": "hr",
        "actor_role": "hr_manager",
        "audience": "internal",
        "benchmark_mode": "benchmark_baseline"
    }
    response = client.post("/analyze", json=payload)
    data = response.json()
    
    checks_executed = [c["detector"] for c in data["checks_executed"]]
    assert "ai_judge" in checks_executed
