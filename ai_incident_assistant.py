import argparse
import json
import os
from pathlib import Path
from urllib import request, error


def build_incident_prompt(report):
    return f"""
You are an experienced Site Reliability and DevOps incident assistant.

Review the evidence-based incident report below.

Provide:
1. A concise incident summary.
2. The most probable root cause.
3. Evidence supporting the conclusion.
4. Immediate containment steps.
5. Safe recovery recommendations.
6. Post-incident prevention actions.
7. A confidence level.

Do not invent evidence.
Do not automatically authorize restarts, rollbacks, or infrastructure changes.
Every recovery action must require human approval.

Incident report:

{report}
"""


def request_ai_analysis(prompt):
    api_key = os.getenv("AI_API_KEY")
    api_url = os.getenv(
        "AI_API_URL",
        "https://api.openai.com/v1/chat/completions",
    )
    model = os.getenv("AI_MODEL", "gpt-4o-mini")

    if not api_key:
        raise RuntimeError(
            "AI_API_KEY is not configured. "
            "Store it securely as an environment variable or GitHub secret."
        )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Provide evidence-based incident investigation guidance. "
                    "Never execute or authorize production recovery actions."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
    }

    api_request = request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(api_request, timeout=60) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")

        raise RuntimeError(
            f"AI API failed with status {exc.code}: {body}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(
            f"Unable to reach AI API: {exc.reason}"
        ) from exc

    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            "AI API returned an unexpected response format."
        ) from exc


def main():
    parser = argparse.ArgumentParser(
        description="Generate AI-assisted incident investigation guidance."
    )
    parser.add_argument(
        "report",
        help="Path to the evidence-based incident report",
    )
    parser.add_argument(
        "--output",
        default="ai-incident-summary.md",
        help="AI summary output path",
    )
    args = parser.parse_args()

    report_path = Path(args.report)

    if not report_path.exists():
        raise SystemExit(
            f"Incident report not found: {report_path}"
        )

    report = report_path.read_text(encoding="utf-8")
    prompt = build_incident_prompt(report)
    analysis = request_ai_analysis(prompt)

    output = "\n".join(
        [
            "# AI-Assisted Incident Summary",
            "",
            analysis,
            "",
            (
                "> Human approval is required before any restart, "
                "rollback, or infrastructure change."
            ),
        ]
    )

    Path(args.output).write_text(
        output,
        encoding="utf-8",
    )

    print(output)
    print(f"\nAI summary saved to {args.output}")


if __name__ == "__main__":
    main()
