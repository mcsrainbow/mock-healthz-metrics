from bottle import route, run, request, HTTPResponse
import random, json
import threading
import time
import concurrent.futures

INTERNAL_APIS = ["billing", "usage"]
EXTERNAL_APIS = ["alipay", "sms"]

# Global cache for the latest check results
last_check_results = {
    "critical": [],
    "external": [],
    "timestamp": 0
}

# Maximum timeout per check (seconds)
CHECK_TIMEOUT = 5

# Background check interval (seconds)
CHECK_INTERVAL = 5

def check_db_connection():
    # Simulate timeout
    if random.random() < 0.02:
        time.sleep(CHECK_TIMEOUT + 1)
        return ("db_connection", False, "db_connection timed out")
    ok = random.random() < 0.98
    msg = "Database is connected" if ok else "Database connection failed"
    return ("db_connection", ok, msg)

def check_config_service():
    # Simulate timeout
    if random.random() < 0.02:
        time.sleep(CHECK_TIMEOUT + 1)
        return ("config_service", False, "config_service timed out")
    ok = random.random() < 0.98
    msg = "Config service is reachable" if ok else "Config service error"
    return ("config_service", ok, msg)

def check_apis(api_list, prefix):
    results = []
    for name in api_list:
        timeout = random.random() < 0.02  # ~2% timeout
        svc = f"{prefix}/{name}"
        if timeout:
            time.sleep(CHECK_TIMEOUT + 1)
            msg = f"{svc} timed out"
            ok = False
        else:
            error = random.random() < 0.13  # ~13% returned error
            if error:
                msg = f"{svc} returned error"
                ok = False
            else:
                latency = random.randint(50, 500)
                time.sleep(latency / 1000.0)  # Simulate real latency
                msg = f"{svc} OK ({latency}ms)"
                ok = True
        results.append((svc, ok, msg))
    return results

# Run all checks concurrently with timeout

def run_checks():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Concurrently run critical checks
        critical_futures = {
            "db_connection": executor.submit(check_db_connection),
            "config_service": executor.submit(check_config_service)
        }
        critical_results = []
        for name, future in critical_futures.items():
            try:
                critical_results.append(future.result(timeout=CHECK_TIMEOUT))
            except concurrent.futures.TimeoutError:
                critical_results.append((name, False, f"{name} timed out"))

        # Internal API checks
        if all(ok for _, ok, _ in critical_results):
            internal_futures = {
                n: executor.submit(lambda name: check_apis([name], "internal_api")[0], n)
                for n in INTERNAL_APIS
            }
            for name, future in internal_futures.items():
                try:
                    critical_results.append(future.result(timeout=CHECK_TIMEOUT))
                except concurrent.futures.TimeoutError:
                    critical_results.append((f"internal_api/{name}", False, f"internal_api/{name} timed out"))
        else:
            for name in INTERNAL_APIS:
                svc = f"internal_api/{name}"
                critical_results.append((svc, False, "Skipped due to upstream failure"))

        # External API checks
        external_results = []
        external_futures = {
            n: executor.submit(lambda name: check_apis([name], "external_api")[0], n)
            for n in EXTERNAL_APIS
        }
        for name, future in external_futures.items():
            try:
                external_results.append(future.result(timeout=CHECK_TIMEOUT))
            except concurrent.futures.TimeoutError:
                external_results.append((f"external_api/{name}", False, f"external_api/{name} timed out"))

    return critical_results, external_results

# Background thread to periodically refresh check results
def background_check_loop():
    while True:
        critical, external = run_checks()
        last_check_results["critical"] = critical
        last_check_results["external"] = external
        last_check_results["timestamp"] = time.time()
        time.sleep(CHECK_INTERVAL)

# Start the background thread
threading.Thread(target=background_check_loop, daemon=True).start()

@route('/healthz')
def healthz():
    fmt = request.query.get("format")
    # Only read from the cache, do not run checks in real time
    critical_results = last_check_results["critical"]
    external_results = last_check_results["external"]
    ts = last_check_results["timestamp"]
    snapshot_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
    failed = any(not ok for _, ok, _ in critical_results)
    code = 500 if failed else 200

    # Only output JSON if explicitly requested with format=json
    if fmt == "json":
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
                "snapshot_time": snapshot_str,
                "checks": {
                    "critical": critical_checks,
                    "external": external_checks
                }
            }
        }
        return HTTPResponse(json.dumps(body, indent=2), status=code, content_type='application/json')

    # Default to text format for all other cases (including None, "text", or any other value)
    title = f"HEALTH CHECK SNAPSHOT [{snapshot_str}]"
    border = "-" * len(title)
    table_header = f"{'CHECK':<24}{'STATUS':<8}MESSAGE"
    lines = [title, border, table_header]
    lines.append("----- CRITICAL -----")
    for name, ok, msg in critical_results:
        status_text = "✔" if ok else "✖"
        lines.append(f"{name:<24}{status_text:<8}{msg}")
    lines.append("----- EXTERNAL -----")
    for name, ok, msg in external_results:
        status_text = "✔" if ok else "✖"
        lines.append(f"{name:<24}{status_text:<8}{msg}")
    return HTTPResponse("\n".join(lines), status=code, content_type='text/plain')

@route('/metrics')
def metrics():
    # Only read from the cache
    critical_results = last_check_results["critical"]
    external_results = last_check_results["external"]
    lines = [
        "# HELP healthcheck_status Health check status (1=ok,0=error)",
        "# TYPE healthcheck_status gauge"
    ]
    for name, ok, _ in critical_results:
        lines.append(f'healthcheck_status{{check="{name}",type="critical"}} {1 if ok else 0}')
    for name, ok, _ in external_results:
        lines.append(f'healthcheck_status{{check="{name}",type="external"}} {1 if ok else 0}')
    return HTTPResponse("\n".join(lines), content_type='text/plain')

if __name__ == '__main__':
    print("Service endpoints available:")
    print("  Healthcheck (Text):  http://0.0.0.0:8080/healthz")
    print("  Healthcheck (JSON):  http://0.0.0.0:8080/healthz?format=json")
    print("  Prometheus metrics:  http://0.0.0.0:8080/metrics")
    run(host='0.0.0.0', port=8080)