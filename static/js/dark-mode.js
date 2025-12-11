(function () {
  const STORAGE_KEY = 'theme';
  const LOCK_KEY = 'theme_locked';
  const DARK_CLASS = 'dark';

  function applyDarkClass(isDark) {
    try {
      if (isDark) {
        document.documentElement.classList.add(DARK_CLASS);
        if (document.body) document.body.classList.add(DARK_CLASS);
      } else {
        document.documentElement.classList.remove(DARK_CLASS);
        if (document.body) document.body.classList.remove(DARK_CLASS);
      }
    } catch (e) {
      // ignore in case document isn't available
    }
  }

  function updateIcons(isDark) {
    const sun = document.getElementById('sun-icon');
    const moon = document.getElementById('moon-icon');
    if (sun) sun.style.opacity = isDark ? '0' : '1';
    if (moon) moon.style.opacity = isDark ? '1' : '0';
  }

  function setTheme(isDark, persist = true) {
    applyDarkClass(isDark);
    updateIcons(isDark);
    // Debug: report current state
    try {
      console.debug('[dark-mode] setTheme ->', isDark ? 'dark' : 'light');
    } catch (e) {}
    try {
      if (persist) localStorage.setItem(STORAGE_KEY, isDark ? 'dark' : 'light');
    } catch (e) {
      // localStorage may be unavailable in some contexts
    }
  }

  // Inicialización temprana (se ejecuta al cargar en <head> para evitar FOUC)
  (function init() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'dark') {
        setTheme(true, false);
        return;
      }
      if (stored === 'light') {
        setTheme(false, false);
        return;
      }
    } catch (e) {
      // ignore
    }

    // Si no hay preferencia guardada, respetar prefers-color-scheme
    try {
      const prefersDark =
        window.matchMedia &&
        window.matchMedia('(prefers-color-scheme: dark)').matches;
      setTheme(!!prefersDark, false);
    } catch (e) {
      // default: light
      setTheme(false, false);
    }
  })();

  // Función global para alternar el modo (usada en `base.html`)
  window.toggleDarkMode = function () {
    try {
      const isDark = document.documentElement.classList.contains(DARK_CLASS);
      // If theme is locked by user preference, prevent switching away from locked value
      try {
        const locked = localStorage.getItem(LOCK_KEY);
        const lockedTheme = localStorage.getItem(STORAGE_KEY);
        if (locked === '1' && lockedTheme === 'dark' && isDark) {
          // already dark and locked -> do nothing
          console.debug('[dark-mode] theme is locked to dark; ignoring toggle');
          return;
        }
        if (locked === '1' && lockedTheme === 'light' && !isDark) {
          console.debug('[dark-mode] theme is locked to light; ignoring toggle');
          return;
        }
      } catch (e) {
        // ignore localStorage issues
      }

      console.debug('[dark-mode] toggleDarkMode current ->', isDark ? 'dark' : 'light');
      setTheme(!isDark, true);
      console.debug('[dark-mode] toggleDarkMode new ->', !isDark ? 'dark' : 'light');
    } catch (e) {
      console.error('[dark-mode] toggleDarkMode error', e);
    }
  };

  // Allow external code to set/unset a lock on theme preference
  window.setThemeLock = function (lock) {
    try {
      if (lock) localStorage.setItem(LOCK_KEY, '1');
      else localStorage.removeItem(LOCK_KEY);
    } catch (e) {}
  };

  // Exponer función para leer el estado actual
  window.getTheme = function () {
    try {
      return (
        localStorage.getItem(STORAGE_KEY) ||
        (document.documentElement.classList.contains(DARK_CLASS)
          ? 'dark'
          : 'light')
      );
    } catch (e) {
      return document.documentElement.classList.contains(DARK_CLASS)
        ? 'dark'
        : 'light';
    }
  };

  // Enlazar botones si existen (uno en header y otro en drawer)
  document.addEventListener('DOMContentLoaded', function () {
    const btnIds = ['theme-toggle'];
    btnIds.forEach(function (id) {
      const btn = document.getElementById(id);
      if (btn) {
        btn.addEventListener('click', function (e) {
          e.preventDefault();
          console.debug('[dark-mode] clicked:', id);
          window.toggleDarkMode();
        });
      }
    });

    // También soportar botones con atributo data-theme-toggle por delegación
    document.body.addEventListener('click', function (e) {
      const toggle =
        e.target.closest && e.target.closest('[data-theme-toggle]');
      if (toggle) {
        e.preventDefault();
        console.debug('[dark-mode] clicked data-theme-toggle element');
        window.toggleDarkMode();
      }
    });
  });
})();
