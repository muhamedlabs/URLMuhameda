// -----------------------------------------------
//  Загрузка страницы
// -----------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    initLoadingScreen();
    initializeApp();
});

// Анимация загрузочного экрана
function initLoadingScreen() {
    const loadingScreen = document.getElementById('loading-screen');
    const progressBar = document.querySelector('.loading-progress-bar');

    if (!loadingScreen) return;

    setTimeout(() => {
        loadingScreen.classList.add('fade-out');
        setTimeout(() => loadingScreen.remove(), 800);
    }, 2500);
}

// -----------------------------------------------
//  Инициализация приложения
// -----------------------------------------------
function initializeApp() {
    setupEventListeners();
}

function setupEventListeners() {
    const urlForm = document.getElementById('urlForm');
    const navLinks = document.querySelectorAll('.nav-links a');
    const copyBtn = document.querySelector('.copy-btn');

    if (urlForm) urlForm.addEventListener('submit', handleFormSubmit);

    navLinks.forEach(link =>
        link.addEventListener('click', e => e.preventDefault())
    );

    if (copyBtn) copyBtn.addEventListener('click', copyToClipboard);
}

// -----------------------------------------------
//  Отправка формы
// -----------------------------------------------
async function handleFormSubmit(e) {
    e.preventDefault();

    const urlInput = document.getElementById('url');
    const url = urlInput?.value.trim();
    const ui = getUI();

    if (!url) return showError('Пожалуйста, введите URL');
    if (!isValidUrl(url)) return showError('Пожалуйста, введите корректный URL');

    showLoading(ui);

    try {
        const data = await shortenUrl(url);
        handleSuccessResponse(data, ui);
    } catch (err) {
        handleErrorResponse(err, ui);
    } finally {
        hideLoading(ui);
    }
}

function getUI() {
    return {
        loading: document.getElementById('loading'),
        result: document.getElementById('result'),
        error: document.getElementById('error'),
        submitBtn: document.getElementById('submitBtn')
    };
}

// -----------------------------------------------
//  Проверка URL
// -----------------------------------------------
function isValidUrl(str) {
    try {
        new URL(str.startsWith('http') ? str : `https://${str}`);
        return true;
    } catch {
        const pattern =
            /^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(\/.*)?$/;
        return pattern.test(str);
    }
}

// -----------------------------------------------
//  UI: загрузка
// -----------------------------------------------
function showLoading(ui) {
    toggle(ui.result, false);
    toggle(ui.error, false);
    toggle(ui.loading, true);

    ui.submitBtn.disabled = true;
    ui.submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Обработка...';
}

function hideLoading(ui) {
    toggle(ui.loading, false);
    ui.submitBtn.disabled = false;
    ui.submitBtn.innerHTML = '<i class="fas fa-magic"></i> Сократить';
}

function toggle(el, show) {
    if (el) el.style.display = show ? 'block' : 'none';
}

// -----------------------------------------------
//  API: сокращение ссылки
// -----------------------------------------------
async function shortenUrl(url) {
    const apiUrl = `${location.origin}/api/shorten`;

    const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });

    const text = await response.text();

    if (!response.ok) {
        try {
            const json = JSON.parse(text);
            throw new Error(json.error || `Ошибка ${response.status}`);
        } catch {
            throw new Error(
                response.status === 500
                    ? 'Ошибка сервера (500). Проверьте логи'
                    : `HTTP ${response.status}`
            );
        }
    }

    try {
        return JSON.parse(text);
    } catch {
        throw new Error('Некорректный ответ сервера');
    }
}

// -----------------------------------------------
//  Успешный ответ
// -----------------------------------------------
function handleSuccessResponse(data, ui) {
    const originalUrl = document.getElementById('originalUrl');
    const shortUrl = document.getElementById('shortUrl');

    if (originalUrl && shortUrl) {
        const trimmed =
            data.original_url.length > 35
                ? data.original_url.slice(0, 35) + '...'
                : data.original_url;

        originalUrl.textContent = trimmed;
        originalUrl.title = data.original_url;
        originalUrl.href = data.original_url;

        shortUrl.textContent = data.short_url;
        shortUrl.href = data.short_url;
    }

    toggle(ui.result, true);
    document.getElementById('url').value = '';
    ui.result.scrollIntoView({ behavior: 'smooth' });
}

// -----------------------------------------------
//  Ошибки
// -----------------------------------------------
function handleErrorResponse(err, ui) {
    console.error(err);
    showError(err.message);
}

function showError(msg) {
    const block = document.getElementById('error');
    const msgEl = document.getElementById('errorMessage');

    if (!block || !msgEl) return alert(msg);

    msgEl.textContent = msg;
    toggle(block, true);

    setTimeout(() => toggle(block, false), 8000);
}

// -----------------------------------------------
//  Копирование ссылки
// -----------------------------------------------
async function copyToClipboard() {
    const shortUrl = document.getElementById('shortUrl')?.textContent;
    const btn = document.querySelector('.copy-btn');

    if (!shortUrl) return showError('Нет ссылки для копирования');

    try {
        await navigator.clipboard.writeText(shortUrl);
        showCopySuccess(btn);
    } catch {
        fallbackCopy(shortUrl, btn);
    }
}

function showCopySuccess(btn) {
    if (!btn) return;

    const original = btn.innerHTML;

    btn.innerHTML = '<i class="fas fa-check"></i> Скопировано!';
    btn.classList.add('success');
    btn.disabled = true;

    setTimeout(() => {
        btn.innerHTML = original;
        btn.classList.remove('success');
        btn.disabled = false;
    }, 5000);
}

function fallbackCopy(text, btn) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';

    document.body.appendChild(textarea);
    textarea.select();

    try {
        document.execCommand('copy');
        showCopySuccess(btn);
    } catch {
        showError('Копирование не поддерживается');
    }

    textarea.remove();
}

// -----------------------------------------------
//  Глобальные ошибки
// -----------------------------------------------
window.addEventListener('error', e => console.error('Global error:', e.error));

window.addEventListener('unhandledrejection', e => {
    console.error('Promise rejection:', e.reason);
    e.preventDefault();
    showError('Неожиданная ошибка. Обновите страницу.');
});
