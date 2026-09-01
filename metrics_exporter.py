import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


def load_metrics(data_path):
    with Path(data_path).open("r", encoding="utf-8") as file:
        data = json.load(file)

    metrics = data.get("metrics", {})
    containers = data.get("containers", [])

    lines = [
        "# HELP incident_http_error_rate_percent HTTP error rate percentage.",
        "# TYPE incident_http_error_rate_percent gauge",
        (
            "incident_http_error_rate_percent "
            f"{metrics.get('http_error_rate_percent', 0)}"
        ),
        "# HELP incident_average_latency_ms Average application latency.",
        "# TYPE incident_average_latency_ms gauge",
        (
            "incident_average_latency_ms "
            f"{metrics.get('average_latency_ms', 0)}"
        ),
        "# HELP incident_cpu_percent CPU utilization percentage.",
        "# TYPE incident_cpu_percent gauge",
        f"incident_cpu_percent {metrics.get('cpu_percent', 0)}",
        "# HELP incident_memory_percent Memory utilization percentage.",
        "# TYPE incident_memory_percent gauge",
        f"incident_memory_percent {metrics.get('memory_percent', 0)}",
        "# HELP incident_container_restarts_total Container restart count.",
        "# TYPE incident_container_restarts_total gauge",
    ]

    for container in containers:
        name = container.get("name", "unknown")
        restarts = container.get("restart_count", 0)

        lines.append(
            f'incident_container_restarts_total{{container="{name}"}} {restarts}'
        )

    return "\n".join(lines) + "\n"


class MetricsHandler(BaseHTTPRequestHandler):
    data_path = "examples/deployment-failure.json"

    def do_GET(self):
        if self.path == "/health":
            body = b"healthy\n"
            status = 200
            content_type = "text/plain"
        elif self.path == "/metrics":
            body = load_metrics(self.data_path).encode("utf-8")
            status = 200
            content_type = "text/plain; version=0.0.4"
        else:
            body = b"not found\n"
            status = 404
            content_type = "text/plain"

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(
            f"{self.client_address[0]} - {format % args}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Expose incident metrics in Prometheus format."
    )
    parser.add_argument(
        "--data",
        default="examples/deployment-failure.json",
        help="Incident JSON data path",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Metrics server port",
    )
    args = parser.parse_args()

    MetricsHandler.data_path = args.data

    server = HTTPServer(
        ("0.0.0.0", args.port),
        MetricsHandler,
    )

    print(
        f"Metrics exporter running on port {args.port}"
    )
    print(
        f"Metrics available at http://localhost:{args.port}/metrics"
    )

    server.serve_forever()


if __name__ == "__main__":
    main()
