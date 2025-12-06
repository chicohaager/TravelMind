"""
Prometheus Metrics Middleware and Endpoint

Collects application metrics for monitoring:
- HTTP request counts and latencies
- Active requests
- Error rates
- Database connection stats
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import threading


@dataclass
class MetricsBucket:
    """Stores metrics for a single endpoint."""
    request_count: int = 0
    error_count: int = 0
    total_latency: float = 0.0
    latency_buckets: Dict[float, int] = field(default_factory=lambda: defaultdict(int))


class MetricsCollector:
    """Thread-safe metrics collector."""

    # Histogram buckets for latency (in seconds)
    LATENCY_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def __init__(self):
        self._lock = threading.Lock()
        self._metrics: Dict[str, MetricsBucket] = defaultdict(MetricsBucket)
        self._active_requests = 0
        self._start_time = time.time()

    def record_request(self, method: str, path: str, status_code: int, latency: float):
        """Record a completed request."""
        # Normalize path to avoid high cardinality
        normalized_path = self._normalize_path(path)
        key = f"{method}:{normalized_path}"

        with self._lock:
            bucket = self._metrics[key]
            bucket.request_count += 1
            bucket.total_latency += latency

            if status_code >= 400:
                bucket.error_count += 1

            # Record in histogram buckets
            for b in self.LATENCY_BUCKETS:
                if latency <= b:
                    bucket.latency_buckets[b] += 1

    def increment_active(self):
        """Increment active request counter."""
        with self._lock:
            self._active_requests += 1

    def decrement_active(self):
        """Decrement active request counter."""
        with self._lock:
            self._active_requests -= 1

    def _normalize_path(self, path: str) -> str:
        """Normalize path to reduce cardinality."""
        # Replace numeric IDs with placeholder
        parts = path.split('/')
        normalized = []
        for part in parts:
            if part.isdigit():
                normalized.append(':id')
            elif part and len(part) > 30:
                # Truncate very long segments (likely UUIDs or tokens)
                normalized.append(':param')
            else:
                normalized.append(part)
        return '/'.join(normalized)

    def get_prometheus_metrics(self) -> str:
        """Generate Prometheus-format metrics output."""
        lines = []

        # App info
        uptime = time.time() - self._start_time
        lines.append("# HELP travelmind_uptime_seconds Application uptime in seconds")
        lines.append("# TYPE travelmind_uptime_seconds gauge")
        lines.append(f"travelmind_uptime_seconds {uptime:.2f}")
        lines.append("")

        # Active requests
        lines.append("# HELP travelmind_http_requests_active Current number of active HTTP requests")
        lines.append("# TYPE travelmind_http_requests_active gauge")
        with self._lock:
            lines.append(f"travelmind_http_requests_active {self._active_requests}")
        lines.append("")

        # Request totals
        lines.append("# HELP travelmind_http_requests_total Total number of HTTP requests")
        lines.append("# TYPE travelmind_http_requests_total counter")

        # Error totals
        lines.append("# HELP travelmind_http_errors_total Total number of HTTP errors (4xx/5xx)")
        lines.append("# TYPE travelmind_http_errors_total counter")

        # Latency histogram
        lines.append("# HELP travelmind_http_request_duration_seconds HTTP request latency histogram")
        lines.append("# TYPE travelmind_http_request_duration_seconds histogram")

        with self._lock:
            for key, bucket in self._metrics.items():
                method, path = key.split(':', 1)
                labels = f'method="{method}",path="{path}"'

                # Request count
                lines.append(f'travelmind_http_requests_total{{{labels}}} {bucket.request_count}')

                # Error count
                lines.append(f'travelmind_http_errors_total{{{labels}}} {bucket.error_count}')

                # Latency histogram buckets
                cumulative = 0
                for b in self.LATENCY_BUCKETS:
                    cumulative += bucket.latency_buckets.get(b, 0)
                    lines.append(f'travelmind_http_request_duration_seconds_bucket{{{labels},le="{b}"}} {cumulative}')
                lines.append(f'travelmind_http_request_duration_seconds_bucket{{{labels},le="+Inf"}} {bucket.request_count}')
                lines.append(f'travelmind_http_request_duration_seconds_sum{{{labels}}} {bucket.total_latency:.6f}')
                lines.append(f'travelmind_http_request_duration_seconds_count{{{labels}}} {bucket.request_count}')

        lines.append("")
        return '\n'.join(lines)


# Global metrics collector instance
metrics_collector = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics."""

    # Paths to exclude from metrics
    EXCLUDE_PATHS = {'/metrics', '/health', '/favicon.ico'}

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip metrics collection for excluded paths
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        metrics_collector.increment_active()
        start_time = time.time()

        try:
            response = await call_next(request)
            latency = time.time() - start_time

            metrics_collector.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency=latency
            )

            return response
        finally:
            metrics_collector.decrement_active()
