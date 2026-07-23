const CACHE_NAME = 'ventebot-dashboard-shell-20260723-mobile-products-v1';
const APP_SHELL = [
    './',
    './index.html',
    './style.css?v=20260720-reseller-telegram-prices',
    './revamp.css?v=20260720-reseller-prices',
    './system.css?v=20260723-pwa-v8',
    './liquid-glass.css?v=20260723-liquid-v1',
    './operations.css?v=20260723-mobile-products-v1',
    './theme-bootstrap.js?v=20260723-liquid-v1',
    './app.js?v=20260723-mobile-products-v1',
    './operations.js?v=20260723-ops-v2',
    './manifest.webmanifest',
    './icons/ventebot-icon-192.png',
    './icons/ventebot-icon-512.png',
    './icons/ventebot-maskable-512.png',
    './icons/ventebot-apple-touch-180.png',
];

const scopeUrl = new URL(self.registration.scope);
const scopePath = scopeUrl.pathname.endsWith('/') ? scopeUrl.pathname : `${scopeUrl.pathname}/`;
const STATIC_ASSET_PATTERN = /\.(?:css|js|png|svg|webmanifest|ico)$/i;

function isDashboardRequest(request, url) {
    if (request.method !== 'GET' || url.origin !== self.location.origin) return false;
    if (request.headers.has('authorization')) return false;
    if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/health')) return false;
    if (!url.pathname.startsWith(scopePath)) return false;
    return request.mode === 'navigate' || STATIC_ASSET_PATTERN.test(url.pathname);
}

function canStore(response) {
    if (!response || !response.ok || response.type !== 'basic') return false;
    const cacheControl = response.headers.get('cache-control') || '';
    return !/(?:no-store|private)/i.test(cacheControl);
}

async function storeResponse(request, response) {
    if (!canStore(response)) return;
    const cache = await caches.open(CACHE_NAME);
    await cache.put(request, response.clone());
}

async function networkFirst(request) {
    try {
        const response = await fetch(request);
        await storeResponse(request, response);
        return response;
    } catch (error) {
        const cached = await caches.match(request);
        if (cached) return cached;
        if (request.mode === 'navigate') {
            const shell = await caches.match('./');
            if (shell) return shell;
        }
        throw error;
    }
}

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL))
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(keys => Promise.all(
                keys
                    .filter(key => key.startsWith('ventebot-dashboard-shell-') && key !== CACHE_NAME)
                    .map(key => caches.delete(key))
            ))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    if (!isDashboardRequest(request, url)) return;
    if (url.pathname.endsWith('/service-worker.js')) return;
    event.respondWith(networkFirst(request));
});
