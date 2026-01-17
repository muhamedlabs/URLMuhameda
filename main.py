import asyncio
import os
import threading
from flask import Flask, send_from_directory
from routes.api import api_bp
from routes.views import views_bp
from protocol.url_storage import initialize_system, load_file_to_redis
from BANNED_FILES.config import redis_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=BASE_DIR, static_folder=BASE_DIR)

app.register_blueprint(api_bp)
app.register_blueprint(views_bp)


@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "home.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(BASE_DIR, filename)


async def periodic_sync():
    """Каждые 30 минут загружает данные из файла в Redis"""
    while True:
        try:
            print("[SYNC] Scheduled file -> Redis started")
            await load_file_to_redis()
            print("[SYNC] Scheduled file -> Redis completed")
        except Exception as e:
            print(f"[SYNC-ERROR] {e}")

        await asyncio.sleep(1800)  # 30 минут


def init_sync():
    """Синхронная инициализация асинхронных компонентов"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(redis_manager.init_connection())
        print("[REDIS] Redis is ready")

        if not hasattr(redis_manager, "_redis") or redis_manager._redis is None:
            raise RuntimeError("Redis connection failed - _redis is None")

        loop.run_until_complete(load_file_to_redis())
        print("[SYNC] File -> Redis done")

        start_background_monitoring()

    except Exception as e:
        print(f"Initialization failed: {e}")
        raise
    finally:
        loop.close()

def start_background_monitoring():
    """Запускаем мониторинг и периодическую синхронизацию в фоновом потоке"""

    def run_monitoring():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop.run_until_complete(initialize_system())

            loop.create_task(periodic_sync())
            print("[SYNC] Periodic file sync every 30 minutes started")

            loop.run_forever()

        except Exception as e:
            print(f"Background monitoring error: {e}")

    threading.Thread(target=run_monitoring, daemon=True).start()
    print("[MONITOR] Background monitoring started")


def run_flask():
    print("[FLASK] Starting Flask server on port 5001")
    app.run(host="0.0.0.0", port=5001, debug=True)


if __name__ == "__main__":
    print("[APP] Starting application...")

    init_sync()
    run_flask()
