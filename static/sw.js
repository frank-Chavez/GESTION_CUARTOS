const CACHE_NAME = 'gestion-cuartos-v1';
const PRECACHE_URLS = [
  '/',
  '/static/css/output.css',
  '/static/js/dark-mode.js',
  '/static/img/acceso_directo.ico',
  '/static/img/icon-192.png',
  '/static/img/icon-512.png',
  '/static/offline.html',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) return caches.delete(key);
        })
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  // Navigation request fallback: try network, then cache, then offline page
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((resp) => {
          return resp;
        })
        .catch(() => {
          return caches
            .match(event.request)
            .then(
              (cacheResp) => cacheResp || caches.match('/static/offline.html')
            );
        })
    );
    return;
  }

  // For other requests, try cache first, then network, and update cache
  event.respondWith(
    caches.match(event.request).then((resp) => {
      if (resp) return resp;
      return fetch(event.request)
        .then((fetchResp) => {
          return caches.open(CACHE_NAME).then((cache) => {
            try {
              cache.put(event.request, fetchResp.clone());
            } catch (e) {}
            return fetchResp;
          });
        })
        .catch(() => {
          // If request is for an image, maybe return a generic cached icon
          if (event.request.destination === 'image')
            return caches.match('/static/img/icon-192.png');
          return caches.match('/static/offline.html');
        });
    })
  );
});

// Manejar push entrante
self.addEventListener('push', function(event) {
  let data = {};
  try { data = event.data.json(); } catch(e) { data = { title: 'Notificación', body: event.data ? event.data.text() : '' }; }
  const title = data.title || 'Notificación';
  const options = {
    body: data.body || '',
    icon: '/static/img/icon-192.png',
    badge: '/static/img/icon-192.png',
    data: { url: data.url || '/' }
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url ? event.notification.data.url : '/';
  event.waitUntil(clients.matchAll({ type: 'window' }).then( windowClients => {
    for (let i = 0; i < windowClients.length; i++) {
      const client = windowClients[i];
      if (client.url === url && 'focus' in client) return client.focus();
    }
    if (clients.openWindow) return clients.openWindow(url);
  }));
});
