# 🩺 Healthz & Metrics Endpoint for Microservices

This Python script provides a lightweight HTTP service for exposing health status and Prometheus metrics.

---

## ✨ Features

- `/healthz`: Returns health status Text by default and JSON by `?format=json`
- `/metrics`: Exposes Prometheus metrics
- Simulates dependency checks for:
  - 🔌 Database connection
  - ⚙️ Config service
  - 🔁 Internal APIs (`user`, `payment`)
  - 🌍 External APIs (`wechat_pay`, `sms_provider`)
  - 🏁 End to End Workflow
- Dependencies have built-in error probability and timeout simulation
- Fully compatible with Kubernetes probes and Prometheus scraping

---

## 🚀 Getting Started

### 1. Install dependencies

```bash
pip install bottle
```

### 2. Run the script

```bash
python mock_healthz_server.py
```

```text
Service endpoints available:
  Healthcheck (Text):  http://0.0.0.0:8080/healthz
  Healthcheck (JSON):  http://0.0.0.0:8080/healthz?format=json
  Prometheus metrics:  http://0.0.0.0:8080/metrics
```

---

## ✅ Healthcheck

### Plaintext

http://127.0.0.1:8080/healthz  
http://127.0.0.1:8080/healthz?format=text  

#### Healthy:

```
Component                     Status  Detail
db_connection                 PASS    Database is connected
config_service                PASS    Config service is reachable
internal_api/user             PASS    internal_api/user OK (200ms)
internal_api/payment          PASS    internal_api/payment OK (333ms)
external_api/wechat_pay       PASS    external_api/wechat_pay OK (305ms)
external_api/sms_provider     PASS    external_api/sms_provider OK (174ms)
endtoend_workflow             PASS    Workflow executed successfully
```

#### Unhealthy:

```
Component                     Status  Detail
db_connection                 PASS    Database is connected
config_service                PASS    Config service is reachable
internal_api/user             FAIL    internal_api/user returned error
internal_api/payment          PASS    internal_api/payment OK (126ms)
external_api/wechat_pay       PASS    external_api/wechat_pay OK (395ms)
external_api/sms_provider     PASS    external_api/sms_provider OK (464ms)
endtoend_workflow             FAIL    Skipped due to upstream failure
```

### JSON Format

http://127.0.0.1:8080/healthz?format=json

#### Healthy:

```json
{
  "status": "ok",
  "data": {
    "message": "All checks passed"
  },
  "checks": [
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
      "name": "internal_api/user",
      "status": "ok",
      "message": "internal_api/user OK (255ms)"
    },
    {
      "name": "internal_api/payment",
      "status": "ok",
      "message": "internal_api/payment OK (170ms)"
    },
    {
      "name": "external_api/wechat_pay",
      "status": "ok",
      "message": "external_api/wechat_pay OK (221ms)"
    },
    {
      "name": "external_api/sms_provider",
      "status": "ok",
      "message": "external_api/sms_provider OK (90ms)"
    },
    {
      "name": "endtoend_workflow",
      "status": "ok",
      "message": "Workflow executed successfully"
    }
  ]
}
```

#### Unhealthy:

```json
{
  "status": "error",
  "data": {
    "message": "Some checks failed"
  },
  "checks": [
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
      "name": "internal_api/user",
      "status": "error",
      "message": "internal_api/user returned error"
    },
    {
      "name": "internal_api/payment",
      "status": "ok",
      "message": "internal_api/payment OK (170ms)"
    },
    {
      "name": "external_api/wechat_pay",
      "status": "ok",
      "message": "external_api/wechat_pay OK (221ms)"
    },
    {
      "name": "external_api/sms_provider",
      "status": "ok",
      "message": "external_api/sms_provider OK (90ms)"
    },
    {
      "name": "endtoend_workflow",
      "status": "error",
      "message": "Skipped due to upstream failure"
    }
  ]
}
```

## 📈 Prometheus

http://127.0.0.1:8080/metrics

### Config

```yaml
scrape_configs:
  - job_name: 'mock-healthz-metrics'
    static_configs:
      - targets: ['127.0.0.1:8080']
```

This will scrape `http://127.0.0.1:8080/metrics` by default.

### Metrics

#### Healthy:

```
# HELP healthcheck_status Health check status (1=ok,0=error)
# TYPE healthcheck_status gauge
healthcheck_status{check="db_connection"} 1
healthcheck_status{check="config_service"} 1
healthcheck_status{check="internal_api/user"} 1
healthcheck_status{check="internal_api/payment"} 1
healthcheck_status{check="external_api/wechat_pay"} 1
healthcheck_status{check="external_api/sms_provider"} 1
healthcheck_status{check="endtoend_workflow"} 1
```


#### Unhealthy:

```
# HELP healthcheck_status Health check status (1=ok,0=error)
# TYPE healthcheck_status gauge
healthcheck_status{check="db_connection"} 1
healthcheck_status{check="config_service"} 1
healthcheck_status{check="internal_api/user"} 0
healthcheck_status{check="internal_api/payment"} 1
healthcheck_status{check="external_api/wechat_pay"} 1
healthcheck_status{check="external_api/sms_provider"} 1
healthcheck_status{check="endtoend_workflow"} 0
```

## 🐳 Kubernetes

For Kubernetes livenessProbe and readinessProbe:

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

## 📌 Notes

- This script uses randomized logic to simulate service instability
- For production usage, replace simulation logic with real health check implementations (e.g., database pings, HTTP client calls, etc.)
