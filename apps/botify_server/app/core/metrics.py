import os
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.metrics import set_meter_provider
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

# Determine OTLP endpoint and protocol
endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "otelcol:4317")
protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "")

if protocol.startswith("http"):
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as HTTPMetricExporter
    exporter = HTTPMetricExporter(endpoint=endpoint, insecure=True)
else:
    exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)

# Set up a periodic reader (default export interval: 30s)
export_interval = int(os.getenv("OTEL_METRIC_EXPORT_INTERVAL_MS", "30000"))
reader = PeriodicExportingMetricReader(exporter, export_interval_millis=export_interval)

# Resource with service identity
resource = Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "botify-server")})

# Meter provider initialization
provider = MeterProvider(resource=resource, metric_readers=[reader])
set_meter_provider(provider)

# Create a meter and instruments
# meter = get_meter(__name__)
# CUSTOM_REQUEST_COUNT = meter.create_counter(
#     "custom.http.request.count",  # Renamed to avoid name collision
#     unit="1",
#     description="Custom HTTP request counter (not currently used)"
# )
    