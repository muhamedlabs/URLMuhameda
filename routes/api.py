import os
import json
import threading
from flask import Blueprint, request, jsonify, redirect
from utils.helpers import generate_short_code, is_valid_url
from BANNED_FILES.config import RedisManager, DATA_FILE
from redis_storage.url import Url  

api_bp = Blueprint('api', __name__)

# ---------------------------
# FILE STORAGE
# ---------------------------

lock = threading.Lock()  # Для потокобезопасного доступа

def load_all_urls():
    """Загрузка всех URL из файла"""
    if not os.path.exists(DATA_FILE):
        return []
    with lock:
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Url(**item) for item in data]
        except Exception as e:
            print(f"Error loading data file: {e}")
            return []

def save_all_urls(urls):
    """Сохраняем все URL в файл"""
    with lock:
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump([{'id': u.id, 'original_url': u.original_url} for u in urls],
                          f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving data file: {e}")

def save_url(record):
    """Добавляем новый URL и сохраняем"""
    urls = load_all_urls()
    urls.append(record)
    save_all_urls(urls)

def find_by_code(code):
    """Поиск URL по короткому коду"""
    urls = load_all_urls()
    for url in urls:
        if url.id == code:
            return url
    return None

def find_by_original(original_url):
    """Поиск URL по оригинальному адресу"""
    urls = load_all_urls()
    for url in urls:
        if url.original_url == original_url:
            return url
    return None

# ---------------------------
# ROUTES
# ---------------------------

@api_bp.route('/api/shorten', methods=['POST'])
def shorten_url():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400

        original_url = data['url'].strip()
        if not original_url:
            return jsonify({'error': 'URL cannot be empty'}), 400

        if not original_url.startswith(('http://', 'https://')):
            original_url = 'https://' + original_url

        if not is_valid_url(original_url):
            return jsonify({'error': 'Invalid URL format'}), 400

        existing = find_by_original(original_url)
        if existing:
            return jsonify({
                'short_code': existing.id,
                'original_url': existing.original_url,
                'short_url': request.host_url + existing.id
            }), 200

        # Генерация уникального кода
        urls = load_all_urls()
        short_code = generate_short_code()
        existing_codes = [url.id for url in urls]
        attempts = 0
        while short_code in existing_codes and attempts < 10:
            short_code = generate_short_code()
            attempts += 1
        if attempts >= 10:
            return jsonify({'error': 'Could not generate unique code'}), 500

        new_url = Url(id=short_code, original_url=original_url)
        save_url(new_url)

        return jsonify({
            'short_code': short_code,
            'original_url': original_url,
            'short_url': request.host_url + short_code
        }), 201

    except Exception as e:
        print("Error in /shorten:", e)
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/<string:short_code>')
def redirect_to_url(short_code):
    try:
        if len(short_code) != 7:
            return "Invalid short code", 404

        record = find_by_code(short_code)
        if record:
            return redirect(record.original_url, code=302)
        return "Short URL not found", 404
    except Exception as e:
        print("Redirect error:", e)
        return "Short URL not found", 404

@api_bp.route('/api/stats')
def get_stats():
    try:
        urls = load_all_urls()
        return jsonify({
            'total_urls': len(urls),
            'urls': [
                {
                    'short_code': u.id,
                    'original_url': u.original_url,
                    'short_url': request.host_url + u.id
                } for u in urls
            ]
        })
    except Exception as e:
        print("Stats error:", e)
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/api/health')
def health():
    try:
        urls = load_all_urls()
        return jsonify({
            'status': 'healthy',
            'storage': 'file',
            'total_urls': len(urls)
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'storage': 'file',
            'error': str(e)
        }), 500
