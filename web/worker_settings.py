import os

# REDIS_URL = 'redis://localhost:6379/1'
# You can also specify the Redis DB to use
REDIS_HOST = 'adapter-redis-master.default.svc.cluster.local'
REDIS_PORT = 6379
REDIS_DB = 3
REDIS_PASSWORD = 'wdias123'
OPTIMIZE_STORAGE: bool = os.getenv('OPTIMIZE_STORAGE', '1') == '1'

# Queues to listen on
QUEUES = [os.getenv('HOSTNAME', 'default')]
