import React, { useState, useEffect, useRef } from 'react';

const BASE_PARADEROS = ["PB719", "PB720", "PC123", "PA456", "PD789"]; 
const LOADING_STEPS = ["Conectando...", "Consultando Red...", "Procesando...", "Casi listo..."];

// URL dinámica: En Vercel usará la de Render, en local usará localhost
const API_URL = import.meta.env.PUBLIC_API_URL || "http://localhost:8000";

export default function Monitor() {
  const [input, setInput] = useState('');
  const [sugerencias, setSugerencias] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [datos, setDatos] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [step, setStep] = useState(0);
  const [showSug, setShowSug] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [countdown, setCountdown] = useState(30);
  const [notifMode, setNotifMode] = useState('single'); 
  const [favoritos, setFavoritos] = useState([]);
  const [historial, setHistorial] = useState([]);

  // REFERENCIAS PARA EL INTERVALO Y ESTADO PERSISTENTE
  const refreshIntervalRef = useRef(null);
  const countdownIntervalRef = useRef(null);
  const stepIntervalRef = useRef(null);
  const searchWrapperRef = useRef(null);
  
  // Solución al problema de clausura: modeRef siempre tiene el valor actual de notifMode
  const modeRef = useRef(notifMode);

  useEffect(() => {
    modeRef.current = notifMode;
  }, [notifMode]);

  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(err => console.log('Error SW', err));
    }

    if (typeof window !== "undefined") {
      const savedFavs = localStorage.getItem('fav_paraderos');
      const savedHist = localStorage.getItem('hist_paraderos');
      if (savedFavs) setFavoritos(JSON.parse(savedFavs));
      if (savedHist) setHistorial(JSON.parse(savedHist));
      if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
      }
    }

    const handleClickOutside = (e) => {
      if (searchWrapperRef.current && !searchWrapperRef.current.contains(e.target)) setShowSug(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      stopAutoRefresh();
    };
  }, []);

  useEffect(() => {
    localStorage.setItem('fav_paraderos', JSON.stringify(favoritos));
    localStorage.setItem('hist_paraderos', JSON.stringify(historial));
  }, [favoritos, historial]);

  useEffect(() => {
    if (!showSug) { setSugerencias([]); return; }
    const q = (input || '').trim().toUpperCase();
    const pool = Array.from(new Set([...favoritos, ...historial, ...BASE_PARADEROS]));
    let filtered = q === '' 
      ? Array.from(new Set([...favoritos, ...historial])).slice(0, 10)
      : pool.filter(f => f.includes(q)).sort((a, b) => favoritos.includes(b) - favoritos.includes(a)).slice(0, 12);
    setSugerencias(filtered);
    setSelectedIndex(-1);
  }, [input, favoritos, historial, showSug]);


  const enviarNotificacion = (paradero, info) => {
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    
    const currentMode = modeRef.current;

    navigator.serviceWorker.ready.then(registration => {
      registration.getNotifications().then(notifications => {
        
        let tagAUsar;
        const hayNotificacionesActivas = notifications.length > 0;

        if (currentMode === 'multiple') {
          tagAUsar = `notif-${Date.now()}`;
        } else {
          // MODO FIJO: Intentamos seguir la pista de la que ya existe
          // Si la borraste, volvemos al tag base para empezar de cero
          tagAUsar = hayNotificacionesActivas 
            ? notifications[notifications.length - 1].tag 
            : 'red-huawei-fixed';
        }

        const esModoFijo = currentMode === 'single';
        // Comprobamos si la notificación que queremos editar REALMENTE está en el panel
        const existeEnPanel = notifications.some(n => n.tag === tagAUsar);

        const opciones = {
          body: info,
          icon: '/favicon.ico',
          badge: '/favicon.ico',
          tag: tagAUsar,
          data: { url: window.location.href },
          // Si la borraste (existeEnPanel = false), renotify vuelve a ser true para que aparezca
          renotify: (esModoFijo && existeEnPanel) ? false : true,
          // Si la borraste, silent es false para que te avise que volvió
          silent: esModoFijo && existeEnPanel,
        };

        if (!opciones.silent) {
          opciones.vibrate = [200, 100, 200];
        }

        registration.showNotification(`RedHuawei: ${paradero}`, opciones);

        // Limpieza: si hay más de una en modo fijo, dejamos solo la actual
        if (esModoFijo && notifications.length > 1) {
          notifications.forEach(n => {
            if (n.tag !== tagAUsar) n.close();
          });
        }
      });
    });
  };

  const stopAutoRefresh = () => {
    if (refreshIntervalRef.current) clearInterval(refreshIntervalRef.current);
    if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
  };

  const startAutoRefresh = (codigo) => {
    stopAutoRefresh();
    setCountdown(30);
    refreshIntervalRef.current = setInterval(() => {
      consultarAPI(codigo, true);
    }, 30000);
    countdownIntervalRef.current = setInterval(() => {
      setCountdown(prev => (prev > 0 ? prev - 1 : 30));
    }, 1000);
  };

  const consultarAPI = async (codigo, silencioso = false) => {
    if (!codigo) return;

    // 1. MATAR TODO EL PASADO DE INMEDIATO (ojo con el if)
    stopAutoRefresh(); 
    if (stepIntervalRef.current) clearInterval(stepIntervalRef.current);

    const codFinal = String(codigo).trim().toUpperCase();
    if (!silencioso || !showSug) setInput(codFinal);
    setShowSug(false);
    
    if (!silencioso) {
      setLoading(true); setDatos(null); setStep(0);
      stepIntervalRef.current = setInterval(() => setStep(s => (s < LOADING_STEPS.length - 1 ? s + 1 : s)), 800);
    } else {
      setIsRefreshing(true);
    }
    
    try {
      const res = await fetch(`${API_URL}/paradero/${codFinal}`);
      if (!res.ok) throw new Error("No encontrado");
      const data = await res.json();
      setDatos(data);
      setHistorial(prev => [codFinal, ...prev.filter(h => h !== codFinal)].slice(0, 10));
      
      // Llamada a notificación
      if (silencioso) enviarNotificacion(codFinal, data.notificacion);
      
      startAutoRefresh(codFinal);
    } catch (e) {
      setErrorMsg(e.message);
      stopAutoRefresh();
    } finally {
      setLoading(false); 
      setIsRefreshing(false);
      if (stepIntervalRef.current) clearInterval(stepIntervalRef.current);
    }
  };

  return (
    <div className="monitor-container">
      {/* Cargando centrado profesionalmente */}
      {loading && (
        <div className="loading-screen">
          <div className="loading-content">
            <div className="spinner"></div>
            <p>{LOADING_STEPS[step]}</p>
          </div>
        </div>
      )}

      <div className="search-section" ref={searchWrapperRef}>
        <div className="search-group">
          <input className="main-input" value={input} disabled={loading} onFocus={() => setShowSug(true)}
            onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => {
              if (e.key === "Enter") consultarAPI(selectedIndex >= 0 ? sugerencias[selectedIndex] : input);
              if (e.key === "ArrowDown") setSelectedIndex(p => (p < sugerencias.length - 1 ? p + 1 : p));
              if (e.key === "ArrowUp") setSelectedIndex(p => (p > 0 ? p - 1 : -1));
            }} placeholder="Paradero (ej: PB719)" />
          <button className="btn-ir" onClick={() => consultarAPI(input)} disabled={loading}>Ir</button>
        </div>

        <div className="notif-settings">
          <span>Notificaciones:</span>
          <button className={`mode-btn ${notifMode === 'single' ? 'active' : ''}`} onClick={() => setNotifMode('single')}>Fijas</button>
          <button className={`mode-btn ${notifMode === 'multiple' ? 'active' : ''}`} onClick={() => setNotifMode('multiple')}>Vibrar Siempre</button>
        </div>

        {showSug && sugerencias.length > 0 && (
          <ul className="sug-list">
            {sugerencias.map((s, i) => (
              <li key={s} className={`sug-item ${i === selectedIndex ? 'active' : ''}`} onClick={() => consultarAPI(s)}>
                <span>{favoritos.includes(s) ? '⭐' : '📍'} {s}</span>
                <button className="sug-fav-btn" onClick={(e) => {
                  e.stopPropagation();
                  setFavoritos(p => p.includes(s) ? p.filter(x => x !== s) : [...p, s]);
                }}>{favoritos.includes(s) ? '✕' : '☆'}</button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="content-area">
        {errorMsg && <div className="error-box">⚠️ {errorMsg}</div>}
        
        {datos && !loading && (
          <div className="results-wrapper">
            <div className="res-header">
              <div className="res-info">
                <h2>{datos.paradero}</h2>
                {isRefreshing ? (
                  <span className="refresh-tag">Sincronizando tiempo real...</span>
                ) : (
                  <span className="auto-text">Actualización en: <strong>{countdown}s</strong></span>
                )}
              </div>
              <button className={`fav-toggle ${favoritos.includes(datos.paradero) ? 'is-fav' : ''}`}
                onClick={() => {
                  const p = datos.paradero;
                  setFavoritos(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]);
                }}>{favoritos.includes(datos.paradero) ? '★' : '☆'}</button>
            </div>
            <div className="bus-grid">
              {(datos.notificacion || "").split('\n').filter(l => l.trim()).map((line, i) => (
                <div key={i} className="bus-card-modern"><div className="bus-line-content">{line}</div></div>
              ))}
            </div>
          </div>
        )}
      </div>

      <style>{`
        .monitor-container { max-width: 600px; margin: 0 auto; padding: 20px; background: #000; min-height: 100vh; color: #fff; font-family: system-ui, sans-serif; }
        
        .loading-screen { 
          position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
          background: rgba(0,0,0,0.85); display: flex; align-items: center; 
          justify-content: center; z-index: 1000; backdrop-filter: blur(5px);
        }
        .loading-content { text-align: center; }
        .spinner { 
          width: 50px; height: 50px; border: 4px solid #222; border-top-color: #e00; 
          border-radius: 50%; animation: spin 1s infinite linear; margin: 0 auto 20px; 
        }

        .search-section { position: relative; margin-bottom: 20px; }
        .search-group { display: flex; gap: 8px; }
        .main-input { flex: 1; background: #1a1a1a; border: 2px solid #333; color: #fff; padding: 12px; border-radius: 10px; font-size: 1rem; outline: none; }
        .main-input:focus { border-color: #00d1ff; }
        .btn-ir { background: #e00; color: #fff; border: none; padding: 0 20px; border-radius: 10px; font-weight: bold; cursor: pointer; }
        
        .notif-settings { display: flex; gap: 8px; align-items: center; margin-top: 12px; font-size: 0.75rem; color: #666; }
        .mode-btn { background: #111; border: 1px solid #333; color: #888; padding: 5px 12px; border-radius: 20px; cursor: pointer; }
        .mode-btn.active { border-color: #00d1ff; color: #00d1ff; background: rgba(0,209,255,0.1); }

        .sug-list { position: absolute; width: 100%; background: #1a1a1a; border: 1px solid #333; border-radius: 10px; z-index: 20; padding: 0; margin-top: 5px; box-shadow: 0 10px 30px rgba(0,0,0,0.8); overflow: hidden; }
        .sug-item { display: flex; justify-content: space-between; padding: 14px; cursor: pointer; border-bottom: 1px solid #222; }
        .sug-item.active { background: #222; color: #00d1ff; }

        .res-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #444; padding-bottom: 15px; }
        .res-info h2 { font-size: 1.6rem; color: #00d1ff; margin: 0; }
        .auto-text { font-size: 0.85rem; color: #888; }
        .auto-text strong { color: #ffd700; }
        .refresh-tag { font-size: 0.85rem; color: #00ffcc; font-weight: bold; animation: pulse 1.5s infinite; }
        
        /* Contenedor de resultados con scroll interno */
        .bus-grid { 
            display: flex; 
            flex-direction: column; 
            gap: 12px; 
            max-height: 400px; /* Altura para aprox 4 micros */
            overflow-y: auto;  /* Scroll vertical interno */
            padding-right: 5px; 
            scrollbar-width: thin;
            scrollbar-color: #333 #000;
        }

        /* Estilizar el scroll para que se vea pro en modo oscuro */
        .bus-grid::-webkit-scrollbar {
            width: 6px;
        }
        .bus-grid::-webkit-scrollbar-thumb {
            background: #333;
            border-radius: 10px;
        }

        /* Aseguramos que el buscador no se mueva tanto */
        .results-wrapper {
            display: flex;
            flex-direction: column;
        }

        .search-section {
         position: sticky;
        top: 0;
        z-index: 100;
        background: #000;
        padding-bottom: 10px;
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
      `}</style>
    </div>
  );
}