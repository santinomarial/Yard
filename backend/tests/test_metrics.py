from app.core.metrics import MetricsRegistry


def test_metrics_render_prometheus_counters_and_summaries() -> None:
    registry = MetricsRegistry()
    registry.increment("reservation_conflicts_total", code="listing_already_reserved")
    registry.observe("search_latency_seconds", 0.125, strategy="hybrid")

    output = registry.render()

    assert 'reservation_conflicts_total{code="listing_already_reserved"} 1.0' in output
    assert 'search_latency_seconds_count{strategy="hybrid"} 1' in output
    assert 'search_latency_seconds_sum{strategy="hybrid"} 0.125' in output
