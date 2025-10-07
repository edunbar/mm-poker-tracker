"""
Business metrics service for structured logging to GCP.

This service logs business events as structured JSON that GCP Cloud Logging
automatically indexes, enabling easy querying and dashboard creation.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def log_metric(event: str, properties: Optional[Dict[str, Any]] = None) -> None:
    """
    Log a business metric event as structured JSON for GCP Cloud Logging.

    GCP Cloud Logging automatically parses and indexes JSON log entries,
    making them queryable in Logs Explorer and usable for log-based metrics.

    Args:
        event: The event name (e.g., "game_created", "session_uploaded")
        properties: Optional dictionary of event properties (e.g., game_id, public_code)

    Example:
        log_metric("game_created", {
            "game_id": "123e4567-e89b-12d3-a456-426614174000",
            "public_code": "ABC123"
        })

    GCP Query Example:
        jsonPayload.event="session_uploaded"
        AND jsonPayload.properties.game_id="some-game-id"
        AND timestamp >= "2025-10-01T00:00:00Z"
    """
    if properties is None:
        properties = {}

    # Create structured log entry
    metric_data = {
        "event": event,
        "properties": properties,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Log as JSON string - GCP automatically parses JSON in log messages
    logger.info(json.dumps(metric_data))
