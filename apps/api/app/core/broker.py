import dramatiq
from dramatiq.brokers.redis import RedisBroker
from app.core.config import settings
import structlog

logger = structlog.get_logger()

def get_broker() -> RedisBroker:
    broker = RedisBroker(url=settings.redis_url)
    dramatiq.set_broker(broker)
    return broker

broker = get_broker()
