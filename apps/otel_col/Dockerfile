# apps/otel_col/Dockerfile
FROM otel/opentelemetry-collector:0.123.0

COPY otel_config.yaml /etc/otelcol-config.yml

ENTRYPOINT ["/otelcol"]
CMD ["--config", "/etc/otelcol-config.yml"]
