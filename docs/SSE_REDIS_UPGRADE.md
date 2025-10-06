# SSE Redis Pub/Sub Upgrade Guide

## Overview

This guide explains how to migrate the Live Game SSE infrastructure from in-memory connection storage to Redis Pub/Sub for production multi-instance deployment.

**Current Implementation**: In-memory connection registry (single-instance only)
**Target Implementation**: Redis Pub/Sub (multi-instance with load balancing)

---

## Why Redis is Needed

### Current Limitation: Single Instance Only

The in-memory connection storage in `src/routes/live_game_sse.py` uses a Python dictionary:

```python
# In-memory storage - NOT suitable for multi-instance
_connections: Dict[str, Dict[str, queue.Queue]] = {}
```

**Problem**: Each server instance has its own connection registry. When a transaction is approved on Instance A, only clients connected to Instance A receive the event. Clients connected to Instance B never get the update.

**Example Scenario**:
```
Player 1 → Load Balancer → Instance A (connected via SSE)
Admin   → Load Balancer → Instance B (approves transaction)

Result: Player 1 never receives the transaction_approved event!
```

### Solution: Redis Pub/Sub

Redis Pub/Sub provides a centralized message broker that all instances can publish to and subscribe from:

```
Instance A → Redis Pub/Sub ← Instance B
    ↓                            ↓
 Player 1                      Admin

Admin approves transaction → Instance B → Publishes to Redis
                                            ↓
                                   Instance A receives → Player 1 gets event ✅
```

---

## Prerequisites

1. **Redis Server**: Version 6.0 or higher
2. **Python Dependencies**:
   ```bash
   pip install redis==5.0.0
   ```

---

## Migration Steps

### Step 1: Set Up Redis

#### Option A: Docker (Development/Staging)

```bash
# Run Redis in Docker
docker run -d \
  --name poker-redis \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --requirepass your_redis_password

# Verify connection
docker exec -it poker-redis redis-cli
> AUTH your_redis_password
> PING
PONG
```

#### Option B: GCP Memorystore (Production)

```bash
# Create Redis instance
gcloud redis instances create poker-redis \
  --size=1 \
  --region=us-central1 \
  --tier=basic \
  --redis-version=redis_6_x

# Get connection details
gcloud redis instances describe poker-redis \
  --region=us-central1 \
  --format="get(host,port,authString)"
```

#### Option C: Managed Redis Services
- **AWS ElastiCache**: https://aws.amazon.com/elasticache/redis/
- **Azure Cache for Redis**: https://azure.microsoft.com/en-us/services/cache/
- **Redis Cloud**: https://redis.com/redis-enterprise-cloud/

---

### Step 2: Update Environment Variables

Add to `.env` or environment configuration:

```bash
# Redis Configuration
REDIS_HOST=127.0.0.1          # or GCP Memorystore IP
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
REDIS_DB=0
REDIS_SSL=false               # true for production
```

---

### Step 3: Create Redis Pub/Sub Manager

Create `src/infrastructure/redis_pubsub.py`:

```python
"""
Redis Pub/Sub manager for SSE event broadcasting.
"""

import json
import redis
import os
from typing import Callable, Dict
import threading
import logging

logger = logging.getLogger(__name__)


class RedisPubSubManager:
    """
    Manages Redis Pub/Sub for broadcasting SSE events across multiple instances.

    Events are published to channels named: `live_game:{live_game_id}`
    All server instances subscribe to these channels and forward events to their connected clients.
    """

    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD'),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True,
            ssl=os.getenv('REDIS_SSL', 'false').lower() == 'true'
        )

        self.pubsub = self.redis_client.pubsub()
        self.subscriptions: Dict[str, Callable] = {}  # channel -> callback
        self.listener_thread = None

    def publish_event(self, live_game_id: str, event_type: str, data: dict):
        """
        Publish event to Redis channel for a live game.

        Args:
            live_game_id: Live game UUID
            event_type: Event name (e.g., "transaction_created")
            data: Event payload
        """
        channel = f"live_game:{live_game_id}"
        message = json.dumps({
            'event_type': event_type,
            'data': data
        })

        try:
            self.redis_client.publish(channel, message)
            logger.info(f"Published {event_type} to {channel}")
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")

    def subscribe(self, live_game_id: str, callback: Callable[[str, dict], None]):
        """
        Subscribe to events for a live game.

        Args:
            live_game_id: Live game UUID
            callback: Function to call when event received: callback(event_type, data)
        """
        channel = f"live_game:{live_game_id}"

        # Store callback
        self.subscriptions[channel] = callback

        # Subscribe to channel
        self.pubsub.subscribe(channel)

        # Start listener thread if not already running
        if self.listener_thread is None or not self.listener_thread.is_alive():
            self.listener_thread = threading.Thread(
                target=self._listen_for_messages,
                daemon=True
            )
            self.listener_thread.start()

    def unsubscribe(self, live_game_id: str):
        """
        Unsubscribe from events for a live game.

        Args:
            live_game_id: Live game UUID
        """
        channel = f"live_game:{live_game_id}"

        # Remove callback
        self.subscriptions.pop(channel, None)

        # Unsubscribe from channel
        self.pubsub.unsubscribe(channel)

    def _listen_for_messages(self):
        """
        Background thread that listens for Redis Pub/Sub messages.
        """
        logger.info("Redis Pub/Sub listener started")

        for message in self.pubsub.listen():
            if message['type'] == 'message':
                channel = message['channel']

                # Get callback for this channel
                callback = self.subscriptions.get(channel)
                if callback:
                    try:
                        # Parse message
                        payload = json.loads(message['data'])
                        event_type = payload['event_type']
                        data = payload['data']

                        # Call callback
                        callback(event_type, data)
                    except Exception as e:
                        logger.error(f"Error processing message from {channel}: {e}")


# Global instance
_redis_pubsub_manager = None


def get_redis_pubsub_manager() -> RedisPubSubManager:
    """Get or create the global Redis Pub/Sub manager."""
    global _redis_pubsub_manager
    if _redis_pubsub_manager is None:
        _redis_pubsub_manager = RedisPubSubManager()
    return _redis_pubsub_manager
```

---

### Step 4: Update SSE Routes

Modify `src/routes/live_game_sse.py`:

```python
from infrastructure.redis_pubsub import get_redis_pubsub_manager

# Remove in-memory connection storage
# _connections: Dict[str, Dict[str, queue.Queue]] = {}  # DELETE THIS

# Keep local connection mapping: {user_id: queue}
_local_connections: Dict[str, queue.Queue] = {}
_local_connections_lock = Lock()


def add_connection(live_game_id: str, user_id: str) -> tuple[queue.Queue | None, str | None]:
    """Add SSE connection and subscribe to Redis channel."""

    # Check limits (same as before)
    # ... existing limit checks ...

    with _local_connections_lock:
        q = queue.Queue(maxsize=10)
        _local_connections[user_id] = q

    # Subscribe to Redis Pub/Sub for this live game
    redis_manager = get_redis_pubsub_manager()

    def handle_redis_event(event_type: str, data: dict):
        """Forward Redis events to this user's SSE connection."""
        message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        try:
            q.put_nowait(message)
        except queue.Full:
            pass

    redis_manager.subscribe(live_game_id, handle_redis_event)

    return q, None


def remove_connection(live_game_id: str, user_id: str):
    """Remove SSE connection and unsubscribe from Redis."""

    with _local_connections_lock:
        _local_connections.pop(user_id, None)

    # Unsubscribe from Redis (if no more connections for this game)
    # Note: This logic needs refinement for production
    redis_manager = get_redis_pubsub_manager()
    redis_manager.unsubscribe(live_game_id)


def broadcast_event(live_game_id: str, event_type: str, data: dict):
    """
    Broadcast event via Redis Pub/Sub (reaches all instances).
    """
    redis_manager = get_redis_pubsub_manager()
    redis_manager.publish_event(live_game_id, event_type, data)
```

---

### Step 5: Testing

#### 1. Multi-Instance Test (Local)

```bash
# Terminal 1: Start Instance A on port 8000
cd backend
PORT=8000 python src/app.py

# Terminal 2: Start Instance B on port 8001
cd backend
PORT=8001 python src/app.py

# Terminal 3: Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Terminal 4: Test SSE
# Connect to Instance A
curl -N http://localhost:8000/api/live-games/A3B7/stream?token=<jwt>

# Terminal 5: Trigger event on Instance B
curl -X POST http://localhost:8001/api/live-games/A3B7/transactions/buy-in \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"amount": 50}'

# Verify: Terminal 4 should receive transaction_created event ✅
```

#### 2. Load Balancer Test (Production)

```bash
# Deploy multiple instances behind GCP load balancer
gcloud run deploy poker-backend \
  --min-instances=2 \
  --max-instances=10 \
  --region=us-central1

# Monitor Redis Pub/Sub
redis-cli MONITOR
```

---

## Performance Considerations

### Redis Memory Usage

```bash
# Check memory usage
redis-cli INFO memory

# Expected usage for 100 active games with 10 events/sec:
# ~1MB for Pub/Sub channels (negligible)
```

### Connection Pooling

```python
# Use connection pool for better performance
redis_pool = redis.ConnectionPool(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT')),
    password=os.getenv('REDIS_PASSWORD'),
    max_connections=20
)

redis_client = redis.Redis(connection_pool=redis_pool)
```

### Monitoring

```python
# Add metrics
def publish_event(self, live_game_id: str, event_type: str, data: dict):
    start_time = time.time()

    try:
        self.redis_client.publish(channel, message)

        # Log latency
        latency = (time.time() - start_time) * 1000
        logger.info(f"Redis publish latency: {latency:.2f}ms")

    except Exception as e:
        logger.error(f"Redis publish failed: {e}")
```

---

## Rollback Plan

If issues arise, quickly rollback to in-memory storage:

```python
# In src/routes/live_game_sse.py

USE_REDIS = os.getenv('USE_REDIS_PUBSUB', 'false').lower() == 'true'

if USE_REDIS:
    from infrastructure.redis_pubsub import get_redis_pubsub_manager
    # Use Redis implementation
else:
    # Use in-memory implementation (current code)
```

Set `USE_REDIS_PUBSUB=false` to disable Redis immediately.

---

## Cost Estimation

### GCP Memorystore (Basic Tier)

| Instance Size | Memory | Price/Month |
|--------------|---------|------------|
| M1 (Basic)   | 1 GB    | ~$30       |
| M2 (Basic)   | 4 GB    | ~$90       |

### Redis Cloud (Free Tier)

- 30 MB free tier (suitable for testing)
- Paid plans start at $5/month

---

## Security Best Practices

1. **Use SSL/TLS** in production:
   ```python
   redis.Redis(
       ssl=True,
       ssl_cert_reqs='required',
       ssl_ca_certs='/path/to/ca-cert.pem'
   )
   ```

2. **Rotate Redis password** regularly

3. **Restrict network access**:
   - GCP: Use VPC peering
   - AWS: Use Security Groups
   - Azure: Use Virtual Network

4. **Monitor Redis logs** for unauthorized access attempts

---

## Troubleshooting

### Problem: Events not received across instances

**Solution**: Check Redis Pub/Sub channels are active:
```bash
redis-cli
> PUBSUB CHANNELS live_game:*
> PUBSUB NUMSUB live_game:uuid-here
```

### Problem: High latency (>100ms)

**Solution**:
- Move Redis closer to application servers (same region)
- Use connection pooling
- Consider Redis Cluster for horizontal scaling

### Problem: Connection drops

**Solution**:
- Increase `timeout` in Redis connection
- Implement reconnection logic with exponential backoff
- Monitor Redis server health metrics

---

## Next Steps

After successful migration:

1. ✅ Remove in-memory connection code
2. ✅ Update documentation
3. ✅ Add Redis health checks to `/api/health` endpoint
4. ✅ Set up Redis monitoring (Prometheus + Grafana)
5. ✅ Configure Redis persistence (RDB snapshots)
6. ✅ Implement Redis Cluster for high availability

---

## References

- [Redis Pub/Sub Documentation](https://redis.io/docs/manual/pubsub/)
- [redis-py Documentation](https://redis-py.readthedocs.io/)
- [GCP Memorystore](https://cloud.google.com/memorystore)
- [Server-Sent Events Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)
