# Autonomous Self-Healing AIOps Engine

An event-driven Autonomous Site Reliability Engineering (AIOps) platform that automatically intercepts Kubernetes incident alerts from Prometheus Alertmanager, performs automated Root Cause Analysis (RCA) on crash logs and events, executes targeted self-healing actions, and dispatches incident reports.

## Architecture Overview
[ K8s Pod Crash / OOM ]
│
▼
[ Prometheus Scrapes Metrics ]
│
▼
[ Alertmanager Webhook ] ──▶ [ FastAPI AIOps Engine (port 8080) ]
│
┌──────────────┴──────────────┐
▼                             ▼
[ K8s API (Logs & Events) ]    [ LLM RCA Engine ]
│                             │
└──────────────┬──────────────┘
▼
[ Auto-Remediation Execution ]
- Pod Termination
- Deployment Rollout Restart
│
▼
[ Discord / Slack Webhook Card ]

## Tech Stack
- **Container Orchestration:** Kubernetes (v1.31+) with Istio Service Mesh
- **Observability:** Prometheus Operator, Kube-State-Metrics, Prometheus Alertmanager
- **Runtime & Webhook Framework:** Python 3.14+, FastAPI, Uvicorn (Systemd managed)
- **Remediation & Automation:** Kubernetes Python Client (`client.CoreV1Api`, `client.AppsV1Api`)
- **Intelligence:** LLM Root Cause Analysis with heuristic fallback

## Verified Live Capabilities
1. **Instant Pod Crash Interception:** Evaluates `CrashLoopBackOff` transitions within 5 seconds.
2. **Istio-Aware Log Extraction:** Dynamically discovers application containers while skipping sidecars (`istio-proxy`, `istio-init`).
3. **Automated Remediations:** Non-disruptive rolling restart of deployments on persistent crash loops.

