import logging
from kubernetes import client, config

logger = logging.getLogger("aiops-engine")

def load_k8s_config():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

load_k8s_config()
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

def get_pod_logs(pod_name: str, namespace: str, tail_lines: int = 50) -> str:
    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        app_container = None
        for c in pod.spec.containers:
            if c.name not in ["istio-proxy", "istio-init"]:
                app_container = c.name
                break
        
        container_to_query = app_container or pod.spec.containers[0].name
        return v1.read_namespaced_pod_log(
            name=pod_name, 
            namespace=namespace, 
            container=container_to_query, 
            tail_lines=tail_lines
        )
    except Exception as e:
        logger.error(f"Error fetching logs for {pod_name}: {e}")
        return f"Could not fetch logs: {str(e)}"

def get_pod_events(pod_name: str, namespace: str) -> str:
    try:
        events = v1.list_namespaced_event(namespace=namespace, field_selector=f"involvedObject.name={pod_name}")
        event_msgs = [f"[{e.type}] {e.reason}: {e.message}" for e in events.items]
        return "\n".join(event_msgs) if event_msgs else "No recent events found."
    except Exception as e:
        logger.error(f"Error fetching events for {pod_name}: {e}")
        return f"Could not fetch events: {str(e)}"

def restart_deployment(deployment_name: str, namespace: str) -> bool:
    import datetime
    try:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        body = {
            'spec': {
                'template': {
                    'metadata': {
                        'annotations': {
                            'kubectl.kubernetes.io/restartedAt': now
                        }
                    }
                }
            }
        }
        apps_v1.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=body)
        logger.info(f"Deployment {deployment_name} restarted successfully in {namespace}")
        return True
    except Exception as e:
        logger.error(f"Failed to restart deployment {deployment_name}: {e}")
        return False

def delete_failed_pod(pod_name: str, namespace: str) -> bool:
    try:
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        logger.info(f"Pod {pod_name} deleted successfully from {namespace}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete pod {pod_name}: {e}")
        return False
