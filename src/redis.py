# The Redis core setup

from os import getenv
from dotenv import load_dotenv
from redis.asyncio import Redis

load_dotenv()
redis_host = getenv("REDIS_HOST")
redis_port = getenv("REDIS_PORT")

redis = Redis(
    host=redis_host,
    port=int(redis_port),
    decode_responses=True,

)