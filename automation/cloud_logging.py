"""Structured logging configuration that works in GCP.

This is mostly default configuration but with a couple of tweaks due to
what Google expects about field naming:
https://cloud.google.com/functions/docs/monitoring/logging.
"""

import logging
import os

import structlog


JSON_LOG_FORMAT = os.environ.get("JSON_LOG_FORMAT", "0") == "1"


def add_log_level(logger, method_name, event_dict):
    """Add the log level under the name "severity", for GCP.

    Otherwise this is just structlog.processors.add_log_level.
    """
    if method_name == "warn":
        # The stdlib has an alias
        method_name = "warning"
    event_dict["severity"] = method_name.upper()
    return event_dict


def rename_event(logger, method_name, event_dict):
    """Rename "event" to "message", for GCP."""
    event_dict["message"] = event_dict.pop("event")
    return event_dict


def configure():
    renderer = (
        structlog.processors.JSONRenderer()
        if JSON_LOG_FORMAT
        else structlog.dev.ConsoleRenderer()
    )
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if JSON_LOG_FORMAT:
        # Use the names "severity" and "message" instead of structlog's
        # defaults of "level" and "event"
        processors.extend([add_log_level, rename_event])
    else:
        processors.append(structlog.processors.add_log_level)
    processors.append(renderer)
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def bind_trace_id(request, project_id):
    """Add the trace id for cloud functions requests.

    Based on https://cloud.google.com/functions/docs/monitoring/logging.

    Call this near the top of your request handler.
    """
    structlog.contextvars.clear_contextvars()
    trace_header = request.headers.get("X-Cloud-Trace-Context")
    if trace_header and project_id:
        trace = trace_header.split("/")
        trace_val = f"projects/{project_id}/traces/{trace[0]}"
        structlog.contextvars.bind_contextvars(
            **{"logging.googleapis.com/trace": trace_val}
        )
