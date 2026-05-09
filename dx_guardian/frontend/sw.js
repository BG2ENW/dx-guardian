// DX Guardian Service Worker - Web Push 接收
const CACHE_NAME = 'dx-guardian-v1';
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/js/app.js',
    '/js/alerts.js',
    '/js/score_display.js',
    '/css/leaflet.css'
];

// 安装
self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

// 激活
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

// 推送通知
self.addEventListener('push', (e) => {
    let data = { title: 'DX Guardian', body: '新 Spot 来了', icon: '/images/icon-192.png' };
    if (e.data) {
        try {
            data = e.data.json();
        } catch (err) {
            data.body = e.data.text();
        }
    }
    e.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: data.icon || '/images/icon-192.png',
            badge: '/images/badge-72.png',
            tag: data.tag || 'dx-spot',
            data: data.data || {},
            actions: data.actions || [],
            vibrate: [100, 50, 100],
            renotify: true
        })
    );
});

// 点击通知
self.addEventListener('notificationclick', (e) => {
    e.notification.close();
    const url = e.notification.data?.url || '/#alerts';
    e.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
            for (const client of clientList) {
                if (client.url.includes(self.location.origin) && 'focus' in client) {
                    client.focus();
                    client.navigate(url);
                    return;
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        })
    );
});
