// public/sw.js
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : { 
    title: 'RedHuawei', 
    body: 'Actualización de tiempos',
    mode: 'multiple' 
  };

  const options = {
    body: data.body,
    icon: '/favicon.ico',
    badge: '/favicon.ico',
    vibrate: [200, 100, 200],
    // Si el modo es 'single', usamos un tag fijo para que se sobrescriba
    tag: data.mode === 'single' ? 'red-huawei-update' : undefined,
    renotify: data.mode === 'single' ? false : true
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Esto ayuda a que el SW tome el control inmediatamente
self.addEventListener('install', () => self.skipWaiting());