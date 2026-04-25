from redis import Redis

try:
    from .config import settings
except ImportError:
    from config import settings

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
