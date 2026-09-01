FROM python:3.12-slim

LABEL maintainer="Hemant Sharma"
LABEL description="AI-assisted incident investigation platform"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system incident \
    && useradd --system --gid incident incident

COPY incident_analyzer.py .
COPY ai_incident_assistant.py .
COPY metrics_exporter.py .
COPY examples/ ./examples/

RUN chown -R incident:incident /app

USER incident

ENTRYPOINT ["python", "incident_analyzer.py"]

CMD ["examples/deployment-failure.json", "--output", "incident-report.md"]
