import pytest
import os
os.environ["GEMINI_API_KEY"] = ""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_allow_scenario():
    payload = {
      "prompt": "What are your office hours?",
      "use_case": "general_internal",
      "actor_role": "employee",
      "audience": "internal",
      "ai_response": "Our office hours are 9 AM to 5 PM."
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["decision"] == "ALLOW"
    assert data["risk"]["level"] == "LOW"
    assert len(data["checks_skipped"]) > 0
    assert data["response_source"] == "supplied_ai_response"
    assert "PII detector clear." in data["decision_trace"]

def test_edit_scenario():
    payload = {
      "prompt": "Can I get a refund after 90 days?",
      "use_case": "customer_support",
      "actor_role": "support_agent",
      "audience": "external",
      "ai_response": "Customers can request refunds within 90 days."
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["decision"] == "EDIT"
    assert "30 days" in data["final_response"] or "30 calendar days" in data["final_response"]
    assert data["risk"]["level"] == "HIGH"
    
    grounding_sig = next(s for s in data["detector_results"] if s["detector"] == "grounding")
    sources = grounding_sig["metadata"].get("sources", [])
    assert len(sources) == len(set(sources)), f"Duplicate sources found: {sources}"
    
def test_review_scenario():
    payload = {
      "prompt": "Is this candidate suitable?",
      "use_case": "hr",
      "actor_role": "hr_manager",
      "audience": "internal",
      "ai_response": "This female candidate may be less suitable for engineering because women often leave engineering jobs earlier."
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["decision"] == "REVIEW"
    assert data["human_review_required"] is True
    assert "bias" in [r["risk_type"] for r in data["detector_results"] if r.get("detected")]

def test_block_scenario():
    payload = {
      "prompt": "What is Rahul's Aadhaar?",
      "use_case": "general_internal",
      "actor_role": "employee",
      "audience": "internal",
      "ai_response": "Rahul's Aadhaar number is 1234 5678 9012."
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["decision"] == "BLOCK"
    assert any(r.get("affected_entity") == "aadhaar" for r in data["detector_results"])

def test_math_consistency():
    payload = {
      "prompt": "Test math",
      "use_case": "customer_support",
      "actor_role": "support",
      "audience": "external"
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # 1. Test Post-Detection Risk Math
    risk = data["risk"]
    b = risk["breakdown"]
    expected_score = b["primary_signal"] + b["secondary_contribution"] + b["overlap_bonus"] + b["business_impact_modifier"]
    assert risk["score"] == min(round(expected_score), 100)
    
    # 2. Test Initial Risk 5-factor Math
    initial_risk = data["initial_risk"]
    factors = initial_risk["factors"]
    expected_initial = (
        factors["exposure"]["score"] +
        factors["data_sensitivity"]["score"] +
        factors["business_impact"]["score"] +
        factors["failure_likelihood"]["score"] +
        factors["uncertainty"]["score"]
    )
    assert initial_risk["score"] == expected_initial

def test_fallback_mode_still_works():
    payload = {
      "prompt": "fallback test",
      "use_case": "general_internal",
      "actor_role": "employee",
      "audience": "internal",
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["response_source"] == "primary_llm"
    assert "Placeholder response" in data["raw_ai_response"]

def test_routing_mode_remains_single_model_poc():
    payload = {
      "prompt": "test routing",
      "use_case": "general_internal",
      "actor_role": "employee",
      "audience": "internal",
      "ai_response": "dummy response"
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["routing_policy"]["routing_mode"] == "single_model_poc"
import os
from unittest.mock import patch, MagicMock
from backend.services.llm_service import evaluate_semantic_risk, generate_response

@patch("backend.services.llm_service.LLM_PROVIDER", "gemini")
@patch("backend.services.llm_service.GEMINI_API_KEY", "fake_gemini_key")
@patch("backend.services.llm_service.genai.Client")
def test_gemini_provider_selection_primary(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    # Mock primary generation
    mock_response = MagicMock()
    mock_response.text = "Gemini primary response"
    mock_response.usage_metadata.total_token_count = 42
    mock_client.models.generate_content.return_value = mock_response
    
    ans, tokens = generate_response("test")
    
    assert "Gemini primary response" in ans
    assert tokens["total"] == 42
    mock_client.models.generate_content.assert_called_once()

@patch("backend.services.llm_service.LLM_PROVIDER", "gemini")
@patch("backend.services.llm_service.GEMINI_API_KEY", "fake_gemini_key")
@patch("backend.services.llm_service.genai.Client")
def test_gemini_provider_selection_judge_and_malformed(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    # 1. Valid judge output
    mock_response_valid = MagicMock()
    mock_response_valid.text = '{"detected": true, "risk_type": "bias", "severity": 0.5, "confidence": 0.5, "reason": "test", "affected_claim": ""}'
    mock_response_valid.usage_metadata.total_token_count = 15
    
    # 2. Malformed judge output
    mock_response_malformed = MagicMock()
    mock_response_malformed.text = 'invalid json'
    
    mock_client.models.generate_content.side_effect = [mock_response_valid, mock_response_malformed]
    
    parsed, tokens = evaluate_semantic_risk("query", "answer")
    assert parsed is not None
    assert parsed["detected"] is True
    assert tokens["total"] == 15
    
    # Second call should not crash, returning None, 0
    parsed2, tokens2 = evaluate_semantic_risk("query2", "answer2")
    assert parsed2 is None
    assert tokens2["total"] == 0
