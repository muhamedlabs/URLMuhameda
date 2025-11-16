import os
import json
import threading
import asyncio
from typing import List, Dict, Any
from BANNED_FILES.config import redis_manager, DATA_FILE
from redis_storage.url import Url

lock = threading.Lock()

# Константа для stream key
REDIS_STREAM_KEY = "urls_stream"

# ---------------------------
# GLOBAL STATE MANAGEMENT
# ---------------------------

class AppState:
    _initialized = False
    _monitoring_active = False
    
    @classmethod
    def is_initialized(cls):
        return cls._initialized
    
    @classmethod
    def set_initialized(cls):
        cls._initialized = True
    
    @classmethod
    def is_monitoring_active(cls):
        return cls._monitoring_active
    
    @classmethod
    def set_monitoring_active(cls, active: bool):
        cls._monitoring_active = active

# ---------------------------
# OPTIMIZED FILE MONITORING
# ---------------------------

class OptimizedFileMonitor:
    def __init__(self):
        self._last_modified = 0
        self._file_size = 0
        self._monitoring = False
        
    def get_file_info(self) -> tuple:
        """Получаем базовую информацию о файле (быстрее чем хеш)"""
        if not os.path.exists(DATA_FILE):
            return (0, 0)
        try:
            stat = os.stat(DATA_FILE)
            return (stat.st_mtime, stat.st_size)
        except Exception:
            return (0, 0)
    
    def has_file_changed(self) -> bool:
        """Быстрая проверка изменений файла"""
        current_mtime, current_size = self.get_file_info()
        
        if (self._last_modified != current_mtime or 
            self._file_size != current_size):
            self._last_modified = current_mtime
            self._file_size = current_size
            return True
        return False
    
    async def start_monitoring(self, interval: int = 10):  # Увеличил интервал до 10 сек
        """Запускаем мониторинг с оптимизацией"""
        if self._monitoring:
            return
            
        self._monitoring = True
        AppState.set_monitoring_active(True)
        print("[FILE MONITOR] Started optimized monitoring (10s interval)")
        
        consecutive_errors = 0
        max_errors = 3
        
        while self._monitoring:
            try:
                if self.has_file_changed():
                    print("[FILE MONITOR] File changed detected, syncing to Redis...")
                    await self.sync_file_to_redis()
                    consecutive_errors = 0  # Сброс счетчика ошибок при успехе
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                consecutive_errors += 1
                print(f"[FILE MONITOR ERROR] {e} (error {consecutive_errors}/{max_errors})")
                
                if consecutive_errors >= max_errors:
                    print("[FILE MONITOR] Too many errors, stopping monitoring")
                    self.stop_monitoring()
                    break
                    
                await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """Останавливаем мониторинг"""
        self._monitoring = False
        AppState.set_monitoring_active(False)
        print("[FILE MONITOR] Stopped monitoring")

    async def sync_file_to_redis(self):
        """Оптимизированная синхронизация файла в Redis"""
        try:
            file_urls = load_file()
            if not file_urls:
                return
                
            redis_urls = await load_all()
            
            # Быстрое сравнение по количеству
            if len(file_urls) != len(redis_urls):
                print(f"[SYNC] Different count: file={len(file_urls)}, redis={len(redis_urls)}")
                await save_many(file_urls)
                return
            
            # Детальное сравнение только если количество совпадает
            file_dict = {url.id: url for url in file_urls}
            redis_dict = {url.id: url for url in redis_urls}
            
            changes_found = False
            
            # Проверяем только изменения
            for url_id in file_dict:
                if url_id not in redis_dict:
                    changes_found = True
                    break
                if (file_dict[url_id].original_url != redis_dict[url_id].original_url or 
                    file_dict[url_id].short_id != redis_dict[url_id].short_id):
                    changes_found = True
                    break
            
            if changes_found:
                print("[SYNC] Changes detected, updating Redis")
                await save_many(file_urls)
            else:
                print("[SYNC] No changes detected")
                
        except Exception as e:
            print(f"[SYNC ERROR] Failed to sync file to Redis: {e}")

# Создаем оптимизированный монитор
file_monitor = OptimizedFileMonitor()

# ---------------------------
# LAZY REDIS MONITORING
# ---------------------------

class LazyRedisMonitor:
    def __init__(self):
        self._monitoring = False
        self._last_url_count = 0
        
    async def start_monitoring(self, interval: int = 15):  # Увеличил интервал до 15 сек
        """Ленивый мониторинг Redis - только при изменениях"""
        if self._monitoring:
            return
            
        self._monitoring = True
        print("[REDIS MONITOR] Started lazy monitoring (15s interval)")
        
        while self._monitoring:
            try:
                current_count = await get_url_count()
                
                # Синхронизируем только если количество изменилось
                if current_count != self._last_url_count:
                    print(f"[REDIS MONITOR] Count changed: {self._last_url_count} -> {current_count}")
                    await self.sync_redis_to_file()
                    self._last_url_count = current_count
                # Или если мониторинг файла не активен (на случай если файл изменился вне системы)
                elif not AppState.is_monitoring_active():
                    await self.sync_redis_to_file()
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                print(f"[REDIS MONITOR ERROR] {e}")
                await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """Останавливаем мониторинг"""
        self._monitoring = False
        print("[REDIS MONITOR] Stopped monitoring")
    
    async def sync_redis_to_file(self):
        """Синхронизируем Redis в файл только при необходимости"""
        try:
            redis_urls = await load_all()
            save_file(redis_urls)
            print(f"[REDIS SYNC] Synced {len(redis_urls)} URLs to file")
        except Exception as e:
            print(f"[REDIS SYNC ERROR] {e}")

# Создаем ленивый монитор Redis
redis_monitor = LazyRedisMonitor()

# ---------------------------
# FILE OPERATIONS (без изменений)
# ---------------------------

def load_file() -> List[Url]:
    """Загрузка URL из файла"""
    if not os.path.exists(DATA_FILE):
        return []
    with lock:
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                urls = []
                for item in data:
                    url = Url(
                        id=item["id"],
                        original_url=item["original_url"],
                        short_id=item.get("short_id", f"https://url.muhamedlabs.pro/{item['id']}")
                    )
                    urls.append(url)
                return urls
        except Exception as e:
            print("[FILE LOAD ERROR]", e)
            return []

def save_file(urls: List[Url]):
    """Сохраняем URL в файл"""
    with lock:
        try:
            # Обновляем метки монитора чтобы избежать цикла
            file_monitor._last_modified, file_monitor._file_size = file_monitor.get_file_info()
            
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                data_to_save = []
                for url in urls:
                    data_to_save.append({
                        "id": url.id,
                        "original_url": url.original_url,
                        "short_id": url.short_id
                    })
                
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            
            print(f"[FILE] Saved {len(urls)} URLs to file")
        except Exception as e:
            print("[FILE SAVE ERROR]", e)

# ---------------------------
# REDIS OPERATIONS
# ---------------------------

async def initialize_system():
    """Инициализация системы"""
    try:
        await redis_manager.init_connection()
        print("[REDIS] Redis is ready")
        
        urls = load_file()
        if urls:
            await save_many(urls)
        print(f"[SYNC] Loaded {len(urls)} URLs from file into Redis.")
        
        AppState.set_initialized()
        print("[SYSTEM] System initialized and ready")
        return True
        
    except Exception as e:
        print(f"[SYSTEM INIT ERROR] {e}")
        return False

async def load_file_to_redis():
    """Для обратной совместимости"""
    return await initialize_system()

# Остальные функции без изменений...
async def save(url: Url) -> bool:
    try:
        result = await redis_manager.save(url)
        print(f"[REDIS] Saved URL: {url.id}")
        return result
    except Exception as e:
        print(f"[REDIS SAVE ERROR] {e}")
        return False

async def save_many(urls: List[Url], keys: List[str] = None) -> bool:
    try:
        if keys is None:
            keys = [u.id for u in urls]
        result = await redis_manager.save_many(urls, keys)
        print(f"[REDIS] Saved {len(urls)} URLs")
        return result
    except Exception as e:
        print(f"[REDIS SAVE_MANY ERROR] {e}")
        return False

async def load(key: str) -> Url:
    try:
        return await redis_manager.load(key, Url)
    except Exception as e:
        print(f"[REDIS LOAD ERROR] {e}")
        return None

async def load_all() -> List[Url]:
    try:
        return await redis_manager.load_stream(REDIS_STREAM_KEY, Url)
    except Exception as e:
        print(f"[REDIS LOAD_STREAM ERROR] {e}")
        return []

async def get_url_count() -> int:
    urls = await load_all()
    return len(urls)

# ... остальные функции

def create_url(short_id: str, original_url: str) -> Url:
    full_short_url = f"https://url.muhamedlabs.pro/{short_id}"
    return Url(id=short_id, original_url=original_url, short_id=full_short_url)

async def get_original_url(short_id: str) -> str:
    try:
        url = await load(short_id)
        return url.original_url if url else None
    except Exception as e:
        print(f"[REDIRECT ERROR] {e}")
        return None

# ---------------------------
# FLASK COMPATIBLE INITIALIZATION
# ---------------------------

def init_sync():
    """Синхронная инициализация для Flask"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        success = loop.run_until_complete(initialize_system())
        
        # Запускаем мониторинг в фоне только если нужно
        if success:
            import threading
            
            def start_monitoring_async():
                monitoring_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(monitoring_loop)
                monitoring_loop.run_until_complete(file_monitor.start_monitoring())
                monitoring_loop.run_until_complete(redis_monitor.start_monitoring())
            
            monitor_thread = threading.Thread(target=start_monitoring_async, daemon=True)
            monitor_thread.start()
            print("[MONITOR] Background monitoring started")
        
        loop.close()
        return success
        
    except Exception as e:
        print(f"[INIT SYNC ERROR] {e}")
        return False