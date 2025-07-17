from bottle import route, run, request, HTTPResponse
import random, json

INTERNAL_APIS = ["user", "payment"]
EXTERNAL_APIS = ["wechat_pay", "sms_provider"]

def check_db_connection():
    ok = random.random() < 0.98
    msg = "Database is connected" if ok else "Database connection failed"
    return ("db_connection", ok, msg)

def check_config_service():
    ok = random.random() < 0.98
    msg = "Config service is reachable" if ok else "Config service error"
    return ("config_service", ok, msg)

def check_apis(api_list, prefix):
    results = []
    for name in api_list:
        latency = random.randint(50, 500)
        timeout = random.random() < 0.02  # ~2% timeout
        svc = f"{prefix}/{name}"

        if timeout:
            msg = f"{svc} timed out after {latency}ms"
            ok = False
        else:
            error = random.random() < 0.13  # ~13% returned error
            if error:
                msg = f"{svc} returned error"
                ok = False
            else:
                msg = f"{svc} OK ({latency}ms)"
                ok = True

        results.append((svc, ok, msg))
    return results

def check_endtoend_workflow(prior_results):
    if any(not ok for _, ok, _ in prior_results):
        return ("endtoend_workflow", False, "Skipped due to upstream failure")
    ok = random.random() < 0.95
    msg = "Workflow executed successfully" if ok else "Workflow execution failed"
    return ("endtoend_workflow", ok, msg)

def run_checks():
    results = [
        check_db_connection(),
        check_config_service()
    ]

    if all(ok for _, ok, _ in results):
        results += check_apis(INTERNAL_APIS, "internal_api")
        results += check_apis(EXTERNAL_APIS, "external_api")
    else:
        for prefix, apis in [("internal_api", INTERNAL_APIS), ("external_api", EXTERNAL_APIS)]:
            for name in apis:
                svc = f"{prefix}/{name}"
                results.append((svc, False, "Skipped due to upstream failure"))

    results.append(check_endtoend_workflow(results))
    return results

@route('/healthz')
def healthz():
    fmt = request.query.get("format", "text")
    results = run_checks()
    failed = any(not ok for _, ok, _ in results)
    code = 500 if failed else 200

    if fmt == "text":
        header = f"{'Component':<30}{'Status':<8}Detail"
        lines = [header]
        for name, ok, msg in results:
            status_text = "PASS" if ok else "FAIL"
            lines.append(f"{name:<30}{status_text:<8}{msg}")
        return HTTPResponse("\n".join(lines), status=code, content_type="text/plain")
    
    # Modified JSON response block
    checks_list = [
        {"name": name, "status": "ok" if ok else "error", "message": msg}
        for name, ok, msg in results
    ]

    body = {
        "status": "ok" if not failed else "error",
        "data": {
            "message": "All checks passed" if not failed else "Some checks failed",
            "checks": checks_list  # Moved the checks list here
        }
    }
    return HTTPResponse(json.dumps(body, indent=2), status=code, content_type='application/json')

@route('/metrics')
def metrics():
    results = run_checks()
    lines = [
        "# HELP healthcheck_status Health check status (1=ok,0=error)",
        "# TYPE healthcheck_status gauge"
    ]
    for name, ok, _ in results:
        lines.append(f'healthcheck_status{{check="{name}"}} {1 if ok else 0}')
    return HTTPResponse("\n".join(lines), content_type="text/plain")

if __name__ == '__main__':
    print("Service endpoints available:")
    print("  Healthcheck (Text):  http://0.0.0.0:8080/healthz")
    print("  Healthcheck (JSON):  http://0.0.0.0:8080/healthz?format=json")
    print("  Prometheus metrics:  http://0.0.0.0:8080/metrics")
    run(host='0.0.0.0', port=8080)