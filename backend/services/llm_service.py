import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from google import genai
from google.genai import types
from typing import Tuple, Optional

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BACKEND_DIR / ".env"
load_dotenv(ENV_PATH)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "fallback").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.6-flash" if LLM_PROVIDER == "gemini" else "gpt-3.5-turbo")

print("LLM provider:", LLM_PROVIDER)
print("Gemini key loaded:", bool(GEMINI_API_KEY))
print("LLM model:", LLM_MODEL)

def get_provider_status():
    return {
        "provider": LLM_PROVIDER,
        "model": LLM_MODEL,
        "api_key_loaded": bool(GEMINI_API_KEY) if LLM_PROVIDER == "gemini" else bool(LLM_API_KEY)
    }

def generate_response(prompt: str, context: str = None) -> Tuple[str, int]:
    if LLM_PROVIDER == "gemini" and GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
        sys_instruction = "You are a helpful enterprise assistant."
        if context:
            sys_instruction += f"\nContext: {context}"
        try:
            response = client.models.generate_content(
                model=LLM_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruction,
                    temperature=0.7
                )
            )
            tokens = 0
            input_tokens = 0
            output_tokens = 0
            if response.usage_metadata:
                tokens = response.usage_metadata.total_token_count
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
            return response.text, {"total": tokens, "input": input_tokens, "output": output_tokens}
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "resource_exhausted" in error_str or "quota" in error_str or "rate limit" in error_str:
                retry_after = None
                import re
                match = re.search(r"retrydelay['\":\s]+(\d+)s", error_str)
                if match:
                    retry_after = int(match.group(1))
                return {
                    "error_type": "RATE_LIMITED",
                    "provider": "gemini",
                    "retryable": True,
                    "retry_after_seconds": retry_after,
                    "message": "Gemini quota/rate limit exceeded"
                }, {"total": 0, "input": 0, "output": 0}
            return f"Error connecting to Gemini LLM: {str(e)}", {"total": 0, "input": 0, "output": 0}
            
    elif LLM_PROVIDER == "openai" and LLM_API_KEY:
        client = OpenAI(api_key=LLM_API_KEY)
        messages = [
            {"role": "system", "content": "You are a helpful enterprise assistant."},
            {"role": "user", "content": prompt}
        ]
        if context:
            messages[0]["content"] += f"\nContext: {context}"
            
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                max_tokens=500,
            )
            answer = response.choices[0].message.content
            total_tokens = response.usage.total_tokens if response.usage else 0
            return answer, {"total": total_tokens, "input": 0, "output": 0}
        except Exception as e:
            return f"Error connecting to OpenAI LLM: {str(e)}", {"total": 0, "input": 0, "output": 0}
    else:
        return "Placeholder response: No API key configured.", {"total": 0, "input": 0, "output": 0}


def evaluate_semantic_risk(prompt: str, ai_response: str) -> Tuple[Optional[dict], int]:
    sys_instruction = "You are an enterprise AI safety evaluator. Evaluate the supplied AI-generated answer. Check only for discriminatory reasoning, semantic policy violation, unsafe high-impact recommendation, or other semantic risk. Return valid JSON only with keys: detected (bool), risk_type (str), severity (float), confidence (float), reason (str), affected_claim (str)."
    user_content = f"Query: {prompt}\n\nAI Answer: {ai_response}"

    if LLM_PROVIDER == "gemini" and GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
        try:
            response = client.models.generate_content(
                model=LLM_MODEL,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruction,
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            parsed = json.loads(response.text)
            tokens = 0
            input_tokens = 0
            output_tokens = 0
            if response.usage_metadata:
                tokens = response.usage_metadata.total_token_count
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
            return parsed, {"total": tokens, "input": input_tokens, "output": output_tokens}
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "resource_exhausted" in error_str or "quota" in error_str or "rate limit" in error_str:
                retry_after = None
                import re
                match = re.search(r"retrydelay['\":\s]+(\d+)s", error_str)
                if match:
                    retry_after = int(match.group(1))
                return {
                    "status": "RATE_LIMITED",
                    "error_type": "RATE_LIMITED",
                    "provider": "gemini",
                    "retryable": True,
                    "retry_after_seconds": retry_after,
                    "message": "Gemini quota/rate limit exceeded"
                }, {"total": 0, "input": 0, "output": 0}
            return None, {"total": 0, "input": 0, "output": 0}
            
    elif LLM_PROVIDER == "openai" and LLM_API_KEY:
        client = OpenAI(api_key=LLM_API_KEY)
        messages = [
            {"role": "system", "content": sys_instruction},
            {"role": "user", "content": user_content}
        ]
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                response_format={"type": "json_object"}
            )
            answer = response.choices[0].message.content
            total_tokens = response.usage.total_tokens if response.usage else 0
            return json.loads(answer), {"total": total_tokens, "input": 0, "output": 0}
        except Exception:
            return None, {"total": 0, "input": 0, "output": 0}
            
    else:
        prompt_lower = prompt.lower()
        ai_resp_lower = ai_response.lower()
        if "female" in prompt_lower or "women" in prompt_lower or "maternity" in prompt_lower or "female" in ai_resp_lower or "women" in ai_resp_lower or "maternity" in ai_resp_lower:
            return {
                "detected": True,
                "risk_type": "bias",
                "severity": 0.82,
                "confidence": 0.71,
                "reason": "Maternity status appears to influence promotion suitability.",
                "affected_claim": "maternity leave"
            }, {"total": 0, "input": 0, "output": 0}
        return {
            "detected": False,
            "risk_type": "none",
            "severity": 0.0,
            "confidence": 1.0,
            "reason": "",
            "affected_claim": ""
        }, {"total": 0, "input": 0, "output": 0}


def generate_corrected_response(original_response: str, authoritative_evidence: str) -> str:
    if LLM_PROVIDER == "gemini" and GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
        sys_instruction = f"You are an editor. Correct the following response using strictly this evidence: {authoritative_evidence}"
        try:
            response = client.models.generate_content(
                model=LLM_MODEL,
                contents=original_response,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruction,
                    temperature=0.0
                )
            )
            return response.text
        except Exception as e:
            return f"Correction error: {str(e)}"
            
    elif LLM_PROVIDER == "openai" and LLM_API_KEY:
        client = OpenAI(api_key=LLM_API_KEY)
        messages = [
            {"role": "system", "content": f"You are an editor. Correct the following response using strictly this evidence: {authoritative_evidence}"},
            {"role": "user", "content": original_response}
        ]
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Correction error: {str(e)}"
            
    else:
        if "30 days" in authoritative_evidence and "90 days" in original_response:
            return "Customers may request refunds within 30 calendar days of purchase."
        return f"Corrected using evidence: {authoritative_evidence[:50]}..."
