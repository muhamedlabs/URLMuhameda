import asyncio
import traceback
import threading
from flask import Blueprint, request, jsonify, redirect
from utils.helpers import generate_short_code, is_valid_url
from config.redis_manager import RedisManager
from models.url import Url

api_bp = Blueprint('api', __name__)

# Инициализируем Redis manager
redis_manager = RedisManager()

# Глобальная переменная для отслеживания инициализации Redis
_redis_initialized = False

def run_async_safe(coro):
    """
    Безопасно запускает async корутину в синхронном контексте Flask
    """
    import concurrent.futures
    import threading
    
    def run_in_thread():
        # Создаем новый event loop в отдельном потоке
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    # Всегда запускаем в отдельном потоке для избежания конфликтов
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_thread)
        return future.result()

async def ensure_redis_connection():
    """
    Убеждаемся что Redis подключение инициализировано
    """
    global _redis_initialized
    if not _redis_initialized:
        try:
            print("Initializing Redis connection...")
            await redis_manager.connect()
            _redis_initialized = True
            print("Redis connection established successfully")
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            raise

def safe_redis_operation(operation_func):
    """
    Декоратор для безопасного выполнения Redis операций
    """
    async def wrapper(*args, **kwargs):
        try:
            await ensure_redis_connection()
            return await operation_func(*args, **kwargs)
        except Exception as e:
            print(f"Redis operation failed: {e}")
            return None
    return wrapper

@api_bp.route('/api/shorten', methods=['POST'])
def shorten_url():
    print("=== DEBUG: Route called ===")
    print(f"Method: {request.method}")
    print(f"Content-Type: {request.content_type}")
    print(f"Raw data: {request.get_data()}")
    
    try:
        # Получаем и валидируем данные
        data = request.get_json()
        print(f"Parsed JSON: {data}")
        
        if not data or 'url' not in data:
            print("ERROR: URL is required")
            return jsonify({'error': 'URL is required'}), 400

        original_url = data['url'].strip()
        print(f"Original URL: {original_url}")
        
        if not original_url:
            print("ERROR: URL cannot be empty")
            return jsonify({'error': 'URL cannot be empty'}), 400

        # Добавляем протокол если его нет
        if not original_url.startswith(('http://', 'https://')):
            original_url = 'https://' + original_url
            print(f"URL with protocol: {original_url}")

        # Валидируем URL
        if not is_valid_url(original_url):
            print("ERROR: Invalid URL format")
            return jsonify({'error': 'Invalid URL format'}), 400

        print("Starting Redis operations...")

        # Загружаем все URL из Redis (безопасно)
        try:
            @safe_redis_operation
            async def load_urls():
                return await redis_manager.load_many(Url, "url_storage")
            
            all_urls = run_async_safe(load_urls())
            print(f"Loaded {len(all_urls) if all_urls else 0} URLs from Redis")
            
            # Если Redis вернул None, используем пустой список
            if all_urls is None:
                all_urls = []
                
        except Exception as redis_error:
            print(f"Redis load error: {redis_error}")
            print(traceback.format_exc())
            # Если Redis недоступен, продолжаем без кеша
            all_urls = []

        # Проверяем, есть ли уже эта ссылка
        for record in all_urls:
            if hasattr(record, 'original_url') and record.original_url == original_url:
                print(f"Found existing URL with code: {record.id}")
                return jsonify({
                    'short_code': record.id,
                    'original_url': original_url,
                    'short_url': request.host_url + record.id
                }), 200

        # Генерируем уникальный код
        short_code = generate_short_code()
        existing_codes = [record.id for record in all_urls if hasattr(record, 'id')]
        
        attempts = 0
        while short_code in existing_codes and attempts < 10:
            short_code = generate_short_code()
            attempts += 1
            
        if attempts >= 10:
            print("ERROR: Could not generate unique short code")
            return jsonify({'error': 'Could not generate unique code'}), 500

        print(f"Generated short code: {short_code}")

        # Сохраняем в Redis (безопасно)
        try:
            @safe_redis_operation
            async def save_url():
                url_record = Url(id=short_code, original_url=original_url)
                return await redis_manager.save(url_record, "url_storage")
            
            result = run_async_safe(save_url())
            if result is not None:
                print("Saved to Redis successfully")
            else:
                print("Redis save failed - continuing without cache")
                
        except Exception as redis_error:
            print(f"Redis save error: {redis_error}")
            print(traceback.format_exc())
            # Не возвращаем ошибку - продолжаем работу без Redis
            print("Continuing without Redis cache")

        response_data = {
            'short_code': short_code,
            'original_url': original_url,
            'short_url': request.host_url + short_code
        }
        print(f"Returning response: {response_data}")

        return jsonify(response_data), 201

    except Exception as e:
        print(f"Unexpected error: {e}")
        print("Full traceback:")
        print(traceback.format_exc())
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@api_bp.route('/<string:short_code>')
def redirect_to_url(short_code):
    print(f"=== Redirect request for code: {short_code} ===")
    
    try:
        if len(short_code) != 7:
            print(f"Invalid code length: {len(short_code)}")
            return "Invalid short code format", 404

        # Загружаем URL по коду (безопасно)
        try:
            @safe_redis_operation
            async def load_url():
                return await redis_manager.load(Url, "url_storage", short_code)
            
            url_record = run_async_safe(load_url())
            print(f"Loaded record: {url_record}")
            
        except Exception as redis_error:
            print(f"Redis load error: {redis_error}")
            print(traceback.format_exc())
            return "Short URL not found", 404
        
        if url_record and hasattr(url_record, 'original_url') and url_record.original_url:
            print(f"Redirecting to: {url_record.original_url}")
            return redirect(url_record.original_url, code=302)
            
        print("URL record not found or empty")
        return "Short URL not found", 404

    except Exception as e:
        print(f"Redirect error: {e}")
        print(traceback.format_exc())
        return "Short URL not found", 404


@api_bp.route('/api/stats')
def get_stats():
    print("=== Stats request ===")
    
    try:
        # Загружаем все URL (безопасно)
        try:
            @safe_redis_operation
            async def load_all_urls():
                return await redis_manager.load_many(Url, "url_storage")
            
            all_urls = run_async_safe(load_all_urls())
            print(f"Loaded {len(all_urls) if all_urls else 0} URLs for stats")
            
            # Если Redis вернул None, используем пустой список
            if all_urls is None:
                all_urls = []
                
        except Exception as redis_error:
            print(f"Redis stats error: {redis_error}")
            print(traceback.format_exc())
            return jsonify({'error': 'Failed to load stats'}), 500
        
        stats_data = {
            'total_urls': len(all_urls) if all_urls else 0,
            'urls': []
        }
        
        if all_urls:
            for record in all_urls:
                if hasattr(record, 'id') and hasattr(record, 'original_url'):
                    stats_data['urls'].append({
                        'code': record.id, 
                        'url': record.original_url
                    })
        
        print(f"Returning stats: {stats_data}")
        return jsonify(stats_data)
        
    except Exception as e:
        print(f"Stats error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


# Добавляем healthcheck endpoint для диагностики
@api_bp.route('/api/health')
def health_check():
    """Простая проверка работоспособности сервера"""
    try:
        # Проверяем подключение к Redis
        @safe_redis_operation  
        async def test_redis():
            return await redis_manager.load_many(Url, "url_storage")
        
        test_result = run_async_safe(test_redis())
        
        return jsonify({
            'status': 'healthy',
            'redis_connection': 'ok' if test_result is not None else 'failed',
            'total_urls': len(test_result) if test_result else 0
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'redis_connection': 'failed'
        }), 500