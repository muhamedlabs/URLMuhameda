document.addEventListener('DOMContentLoaded', initializeApp);

function initializeApp() {
    setupEventListeners();
}

function setupEventListeners() {
    const urlForm = document.getElementById('urlForm');
    if (urlForm) urlForm.addEventListener('submit', handleFormSubmit);

    const navLinks = document.querySelectorAll('.nav-links a');
    navLinks.forEach(link => link.addEventListener('click', e => e.preventDefault()));

    const copyBtn = document.querySelector('.copy-btn');
    if (copyBtn) copyBtn.addEventListener('click', copyToClipboard);
}

async function handleFormSubmit(e) {
    e.preventDefault();
    const urlInput = document.getElementById('url');
    const url = urlInput?.value.trim();
    const elements = getFormElements();

    if (!url) return showError('Пожалуйста, введите URL');
    if (!isValidUrl(url)) return showError('Пожалуйста, введите корректный URL');

    showLoading(elements);

    try {
        const data = await shortenUrl(url);
        handleSuccessResponse(data, elements);
    } catch (err) {
        handleErrorResponse(err, elements);
    } finally {
        hideLoading(elements);
    }
}

function getFormElements() {
    return {
        loading: document.getElementById('loading'),
        result: document.getElementById('result'),
        error: document.getElementById('error'),
        submitBtn: document.getElementById('submitBtn'),
        urlCard: document.querySelector('.url-card')
    };
}

function isValidUrl(string) {
    try {
        new URL(string.startsWith('http') ? string : `https://${string}`);
        return true;
    } catch (_) {
        const urlPattern = /^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(\/.*)?$/;
        return urlPattern.test(string);
    }
}

function showLoading(elements) {
    toggleElement(elements.result, false);
    toggleElement(elements.error, false);
    toggleElement(elements.loading, true);
    elements.submitBtn.disabled = true;
    elements.submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Обработка...';
}

function hideLoading(elements) {
    toggleElement(elements.loading, false);
    elements.submitBtn.disabled = false;
    elements.submitBtn.innerHTML = '<i class="fas fa-magic"></i> Сократить';
}

function getApiBaseUrl() {
    return window.location.origin;
}

async function shortenUrl(url) {
    const apiUrl = `${getApiBaseUrl()}/api/shorten`;
    const payload = { url };

    try {
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const text = await response.text();
        if (!response.ok) {
            try {
                const json = JSON.parse(text);
                throw new Error(json.error || `Ошибка сервера ${response.status}`);
            } catch {
                throw new Error(response.status === 500
                    ? 'Ошибка на сервере (500). Проверьте логи сервера'
                    : `HTTP ${response.status}`);
            }
        }

        try {
            return JSON.parse(text);
        } catch {
            throw new Error('Некорректный формат ответа сервера');
        }
    } catch (err) {
        throw new Error(err.message || 'Ошибка соединения с сервером');
    }
}

function handleSuccessResponse(data, elements) {
    const originalUrlElement = document.getElementById('originalUrl');
    const shortUrlElement = document.getElementById('shortUrl');
    if (originalUrlElement && shortUrlElement) {
        originalUrlElement.textContent = data.original_url;
        shortUrlElement.textContent = data.short_url;
        shortUrlElement.href = data.short_url;
    }
    toggleElement(elements.result, true);
    document.getElementById('url').value = '';
    elements.result.scrollIntoView({ behavior: 'smooth' });
}

function handleErrorResponse(err, elements) {
    console.error(err);
    showError(err.message || 'Произошла ошибка сервера', elements);
}

function showError(message) {
    const errorElement = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');
    if (!errorElement || !errorMessage) return alert(message);
    errorMessage.textContent = message;
    toggleElement(errorElement, true);
    errorElement.scrollIntoView({ behavior: 'smooth' });
    setTimeout(() => toggleElement(errorElement, false), 8000);
}

async function copyToClipboard() {
    const shortUrl = document.getElementById('shortUrl')?.textContent;
    const copyBtn = document.querySelector('.copy-btn');
    if (!shortUrl) return showError('Нет ссылки для копирования');

    try {
        await navigator.clipboard.writeText(shortUrl);
        showCopySuccess(copyBtn);
    } catch {
        fallbackCopyTextToClipboard(shortUrl, copyBtn);
    }
}

function showCopySuccess(copyBtn) {
    if (!copyBtn) return;
    const original = copyBtn.innerHTML;
    copyBtn.innerHTML = '<i class="fas fa-check"></i> Скопировано!';
    copyBtn.classList.add('success');
    setTimeout(() => {
        copyBtn.innerHTML = original;
        copyBtn.classList.remove('success');
    }, 2000);
}

function fallbackCopyTextToClipboard(text, copyBtn) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    try { document.execCommand('copy'); showCopySuccess(copyBtn); }
    catch { showError('Копирование не поддерживается браузером'); }
    document.body.removeChild(textarea);
}

function toggleElement(element, show) {
    if (element) element.style.display = show ? 'block' : 'none';
}

window.addEventListener('error', e => console.error('Global error:', e.error));
window.addEventListener('unhandledrejection', e => {
    console.error('Unhandled promise rejection:', e.reason);
    e.preventDefault();
    showError('Произошла неожиданная ошибка. Попробуйте обновить страницу.');
});
