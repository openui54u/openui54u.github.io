// Basic service worker for offline caching of the app shell
const CACHE = 'super-compound-v1';
const FILES = [
  './index.html',
  './styles.css',
  './app.js',
  './manifest.json',
  './icon.svg'
];

self.addEventListener('install', evt => {
  evt.waitUntil(caches.open(CACHE).then(cache => cache.addAll(FILES)));
  self.skipWaiting();
});

self.addEventListener('activate', evt => {
  evt.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', evt => {
  evt.respondWith(
    caches.match(evt.request).then(resp => {
      return resp || fetch(evt.request).then(r => { 
        return caches.open(CACHE).then(cache => { cache.put(evt.request, r.clone()); return r; });
      }).catch(()=>caches.match('./index.html'));
    })
  );
});
