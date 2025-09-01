// URL Shortener JavaScript
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    setupEventListeners();
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    const urlForm = document.getElementById('urlForm');
    if (urlForm) {
        urlForm.addEventListener('submit', handleFormSubmit);
    }

    // Navigation links smooth scroll
    const navLinks = document.querySelectorAll('.nav-links a');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            // Add your navigation logic here
        });
    });

    // Copy button
    const copyBtn = document.querySelector('.copy-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', copyToClipboard);
    }
}

/**
 * Handle form submission
 */
async function handleFormSubmit(e) {
    e.preventDefault();
    
    const url = document.getElementById('url').value.trim();
    const elements = getFormElements();
    
    if (!url) {
        showError('Пожалуйста, введите URL');
        return;
    }

    if (!isValidUrl(url)) {
        showError('Пожалуйста, введите корректный URL');
        return;
    }

    showLoading(elements);
    
    try {
        const response = await shortenUrl(url);
        handleSuccessResponse(response, elements);
    } catch (error) {
        handleErrorResponse(error, elements);
    } finally {
        hideLoading(elements);
    }
}

/**
 * Get form elements
 */
function getFormElements() {
    return {
        loading: document.getElementById('loading'),
        result: document.getElementById('result'),
        error: document.getElementById('error'),
        submitBtn: document.getElementById('submitBtn'),
        urlCard: document.querySelector('.url-card')
    };
}

/**
 * Validate URL
 */
function isValidUrl(string) {
    try {
        const url = new URL(string.startsWith('http') ? string : `https://${string}`);
        return true;
    } catch (_) {
        // Дополнительная проверка для URL без протокола
        const urlPattern = /^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(\/.*)?$/;
        return urlPattern.test(string);
    }
}

/**
 * Show loading state
 */
function showLoading(elements) {
    elements.result.style.display = 'none';
    elements.error.style.display = 'none';
    elements.loading.style.display = 'block';
    elements.submitBtn.disabled = true;
    elements.submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Обработка...';
}

/**
 * Hide loading state
 */
function hideLoading(elements) {
    elements.loading.style.display = 'none';
    elements.submitBtn.disabled = false;
    elements.submitBtn.innerHTML = '<i class="fas fa-magic"></i> Сократить';
}

/**
 * Get API base URL
 */
function getApiBaseUrl() {
    // Try to determine the correct API URL
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return window.location.origin; // Use current origin for localhost
    }
    
    // For production or specific server configurations
    // You can hardcode your server URL here if needed
    // return 'http://192.168.0.101:5001';
    
    return window.location.origin; // Use current origin by default
}

/**
 * API call to shorten URL
 */
async function shortenUrl(url) {
    const apiUrl = `${getApiBaseUrl()}/api/shorten`;
    
    try {
        console.log('Sending request to:', apiUrl);
        console.log('Request payload:', { url });
        
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });

        console.log('Response status:', response.status);
        console.log('Response headers:', Object.fromEntries([...response.headers.entries()]));

        // Сначала получаем текст ответа
        const responseText = await response.text();
        console.log('Raw response:', responseText);

        // Проверяем статус ответа
        if (!response.ok) {
            // Пытаемся парсить как JSON для получения детальной ошибки
            try {
                const errorData = JSON.parse(responseText);
                throw new Error(errorData.error || errorData.message || `Ошибка сервера: ${response.status}`);
            } catch (parseError) {
                // Если не JSON, показываем детальную ошибку
                if (response.status === 500) {
                    console.error('Server 500 Error Details:', {
                        status: response.status,
                        statusText: response.statusText,
                        headers: Object.fromEntries([...response.headers.entries()]),
                        body: responseText
                    });
                    throw new Error('Ошибка на сервере (500). Проверьте серверные логи:\n' + 
                                  'python app.py или pm2 logs или docker logs');
                } else if (response.status === 404) {
                    throw new Error('API endpoint не найден (404). Убедитесь что route /api/shorten существует.');
                } else if (response.status === 405) {
                    throw new Error('Метод не разрешен (405). Убедитесь что endpoint принимает POST запросы.');
                } else {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
            }
        }

        // Проверяем, что ответ в формате JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            console.error('Unexpected content type:', contentType);
            console.error('Response body:', responseText);
            throw new Error('Сервер вернул неожиданный формат ответа. Ожидался JSON.');
        }

        // Парсим JSON
        let data;
        try {
            data = JSON.parse(responseText);
        } catch (parseError) {
            console.error('JSON parse error:', parseError);
            console.error('Response text:', responseText);
            throw new Error('Ошибка парсинга ответа сервера');
        }

        console.log('Parsed response data:', data);

        // Проверяем, что в ответе есть нужные поля
        if (!data.short_url) {
            throw new Error('Некорректный ответ сервера: отсутствует short_url');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        
        // Улучшенная обработка ошибок
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            throw new Error('Ошибка соединения с сервером. Проверьте подключение к интернету.');
        } else if (error.name === 'AbortError') {
            throw new Error('Запрос был отменен. Попробуйте еще раз.');
        } else {
            throw error; // Передаем оригинальную ошибку
        }
    }
}

/**
 * Handle successful response
 */
function handleSuccessResponse(data, elements) {
    const originalUrlElement = document.getElementById('originalUrl');
    const shortUrlElement = document.getElementById('shortUrl');
    
    if (originalUrlElement && shortUrlElement) {
        originalUrlElement.textContent = data.original_url;
        shortUrlElement.textContent = data.short_url;
        shortUrlElement.href = data.short_url;
    }
    
    elements.result.style.display = 'block';

    // Clear form
    const urlInput = document.getElementById('url');
    if (urlInput) {
        urlInput.value = '';
    }
    
    // Scroll to result
    elements.result.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Handle error response
 */
function handleErrorResponse(error, elements) {
    console.error('Error:', error);
    showError(error.message || 'Ошибка соединения с сервером. Попробуйте позже.');
}

/**
 * Show error message
 */
function showError(message) {
    const errorElement = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');
    
    if (!errorElement || !errorMessage) {
        console.error('Error elements not found in DOM');
        alert(message); // Fallback
        return;
    }
    
    errorMessage.textContent = message;
    errorElement.style.display = 'block';
    
    // Auto hide after 8 seconds (увеличил время)
    setTimeout(() => {
        errorElement.style.display = 'none';
    }, 8000);
    
    // Scroll to error
    errorElement.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Copy to clipboard functionality
 */
async function copyToClipboard() {
    const shortUrlElement = document.getElementById('shortUrl');
    const copyBtn = document.querySelector('.copy-btn');
    
    if (!shortUrlElement || !shortUrlElement.textContent) {
        showError('Нет ссылки для копирования');
        return;
    }
    
    const shortUrl = shortUrlElement.textContent;
    
    try {
        await navigator.clipboard.writeText(shortUrl);
        showCopySuccess(copyBtn);
    } catch (err) {
        console.error('Copy failed:', err);
        fallbackCopyTextToClipboard(shortUrl, copyBtn);
    }
}

/**
 * Show copy success feedback
 */
function showCopySuccess(copyBtn) {
    if (!copyBtn) return;
    
    const originalContent = copyBtn.innerHTML;
    
    copyBtn.innerHTML = '<i class="fas fa-check"></i> Скопировано!';
    copyBtn.classList.add('success');
    
    setTimeout(() => {
        copyBtn.innerHTML = originalContent;
        copyBtn.classList.remove('success');
    }, 2000);
}

/**
 * Fallback copy method for older browsers
 */
function fallbackCopyTextToClipboard(text, copyBtn) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.top = '0';
    textArea.style.left = '0';
    textArea.style.opacity = '0';
    textArea.style.pointerEvents = 'none';
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showCopySuccess(copyBtn);
        } else {
            showError('Не удалось скопировать ссылку');
        }
    } catch (err) {
        console.error('Fallback copy failed:', err);
        showError('Копирование не поддерживается вашим браузером');
    } finally {
        document.body.removeChild(textArea);
    }
}

/**
 * Utility function to show/hide elements
 */
function toggleElement(element, show) {
    if (element) {
        element.style.display = show ? 'block' : 'none';
    }
}

// Enhanced error handling
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    console.error('Error details:', {
        message: e.message,
        filename: e.filename,
        lineno: e.lineno,
        colno: e.colno
    });
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    console.error('Promise:', e.promise);
    
    // Prevent the default behavior (logging to console)
    e.preventDefault();
    
    // Show user-friendly error
    showError('Произошла неожиданная ошибка. Попробуйте обновить страницу.');
});