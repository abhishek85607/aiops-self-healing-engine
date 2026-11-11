from fastapi import FastAPI, Request, BackgroundTasks
import logging
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aiops-engine")

from app.k8s_client import get_pod_logs, get_pod_events, restart_deployment, delete_failed_pod
from app.rca_engine import analyze_incident_with_ai
from app.notifier import send_incident_notification

app = FastAPI(title="Autonomous Self-Healing AIOps Engine", version="1.0.0")

IGNORED_ALERTS = {"Watchdog", "KubeAPIDown", "etcdInsufficientMembers", "InfoInhibitor"}

def process_alert_healing(alert: dict):
    labels = alert.get("labels", {})
    alert_name = labels.get("alertname", "UnknownAlert")
    
    if alert_name in IGNORED_ALERTS:
        return

    pod_name = labels.get("pod", "")
    namespace = labels.get("namespace", "default")
    deployment = labels.get("deployment", "")

    if not deployment and pod_name:
        parts = pod_name.split("-")
        deployment = "-".join(parts[:-2]) if len(parts) > 2 else pod_name

    logger.info(f"⚡ [ALERT RECEIVED] Alert: {alert_name} | Target Pod: {pod_name} | Namespace: {namespace}")

    logs = get_pod_logs(pod_name, namespace) if pod_name else "N/A"
    events = get_pod_events(pod_name, namespace) if pod_name else "N/A"

    logger.info(f"📋 Fetched Pod Logs snippet: {logs.strip()[-120:] if logs else 'None'}")

    ai_analysis = analyze_incident_with_ai(pod_name, namespace, alert_name, logs, events)
    logger.info(f"🧠 AI RCA: {ai_analysis.get('root_cause')}")
    action = ai_analysis.get("recommended_action", "RESTART_POD")
    logger.info(f"🎯 Action Decided: {action} (Confidence: {ai_analysis.get('confidence_score')})")

    action_summary = "NO_ACTION"
    if (action in ["RESTART_POD", "RESTART_DEPLOYMENT"]) and pod_name:
        logger.info(f"🛠️ [SELF-HEALING] Deleting faulty pod {pod_name} to force recovery...")
        delete_failed_pod(pod_name, namespace)
        action_summary = "POD_DELETED"
        if deployment:
            logger.info(f"🛠️ [SELF-HEALING] Triggering rollout restart for deployment: {deployment}")
            restart_deployment(deployment, namespace)
            action_summary = "DEPLOYMENT_ROLLOUT_RESTARTED"
    elif action == "ESCALATE":
        action_summary = "ESCALATED_MANUAL_REVIEW"
        logger.warning(f"⚠️ [ESCALATE] Critical issue, requires manual engineer intervention.")

    send_incident_notification(pod_name, namespace, alert_name, ai_analysis, action_summary)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "aiops-engine"}

@app.post("/webhook")
async def receive_alert(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    alerts = data.get("alerts", [])

    for alert in alerts:
        if alert.get("status") == "firing":
            background_tasks.add_task(process_alert_healing, alert)

    return {"status": "acknowledged", "alerts_queued": len(alerts)}
