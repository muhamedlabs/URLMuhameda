import asyncio
import os
import threading
from flask import Flask
from routes.api import api_bp
from routes.views import views_bp
from protocol.url_storage import initialize_system, load_file_to_redis
from BANNED_FILES.config import redis_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=BASE_DIR)

app.register_blueprint(api_bp)
app.register_blueprint(views_bp)

def init_sync():
    """Синхронная инициализация асинхронных компонентов"""
    try:
        # Создаем новый event loop для основного потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Инициализируем Redis
        loop.run_until_complete(redis_manager.init_connection())
        print("[REDIS] Redis is ready")
        
        # Проверяем соединение
        if not hasattr(redis_manager, '_redis') or redis_manager._redis is None:
            raise RuntimeError("Redis connection failed - _redis is None")
        
        # Загружаем данные из файла в Redis
        loop.run_until_complete(load_file_to_redis())
        print("[SYNC] File -> Redis done")
        
        # Запускаем мониторинг в фоновом потоке
        start_background_monitoring()
        
    except Exception as e:
        print(f"Initialization failed: {e}")
        raise
    finally:
        loop.close()

def start_background_monitoring():
    """Запускаем мониторинг в фоновом потоке"""
    def run_monitoring():
        try:
            # Создаем новый event loop для фонового потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Инициализируем систему с мониторингом
            loop.run_until_complete(initialize_system())
            
            # Запускаем бесконечный цикл мониторинга
            loop.run_forever()
        except Exception as e:
            print(f"Background monitoring error: {e}")
    
    # Запускаем мониторинг в отдельном потоке
    monitor_thread = threading.Thread(target=run_monitoring, daemon=True)
    monitor_thread.start()
    print("[MONITOR] Background monitoring started")

def run_flask():
    """Запускаем Flask синхронно"""
    print("[FLASK] Starting Flask server...")
    app.run(host="0.0.0.0", port=5001, debug=True)

if __name__ == "__main__":
    try:
        print("[APP] Starting application...")
        
        # Сначала инициализация Redis и синхронизация файла
        init_sync()
        
        # После этого запускаем Flask
        run_flask()
        
    except Exception as e:
        print(f"Failed to start application: {e}")