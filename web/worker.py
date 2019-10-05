#!/usr/bin/env python
import sys, redis, logging
from rq import Connection, Worker
from web import worker_settings as conf

# Preload libraries
from web.api import ascii_grid

logger = logging.getLogger(__name__)

# Provide queue names to listen to as arguments to this script,
# similar to rq worker
r = redis.Redis(host=conf.REDIS_HOST, port=conf.REDIS_PORT, db=conf.REDIS_DB, password=conf.REDIS_PASSWORD)
with Connection(r):
    qs = sys.argv[1:] or ['default']
    logger.info("Starting worker...")

    w = Worker(qs)
    w.work()
