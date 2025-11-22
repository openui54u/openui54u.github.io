// Minimal SW for offline cache
const CACHE = 'adv-market-v1';
const FILES = ['./','./index.html','./styles.css','./app.js'];
self.addEventListener('install', evt=>{ evt.waitUntil(caches.open(CACHE).then(c=>c.addAll(FILES))); self.skipWaiting(); });
self.addEventListener('activate', evt=>{ evt.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', evt=>{ evt.respondWith(caches.match(evt.request).then(r=> r || fetch(evt.request))); });
