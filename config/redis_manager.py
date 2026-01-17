import os
import asyncio
from dotenv import load_dotenv
from ashredis import RedisParams, RedisManager as BaseRedisManager

load_dotenv()

REDIS_PARAMS = RedisParams(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT")),
    password=os.environ.get("REDIS_PASSWORD") or None,
    db=int(os.environ.get("NUMBER_BD"))
)


class RedisManager(BaseRedisManager):
    def __init__(self):
        super().__init__(redis_params=REDIS_PARAMS)
        self._connected = False

    async def init_connection(self):
        if not self._connected:
            print(f"Connecting to Redis: {REDIS_PARAMS.host}:{REDIS_PARAMS.port}")
            await self.connect()   # <<< ВАЖНО!
            self._connected = True
            print("Redis connected successfully")


# Глобальный инстанс RedisManager
redis_manager = RedisManager()

# helper для синхронного вызова в Flask
def init_redis_sync():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(redis_manager.init_connection())
    loop.close()
