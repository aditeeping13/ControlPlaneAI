import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app
import os
import sys

client = TestClient(app)

class MockRateLimitError(Exception):
    def __str__(self):
        return "429 Resource exhausted: Quota exceeded. [{'retryDelay': '36s'}]"

@patch("backend.services.llm_service.LLM_PROVIDER", "gemini")
@patch("backend.services.llm_service.GEMINI_API_KEY", "fake_key")
@patch("backend.services.llm_service.genai.Client")
def test_primary_generation_rate_limit(mock_client_class):
    # Setup mock to raise rate limit exception
    mock_client = mock_client_class.return_value
    mock_client.models.generate_content.side_effect = MockRateLimitError()

    payload = {
        "prompt": "Tell me a joke.",
        "use_case": "general_internal",
        "actor_role": "employee",
        "audience": "internal"
    }
    
    with patch.dict(os.environ, {"DEMO_SAFE_MODE": "true"}):
        response = client.post("/analyze", json=payload)
        
    assert response.status_code == 200
    data = response.json()
    
    # 1. 429 triggers graceful fallback
    # 6. fallback source is clearly marked
    assert data["response_source"] == "fallback_rate_limited"
    assert "Gemini rate limit exceeded" in data["raw_ai_response"]
    
    # Telemetry should reflect rate limit
    # 2. retry_after_seconds is extracted
    telemetry = data["telemetry"]
    assert telemetry["provider_rate_limited"] == 1
    assert telemetry["retry_after_seconds"] == 36
    assert telemetry["fallback_used"] == 1
    
    # 9. No aggressive retry loop (call count is 1)
    assert mock_client.models.generate_content.call_count == 1

@patch("backend.services.llm_service.LLM_PROVIDER", "gemini")
@patch("backend.services.llm_service.GEMINI_API_KEY", "fake_key")
@patch("backend.services.llm_service.genai.Client")
def test_required_ai_judge_rate_limit(mock_client_class):
    # Setup mock to raise rate limit exception
    mock_client = mock_client_class.return_value
    mock_client.models.generate_content.side_effect = MockRateLimitError()

    # Provide ai_response to skip primary generation and test ai_judge
    payload = {
        "prompt": "Test AI Judge",
        "use_case": "general_internal",
        "actor_role": "employee",
        "audience": "internal",
        "ai_response": "I will tell you a secret.",
        "benchmark_mode": "benchmark_baseline" # This forces AI Judge
    }
    
    with patch.dict(os.environ, {"DEMO_SAFE_MODE": "true"}):
        response = client.post("/analyze", json=payload)
        
    assert response.status_code == 200
    data = response.json()
    
    # 4. required AI Judge 429 triggers REVIEW
    assert data["decision"] == "REVIEW"
    assert "Required semantic verification could not be completed" in data["decision_trace"][-2]
    
    telemetry = data["telemetry"]
    assert telemetry["provider_rate_limited"] == 1
    assert telemetry["retry_after_seconds"] == 36

def test_benchmark_safety():
    # 7. benchmark defaults to non-live mode
    import subprocess
    
    # Run benchmark without --live
    result = subprocess.run(["python", "backend/benchmarks/benchmark.py"], capture_output=True, text=True)
    assert "live_provider" not in result.stdout
    assert "deterministic_mock" in result.stdout

    # 8. live benchmark requires explicit flag
    result = subprocess.run(["python", "backend/benchmarks/benchmark.py", "--live"], capture_output=True, text=True)
    assert "Live benchmark will consume multiple Gemini API requests" in result.stdout
    assert "Please run with '--live --confirm-live'" in result.stdout
