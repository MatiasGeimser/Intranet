/* Service worker de la Intranet: notificaciones push del chat institucional. */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));

self.addEventListener('push', event => {
    let data = {};
    try { data = event.data ? event.data.json() : {}; } catch (e) { data = { body: event.data && event.data.text() }; }
    const title = data.title || 'Intranet';
    const options = {
        body: data.body || 'Nuevo mensaje',
        icon: '/static/images/icon-192.png',
        badge: '/static/images/icon-192.png',
        tag: data.tag || 'intranet-chat',
        renotify: true,
        vibrate: [120, 60, 120],
        data: { url: data.url || '/admin-chat' },
    };
    event.waitUntil((async () => {
        // Si la intranet está abierta y en primer plano, la página ya avisa con sonido y aviso interno.
        const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
        if (windows.some(client => client.focused && client.visibilityState === 'visible')) return;
        await self.registration.showNotification(title, options);
    })());
});

self.addEventListener('notificationclick', event => {
    event.notification.close();
    const target = new URL((event.notification.data && event.notification.data.url) || '/admin-chat', self.location.origin).href;
    event.waitUntil((async () => {
        const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
        for (const client of windows) {
            if (new URL(client.url).origin === self.location.origin) {
                await client.focus();
                if ('navigate' in client) return client.navigate(target);
                return;
            }
        }
        return self.clients.openWindow(target);
    })());
});
