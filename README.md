# 🩺 Mock /healthz and /metrics

![featured-image](featured-image.png)

## ✨ Features

- `/healthz`:
  - Return code: Healthy `200`, Unhealthy `500`
  - Output: `Plaintext`, `JSON`
- `/metrics`: Prometheus metrics
- **Two-tier health checks**:
  - 🔴 **Critical checks** Affect overall health status:
    - 🔌 Database connection: Core dependency, must be healthy
    - ⚙️ Config service: Core dependency, must be healthy
    - 🔁 Internal APIs `billing`, `usage`: Depend on upstream services (DB + Config), skipped if upstream fails
  - 🟡 **External checks** Independent:
    - 🌍 External APIs `alipay`, `sms`: Run independently, don't affect overall health status
- Dependencies have built-in error probability and timeout simulation
- Fully compatible with Kubernetes probes and Prometheus scraping
- **Dependency Chain**:
  - Database + Config Service → Internal APIs → Overall Health Status
  - External APIs → Independent Monitoring Only

---

## 🚀 Getting Started

### 1. Install dependencies

```bash
pip install bottle
```

### 2. Run the script

```bash
python mock-healthz-metrics.py
```

```text
Service endpoints available:
  Healthcheck (Text):  http://0.0.0.0:8080/healthz
  Healthcheck (JSON):  http://0.0.0.0:8080/healthz?format=json
  Prometheus metrics:  http://0.0.0.0:8080/metrics
```

## ✅ Healthcheck

### Plaintext

http://127.0.0.1:8080/healthz  
http://127.0.0.1:8080/healthz?format=text  

**Healthy**

```
HEALTH CHECK SNAPSHOT [2025-07-18 11:03:15]
-------------------------------------------
CHECK                   STATUS  MESSAGE
----- CRITICAL -----
db_connection           ✔       Database is connected
config_service          ✔       Config service is reachable
internal_api/billing    ✔       internal_api/billing OK (392ms)
internal_api/usage      ✔       internal_api/usage OK (348ms)
----- EXTERNAL -----
external_api/alipay     ✔       external_api/alipay OK (308ms)
external_api/sms        ✖       external_api/sms timed out
```

**Unhealthy**

```
HEALTH CHECK SNAPSHOT [2025-07-18 11:05:27]
-------------------------------------------
CHECK                   STATUS  MESSAGE
----- CRITICAL -----
db_connection           ✔       Database is connected
config_service          ✔       Config service is reachable
internal_api/billing    ✔       internal_api/billing OK (253ms)
internal_api/usage      ✖       internal_api/usage returned error
----- EXTERNAL -----
external_api/alipay     ✔       external_api/alipay OK (101ms)
external_api/sms        ✔       external_api/sms OK (183ms)
```

### JSON Format

http://127.0.0.1:8080/healthz?format=json

**Healthy**

```json
{
  "status": "ok",
  "data": {
    "message": "All critical checks passed",
    "snapshot_time": "2025-07-18 11:03:15",
    "checks": {
      "critical": [
        {
          "name": "db_connection",
          "status": "ok",
          "message": "Database is connected"
        },
        {
          "name": "config_service",
          "status": "ok",
          "message": "Config service is reachable"
        },
        {
          "name": "internal_api/billing",
          "status": "ok",
          "message": "internal_api/billing OK (392ms)"
        },
        {
          "name": "internal_api/usage",
          "status": "ok",
          "message": "internal_api/usage OK (348ms)"
        }
      ],
      "external": [
        {
          "name": "external_api/alipay",
          "status": "ok",
          "message": "external_api/alipay OK (308ms)"
        },
        {
          "name": "external_api/sms",
          "status": "error",
          "message": "external_api/sms timed out"
        }
      ]
    }
  }
}
```

**Unhealthy**

```json
{
  "status": "error",
  "data": {
    "message": "Some critical checks failed",
    "snapshot_time": "2025-07-18 11:05:27",
    "checks": {
      "critical": [
        {
          "name": "db_connection",
          "status": "ok",
          "message": "Database is connected"
        },
        {
          "name": "config_service",
          "status": "ok",
          "message": "Config service is reachable"
        },
        {
          "name": "internal_api/billing",
          "status": "ok",
          "message": "internal_api/billing OK (253ms)"
        },
        {
          "name": "internal_api/usage",
          "status": "error",
          "message": "internal_api/usage returned error"
        }
      ],
      "external": [
        {
          "name": "external_api/alipay",
          "status": "ok",
          "message": "external_api/alipay OK (101ms)"
        },
        {
          "name": "external_api/sms",
          "status": "ok",
          "message": "external_api/sms OK (183ms)"
        }
      ]
    }
  }
}
```

## 📈 Prometheus

http://127.0.0.1:8080/metrics

**Config**

```yaml
scrape_configs:
  - job_name: 'mock-healthz-metrics'
    static_configs:
      - targets: ['127.0.0.1:8080']
```

Scrape `http://127.0.0.1:8080/metrics` by default.

**Metrics**

**Healthy**

```
# HELP healthcheck_status Health check status (1=ok,0=error)
# TYPE healthcheck_status gauge
healthcheck_status{check="db_connection",type="critical"} 1
healthcheck_status{check="config_service",type="critical"} 1
healthcheck_status{check="internal_api/billing",type="critical"} 1
healthcheck_status{check="internal_api/usage",type="critical"} 1
healthcheck_status{check="external_api/alipay",type="external"} 1
healthcheck_status{check="external_api/sms",type="external"} 0
```


**Unhealthy**

```
# HELP healthcheck_status Health check status (1=ok,0=error)
# TYPE healthcheck_status gauge
healthcheck_status{check="db_connection",type="critical"} 1
healthcheck_status{check="config_service",type="critical"} 1
healthcheck_status{check="internal_api/billing",type="critical"} 1
healthcheck_status{check="internal_api/usage",type="critical"} 0
healthcheck_status{check="external_api/alipay",type="external"} 1
healthcheck_status{check="external_api/sms",type="external"} 1
```

## 🐳 Kubernetes

For Kubernetes livenessProbe and readinessProbe:

```bash
❯ curl -I http://127.0.0.1:8080/healthz
HTTP/1.0 200 OK
Date: Fri, 18 Jul 2025 03:03:31 GMT
Server: WSGIServer/0.2 CPython/3.11.11
Content-Type: text/plain
Content-Length: 444

❯ curl -I http://127.0.0.1:8080/healthz
HTTP/1.0 500 Internal Server Error
Date: Fri, 18 Jul 2025 03:05:36 GMT
Server: WSGIServer/0.2 CPython/3.11.11
Content-Type: text/plain
Content-Length: 438
```

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 30
  failureThreshold: 5
  timeoutSeconds: 5

readinessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 20
  failureThreshold: 3
  successThreshold: 2
  timeoutSeconds: 2
```

For more detailed probe design, please refer to the article: [Kubernetes Container Healthcheck and Graceful Termination](https://blog.heylinux.com/en/2024/07/kubernetes-container-healthcheck-and-graceful-termination/).

## 📌 Notes

- This script uses randomized logic to simulate service instability
- For production usage, replace simulation logic with real health check implementations (e.g., database pings, HTTP client calls, etc.)
