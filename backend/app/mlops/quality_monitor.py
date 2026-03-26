from collections import deque

_LATENCY_WINDOW = deque(maxlen=100)
_RELEVANCE_KEYWORDS = [
    "pakistan",
    "history",
    "affairs",
    "essay",
    "fpsc",
    "current affairs",
    "general knowledge",
    "css exam",
]


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = (len(sorted_values) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def response_relevance_score(response_text: str) -> float:
    text = response_text.lower()
    matches = sum(1 for keyword in _RELEVANCE_KEYWORDS if keyword in text)
    return round(matches / len(_RELEVANCE_KEYWORDS), 4)


def record_latency(latency_ms: float) -> dict[str, float]:
    _LATENCY_WINDOW.append(float(latency_ms))
    values = list(_LATENCY_WINDOW)
    return {
        "model_latency_p50_p95_p99": {
            "p50": round(_percentile(values, 0.50), 2),
            "p95": round(_percentile(values, 0.95), 2),
            "p99": round(_percentile(values, 0.99), 2),
        }
    }


def analyze_response(
    response_text: str, latency_ms: float
) -> dict[str, float | dict[str, float]]:
    latency = record_latency(latency_ms)["model_latency_p50_p95_p99"]
    return {
        "response_relevance_score": response_relevance_score(response_text),
        "response_length_chars": len(response_text),
        "model_latency_p50_p95_p99": latency,
    }
