import redis
import logging

from api.config.config import settings as CONFIG

logger = logging.getLogger(__name__)

REDIS_PUBSUB_URL=CONFIG.REDIS_PUBSUB_URL

def get_redis_client():
    try:
        redis_client = redis.StrictRedis.from_url(REDIS_PUBSUB_URL)
        redis_client.ping()
        logger.info("Connected to Redis successfully")
        return redis_client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None