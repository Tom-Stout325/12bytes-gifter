// Gifter Service Worker
const CACHE_NAME = "gifter-v1";

// Add any core pages + static assets you want cached on install
const URLS_TO_CACHE = [
  "/",
  "/offline/",
  "/static/images/offline.png",
  "/static/images/logo.png",
  "/static/images/favicon.ico",
  "/static/styles/index.css",

];



// Install event — cache core assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(URLS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// Activate event — clean up old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// Fetch event — network first, fallback to cache, then offline.html
self.addEventListener("fetch", (event) => {
  // Do not intercept non-GET requests
  if (event.request.method !== "GET") {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Clone response and store it in cache dynamically
        const cloned = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, cloned);
        });
        return response;
      })
      .catch(() => {
        // If network fails, try cache
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          // Otherwise show offline fallback
          return caches.match("/offline/");
        });
      })
  );
});
