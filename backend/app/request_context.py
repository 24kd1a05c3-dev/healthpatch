"""Correlation metadata only: never store credentials or patient payloads in logs."""
import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

request_id_context = ContextVar('request_id', default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {'timestamp': datetime.now(timezone.utc).isoformat(), 'level': record.levelname,
                'logger': record.name, 'event': record.getMessage()}
        for key in ('request_id', 'method', 'route', 'status_code', 'duration_ms', 'error_type'):
            value = getattr(record, key, None)
            if value is not None:
                data[key] = value
        return json.dumps(data)
