# The Redis core setup

from os import getenv
from dotenv import load_dotenv
from redis.asyncio import Redis

load_dotenv()

# Parse REDIS_URL or use individual host/port
REDIS_URL = getenv("REDIS_URL")

if REDIS_URL:
    # Docker setup - use REDIS_URL
    redis = Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        encoding="utf-8"
    )
else:
    # Local development - use host/port
    redis_host = getenv("REDIS_HOST", "localhost")
    redis_port = getenv("REDIS_PORT", "6379")
    redis = Redis(
        host=redis_host,
        port=int(redis_port),
        decode_responses=True,
        encoding="utf-8"
    )

# Create a second connection for pub/sub (doesn't use decode_responses)
pubsub_redis = Redis.from_url(
    REDIS_URL if REDIS_URL else f"redis://{getenv('REDIS_HOST', 'localhost')}:{getenv('REDIS_PORT', '6379')}",
    decode_responses=True,
    encoding="utf-8"
)