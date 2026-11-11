import os
import requests
import logging

logger = logging.getLogger("aiops-engine")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

def send_incident_notification(pod_name: str, namespace: str, alert_name: str, rca: dict, action_taken: str):
    if not DISCORD_WEBHOOK_URL:
        logger.info("No DISCORD_WEBHOOK_URL set; skipping external chat alert.")
        return

    payload = {
        "embeds": [
            {
                "title": f"🚨 [AIOps Auto-Healed] {alert_name}",
                "color": 3066993,  # Green/Cyan
                "fields": [
                    {"name": "Pod Name", "value": f"`{pod_name}`", "inline": True},
                    {"name": "Namespace", "value": f"`{namespace}`", "inline": True},
                    {"name": "Root Cause", "value": rca.get("root_cause", "N/A"), "inline": False},
                    {"name": "Remediation Action", "value": f"**{action_taken}** (Confidence: {rca.get('confidence_score', 'N/A')})", "inline": True},
                    {"name": "Suggested Code Fix", "value": f"`{rca.get('fix_details', 'N/A')}`", "inline": False}
                ],
                "footer": {"text": "Autonomous Self-Healing AIOps Engine"}
            }
        ]
    }

    try:
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        if res.status_code in [200, 204]:
            logger.info("Incident notification dispatched to Discord channel successfully.")
        else:
            logger.warning(f"Discord webhook responded with code: {res.status_code}")
    except Exception as e:
        logger.error(f"Failed to post notification to Discord: {e}")
