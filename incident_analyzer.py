import argparse
import json
from telemetry import record_incident_trace
from datetime import datetime, timezone
from pathlib import Path


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def add_finding(findings, severity, title, evidence, recommendation, confidence):
    findings.append(
        {
            "severity": severity,
            "title": title,
            "evidence": evidence,
            "recommendation": recommendation,
            "confidence": confidence,
        }
    )


def analyze_incident(data):
    findings = []

    incident_time = parse_time(data["incident"]["detected_at"])
    metrics = data.get("metrics", {})
    containers = data.get("containers", [])
    deployments = data.get("deployments", [])
    logs = data.get("logs", [])

    error_rate = metrics.get("http_error_rate_percent", 0)
    latency = metrics.get("average_latency_ms", 0)
    cpu = metrics.get("cpu_percent", 0)
    memory = metrics.get("memory_percent", 0)

    if error_rate >= 5:
        add_finding(
            findings,
            "HIGH",
            "Elevated HTTP error rate",
            f"HTTP error rate reached {error_rate}%.",
            "Inspect recent application errors and compare behavior with the last deployment.",
            "High",
        )

    if latency >= 1000:
        add_finding(
            findings,
            "MEDIUM",
            "High application latency",
            f"Average response latency reached {latency} ms.",
            "Review slow requests, downstream dependencies, and resource saturation.",
            "High",
        )

    if cpu >= 85:
        add_finding(
            findings,
            "HIGH",
            "CPU saturation",
            f"CPU utilization reached {cpu}%.",
            "Inspect expensive processes and scale capacity after human approval.",
            "High",
        )

    if memory >= 85:
        add_finding(
            findings,
            "HIGH",
            "Memory pressure",
            f"Memory utilization reached {memory}%.",
            "Check for memory leaks and review container memory limits.",
            "High",
        )

    for container in containers:
        restarts = container.get("restart_count", 0)

        if restarts >= 3:
            add_finding(
                findings,
                "HIGH",
                f"Repeated container restarts: {container['name']}",
                f"The container restarted {restarts} times.",
                "Inspect container logs, health probes, exit codes, and resource limits.",
                "High",
            )

    recent_deployments = []

    for deployment in deployments:
        deployed_at = parse_time(deployment["deployed_at"])
        minutes_before_incident = (
            incident_time - deployed_at
        ).total_seconds() / 60

        if 0 <= minutes_before_incident <= 60:
            recent_deployments.append(
                {
                    "version": deployment["version"],
                    "minutes": round(minutes_before_incident),
                    "status": deployment.get("status", "unknown"),
                }
            )

    if recent_deployments and error_rate >= 5:
        deployment = recent_deployments[0]

        add_finding(
            findings,
            "CRITICAL",
            "Recent deployment correlates with service degradation",
            (
                f"Version {deployment['version']} was deployed "
                f"{deployment['minutes']} minutes before the incident, "
                f"while HTTP errors reached {error_rate}%."
            ),
            (
                "Compare the new release with the previous stable version. "
                "Request human approval before rollback."
            ),
            "High",
        )

    error_logs = [
        log for log in logs
        if log.get("level", "").upper() in {"ERROR", "CRITICAL"}
    ]

    if error_logs:
        messages = "; ".join(
            log.get("message", "Unknown error")
            for log in error_logs[:3]
        )

        add_finding(
            findings,
            "HIGH",
            "Application error events detected",
            messages,
            "Review stack traces and affected dependencies before taking recovery action.",
            "Medium",
        )

    severity_order = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
    }

    findings.sort(
        key=lambda item: severity_order[item["severity"]],
        reverse=True,
    )

    return findings


def create_report(data, findings):
    incident = data["incident"]

    lines = [
        "# Incident Investigation Report",
        "",
        f"**Incident ID:** {incident['id']}",
        f"**Service:** {incident['service']}",
        f"**Detected at:** {incident['detected_at']}",
        f"**Total findings:** {len(findings)}",
        "",
        "## Probable Root Causes and Evidence",
        "",
    ]

    if not findings:
        lines.append("No configured incident conditions were detected.")
        return "\n".join(lines)

    for finding in findings:
        lines.extend(
            [
                f"### {finding['severity']}: {finding['title']}",
                "",
                f"**Evidence:** {finding['evidence']}",
                "",
                f"**Confidence:** {finding['confidence']}",
                "",
                f"**Recommendation:** {finding['recommendation']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Recovery Control",
            "",
            (
                "No restart, rollback, or infrastructure modification was "
                "executed automatically. Recovery actions require human approval."
            ),
        ]
    )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Correlate incident logs, metrics, deployments, and container events."
    )
    parser.add_argument("incident_data", help="Path to incident JSON data")
    parser.add_argument(
        "--output",
        default="incident-report.md",
        help="Markdown report output path",
    )
    args = parser.parse_args()

    data_path = Path(args.incident_data)

    if not data_path.exists():
        raise SystemExit(f"Incident data not found: {data_path}")

    with data_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    findings = analyze_incident(data)
    record_incident_trace(data, findings)
    report = create_report(data, findings)

    Path(args.output).write_text(report, encoding="utf-8")

    print(report)
    print(f"\nReport saved to {args.output}")


if __name__ == "__main__":
    main()
