"""
Evaluation tasks for the doc-format benchmark.

Each task has a natural-language question and a ground-truth answer drawn
directly from the source document. The LLM judge scores answers 0–2.
"""

TASKS = [
    {
        "id": "prereq_list",
        "category": "factual_retrieval",
        "question": "List every prerequisite mentioned in this documentation.",
        "ground_truth": (
            "Elastic deployment (Serverless, Elastic Cloud Hosted, or self-managed); "
            "Observability project Kibana instance; "
            "permissions to create API keys; "
            "a system to run the EDOT Collector (Docker, host, or VM); "
            "optional: an application that emits OpenTelemetry metrics"
        ),
    },
    {
        "id": "docker_command",
        "category": "code_extraction",
        "question": "What is the exact Docker command used to run the EDOT Collector?",
        "ground_truth": (
            "docker run --rm "
            "-v $(pwd)/collector-config.yaml:/etc/otel/config.yaml "
            "-p 4317:4317 -p 4318:4318 "
            "docker.elastic.co/observability/otel-collector:latest"
        ),
    },
    {
        "id": "port_conflict_fix",
        "category": "troubleshooting",
        "question": (
            "How do you resolve a 'bind: address already in use' port conflict "
            "when starting the EDOT Collector?"
        ),
        "ground_truth": (
            "Add a telemetry section under 'service' in the YAML config: "
            "service.telemetry.metrics.address: localhost:8889. "
            "You can also verify which process is using the port with: lsof -i :4318 -i :4317"
        ),
    },
    {
        "id": "metric_name",
        "category": "factual_retrieval",
        "question": "What is the name of the custom metric created in the Python example?",
        "ground_truth": "custom.temperature",
    },
    {
        "id": "verify_location",
        "category": "navigation",
        "question": "Where in Kibana can you verify that the custom metrics are flowing in?",
        "ground_truth": "Infrastructure > Metrics Explorer; search for 'custom.temperature'",
    },
    {
        "id": "auth_header",
        "category": "code_extraction",
        "question": (
            "What is the exact format of the Authorization header value "
            "in the OTLP exporter configuration?"
        ),
        "ground_truth": "ApiKey <YOUR_API_KEY>",
    },
    {
        "id": "applies_to",
        "category": "metadata",
        "question": (
            "Which Elastic products and deployment types does this quickstart officially apply to?"
        ),
        "ground_truth": (
            "Elastic Cloud Hosted, Elastic Cloud Serverless, "
            "Elastic Distribution of OpenTelemetry Collector, Elastic Observability; "
            "Serverless Observability projects (Generally available), "
            "Elastic Stack (Generally available), "
            "EDOT Collector (Generally available)"
        ),
    },
    {
        "id": "step_order",
        "category": "reasoning",
        "question": (
            "In what order should you perform the setup steps to get custom "
            "Python metrics flowing into Kibana?"
        ),
        "ground_truth": (
            "1. Create an Elastic API key and note the OTLP ingest endpoint; "
            "2. Configure collector-config.yaml with OTLP receivers, batch processor, "
            "and OTLPHTTP exporter pointing to your Elastic endpoint; "
            "3. Run the EDOT Collector via Docker; "
            "4. Run the Python app that emits OTLP metrics; "
            "5. Verify metrics in Kibana under Infrastructure > Metrics Explorer"
        ),
    },
    {
        "id": "extend_options",
        "category": "comprehension",
        "question": "What are all the ways to extend the basic metrics setup described in this doc?",
        "ground_truth": (
            "Add more receivers to collect additional metrics; "
            "configure the Collector to send logs and traces alongside metrics; "
            "use Metrics Explorer to create custom visualizations and dashboards; "
            "set up alerts based on custom metrics; "
            "aggregate and analyze metric trends over time"
        ),
    },
    {
        "id": "otlp_endpoint",
        "category": "code_extraction",
        "question": (
            "What local endpoint URL does the Python OTLP metric exporter "
            "send metrics to in the example?"
        ),
        "ground_truth": "http://localhost:4318/v1/metrics",
    },
]
