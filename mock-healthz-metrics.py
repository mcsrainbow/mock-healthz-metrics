from bottle import route, run, request, HTTPResponse
import random, json

INTERNAL_APIS = ["billing", "usage"]
EXTERNAL_APIS = ["alipay", "sms"]

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
        timeout = random.random() < 0.02  # ~2% timeout
        svc = f"{prefix}/{name}"

        if timeout:
            msg = f"{svc} timed out"
            ok = False
        else:
            error = random.random() < 0.13  # ~13% returned error
            if error:
                msg = f"{svc} returned error"
                ok = False
            else:
                latency = random.randint(50, 500)
                msg = f"{svc} OK ({latency}ms)"
                ok = True

        results.append((svc, ok, msg))
    return results

def run_checks():
    # Critical checks that affect overall health status
    critical_results = [
        check_db_connection(),
        check_config_service()
    ]

    # Internal APIs depend on upstream and affect health status
    if all(ok for _, ok, _ in critical_results):
        critical_results += check_apis(INTERNAL_APIS, "internal_api")
    else:
        for name in INTERNAL_APIS:
            svc = f"internal_api/{name}"
            critical_results.append((svc, False, "Skipped due to upstream failure"))

    # External APIs are independent and don't affect health status
    external_results = check_apis(EXTERNAL_APIS, "external_api")
    
    return critical_results, external_results

@route('/healthz')
def healthz():
    fmt = request.query.get("format", "text")
    critical_results, external_results = run_checks()
    
    # Only critical checks determine overall health status
    failed = any(not ok for _, ok, _ in critical_results)
    code = 500 if failed else 200

    if fmt == "text":
        header = f"{'CHECK':<24}{'STATUS':<8}MESSAGE"
        lines = [header]
        
        # Critical checks
        lines.append("----- Critical -----")
        for name, ok, msg in critical_results:
            status_text = "PASS" if ok else "FAIL"
            lines.append(f"{name:<24}{status_text:<8}{msg}")
        
        # External checks
        lines.append("----- External -----")
        for name, ok, msg in external_results:
            status_text = "PASS" if ok else "FAIL"
            lines.append(f"{name:<24}{status_text:<8}{msg}")
            
        return HTTPResponse("\n".join(lines), status=code, content_type='text/plain')

    # JSON format with separated critical and external checks
    critical_checks = [
        {"name": name, "status": "ok" if ok else "error", "message": msg}
        for name, ok, msg in critical_results
    ]
    
    external_checks = [
        {"name": name, "status": "ok" if ok else "error", "message": msg}
        for name, ok, msg in external_results
    ]

    body = {
        "status": "ok" if not failed else "error",
        "data": {
            "message": "All critical checks passed" if not failed else "Some critical checks failed",
            "checks": {
                "critical": critical_checks,
                "external": external_checks
            }
        }
    }
    return HTTPResponse(json.dumps(body, indent=2), status=code, content_type='application/json')

@route('/metrics')
def metrics():
    critical_results, external_results = run_checks()
    lines = [
        "# HELP healthcheck_status Health check status (1=ok,0=error)",
        "# TYPE healthcheck_status gauge"
    ]
    
    # Critical checks
    for name, ok, _ in critical_results:
        lines.append(f'healthcheck_status{{check="{name}",type="critical"}} {1 if ok else 0}')
    
    # External checks
    for name, ok, _ in external_results:
        lines.append(f'healthcheck_status{{check="{name}",type="external"}} {1 if ok else 0}')
        
    return HTTPResponse("\n".join(lines), content_type='text/plain')

if __name__ == '__main__':
    print("Service endpoints available:")
    print("  Healthcheck (Text):  http://0.0.0.0:8080/healthz")
    print("  Healthcheck (JSON):  http://0.0.0.0:8080/healthz?format=json")
    print("  Prometheus metrics:  http://0.0.0.0:8080/metrics")
    run(host='0.0.0.0', port=8080)