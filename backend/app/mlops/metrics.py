from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

REGISTRY = CollectorRegistry()

# Counter: total number of chat requests
# Labels: model (gpt/claude/gemini), status (success/error), endpoint (chat/stream)
chat_requests_total = Counter(
    "css_prep_chat_requests_total",
    "Total number of chat requests",
    ["model", "status", "endpoint"],
    registry=REGISTRY,
)

# Histogram: LLM response latency in seconds
# Labels: model
# Buckets: 0.5s, 1s, 2s, 5s, 10s, 20s, 30s
chat_latency_seconds = Histogram(
    "css_prep_chat_latency_seconds",
    "LLM response latency in seconds",
    ["model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0],
    registry=REGISTRY,
)

# Counter: total auth events
# Labels: event (register/login/logout), status (success/error)
auth_events_total = Counter(
    "css_prep_auth_events_total",
    "Total authentication events",
    ["event", "status"],
    registry=REGISTRY,
)

# Gauge: active users in the last 5 minutes (approximation)
active_users_gauge = Gauge(
    "css_prep_active_users",
    "Approximate number of active users",
    registry=REGISTRY,
)

# Counter: total tokens used per model (approximate from response length)
tokens_used_total = Counter(
    "css_prep_tokens_used_total",
    "Approximate total tokens used",
    ["model"],
    registry=REGISTRY,
)

# Histogram: request prompt length in characters
prompt_length_histogram = Histogram(
    "css_prep_prompt_length_chars",
    "Length of user prompts in characters",
    buckets=[50, 100, 200, 500, 1000, 2000],
    registry=REGISTRY,
)


def record_chat_request(
    model: str,
    status: str,
    endpoint: str,
    latency_seconds: float,
    prompt_length: int,
    response_length: int,
) -> None:
    """
    Convenience function to record all metrics for one chat request.
    Call this at the end of every /chat and /chat/stream request.
    """
    chat_requests_total.labels(
        model=model, status=status, endpoint=endpoint
    ).inc()
    chat_latency_seconds.labels(model=model).observe(latency_seconds)
    prompt_length_histogram.observe(prompt_length)
    # Approximate token count: 1 token ≈ 4 chars
    approx_tokens = response_length // 4
    tokens_used_total.labels(model=model).inc(approx_tokens)
