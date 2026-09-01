import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)


def configure_tracing():
    resource = Resource.create(
        {
            "service.name": "incident-investigation-platform",
            "service.version": "1.0.0",
            "deployment.environment": os.getenv(
                "DEPLOYMENT_ENVIRONMENT",
                "development",
            ),
        }
    )

    provider = TracerProvider(resource=resource)
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    if otlp_endpoint:
        exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
        )
        provider.add_span_processor(
            BatchSpanProcessor(exporter)
        )
    else:
        provider.add_span_processor(
            SimpleSpanProcessor(
                ConsoleSpanExporter()
            )
        )

    trace.set_tracer_provider(provider)

    return trace.get_tracer(
        "incident-investigation-platform"
    )


def record_incident_trace(data, findings):
    tracer = configure_tracing()
    incident = data["incident"]

    with tracer.start_as_current_span(
        "investigate-incident"
    ) as span:
        span.set_attribute(
            "incident.id",
            incident["id"],
        )
        span.set_attribute(
            "incident.service",
            incident["service"],
        )
        span.set_attribute(
            "incident.finding_count",
            len(findings),
        )

        for finding in findings:
            span.add_event(
                "incident.finding",
                {
                    "severity": finding["severity"],
                    "title": finding["title"],
                    "confidence": finding["confidence"],
                },
            )
