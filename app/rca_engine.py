import os
import requests
import json
import logging

logger = logging.getLogger("aiops-engine")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def analyze_incident_with_ai(pod_name: str, namespace: str, alert_name: str, logs: str, events: str) -> dict:
    prompt = f"""
You are an expert Autonomous Site Reliability Engineer (AIOps).
Analyze the following Kubernetes incident:

Pod Name: {pod_name}
Namespace: {namespace}
Alert Triggered: {alert_name}

Recent Pod Events:
{events}

Recent Pod Logs:
{logs}

Provide your analysis in strictly valid JSON format with the following keys:
{{
  "root_cause": "short 1-2 sentence explanation of why the failure occurred",
  "recommended_action": "RESTART_POD | RESTART_DEPLOYMENT | ROLLBACK | ESCALATE",
  "confidence_score": 0.95,
  "action_reason": "why this action is appropriate",
  "fix_details": "technical explanation of what needs to be changed permanently in code/manifest"
}}
Return only the raw JSON string without markdown quotes.
"""

    if not GEMINI_API_KEY:
        logger.warning("No GEMINI_API_KEY found, running rule-based heuristic RCA.")
        action = "RESTART_DEPLOYMENT"
        if "OOMKilled" in events or "OOM" in alert_name:
            action = "ESCALATE"
        return {
            "root_cause": f"Pod encountered {alert_name}. Heuristic analysis detected crash/fault in container lifecycle.",
            "recommended_action": action,
            "confidence_score": 0.85,
            "action_reason": "Triggered fallback heuristic remediation strategy.",
            "fix_details": "Check container memory limit or application exception handling in code."
        }

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
        if res.status_code == 200:
            raw_text = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3].strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:-3].strip()
            return json.loads(raw_text)
        else:
            logger.error(f"LLM API returned status {res.status_code}: {res.text}")
    except Exception as e:
        logger.error(f"Error calling LLM API: {e}")

    return {
        "root_cause": f"Incident triggered by {alert_name}. Unable to query LLM.",
        "recommended_action": "RESTART_DEPLOYMENT",
        "confidence_score": 0.5,
        "action_reason": "Default safety restart due to API timeout.",
        "fix_details": "Inspect pod logs manually."
    }
