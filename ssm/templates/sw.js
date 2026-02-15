{% load static %}
const CACHE_NAME = 'au-it-dept-v1';
const DYNAMIC_CACHE = 'au-it-dept-dynamic-v1';
const ASSETS_TO_CACHE = [
    "{% static 'imgs/annamalai.png' %}",
    "{% static 'css/student_style.css' %}",
    "/offline/"
];

// Install event: Cache core assets
self.addEventListener('install', (event) => {
    self.skipWaiting(); // Force waiting SW to become active
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
});

// Activate event: Clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        Promise.all([
            self.clients.claim(), // Become available to all pages
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cache) => {
                        if (cache !== CACHE_NAME && cache !== DYNAMIC_CACHE) {
                            return caches.delete(cache);
                        }
                    })
                );
            })
        ])
    );
});

// Fetch event: Network First, then Cache, then Offline Page
self.addEventListener('fetch', (event) => {
    // Skip cross-origin requests
    if (!event.request.url.startsWith(self.location.origin)) return;

    event.respondWith(
        fetch(event.request)
            .then((fetchRes) => {
                // Cache successful GET requests
                if (!fetchRes || fetchRes.status !== 200 || fetchRes.type !== 'basic') {
                    return fetchRes;
                }
                // Clone response to cache it
                const responseToCache = fetchRes.clone();
                if (event.request.method === 'GET') {
                    caches.open(DYNAMIC_CACHE).then((cache) => {
                        cache.put(event.request, responseToCache);
                    });
                }
                return fetchRes;
            })
            .catch(() => {
                // If network fails, try cache
                return caches.match(event.request).then((cachedRes) => {
                    if (cachedRes) return cachedRes;
                    // If not in cache and it's a page navigation, show offline page
                    if (event.request.headers.get('accept').includes('text/html')) {
                        return caches.match('/offline/');
                    }
                });
            })
    );
});
// ... existing code ...

// ==========================================
// WEB PUSH NOTIFICATIONS
// ==========================================

// ==========================================
// WEB PUSH NOTIFICATIONS (Background & Foreground)
// ==========================================

self.addEventListener('push', function (event) {
    if (event.data) {
        let data = {};
        try {
            data = event.data.json();
        } catch (e) {
            console.error('Push data is not JSON:', event.data.text());
            data = { title: 'New Notification', body: event.data.text() };
        }

        const title = data.title || data.head || 'Annamalai University';
        const options = {
            body: data.body || 'You have a new update.',
            icon: '/static/imgs/annamalai.png',     // Main icon (192x192)
            badge: '/static/imgs/aublack.png',       // Small monochrome icon for status bar
            vibrate: [100, 50, 100],
            data: {
                url: data.url || '/',                // Target URL for click
                ...data                              // Store full data
            },
            actions: data.actions || [],             // Optional actions
            tag: data.tag || 'au-notification'       // Grouping
        };

        event.waitUntil(
            self.registration.showNotification(title, options)
        );
    } else {
        console.warn('Push event received with no data.');
    }
});

self.addEventListener('notificationclick', function (event) {
    event.notification.close();

    const targetUrl = new URL(event.notification.data.url, self.location.origin).href;

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
            // Check if there is already a window/tab open with the target URL
            for (let i = 0; i < windowClients.length; i++) {
                const client = windowClients[i];
                if (client.url === targetUrl && 'focus' in client) {
                    return client.focus();
                }
            }
            // If not, open a new window
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});
