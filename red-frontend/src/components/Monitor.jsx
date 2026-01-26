import React, { useState, useEffect, useRef } from 'react';

const BASE_PARADEROS = ["PB719", "PB720", "PC123", "PA456", "PD789"]; 
const LOADING_STEPS = ["Conectando...", "Consultando Red...", "Procesando...", "Casi listo..."];
const API_URL = import.meta.env.PUBLIC_API_URL || "http://localhost:8000";

export default function Monitor() {
  const [input, setInput] = useState('');
  const [sugerencias, setSugerencias] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [datos, setDatos] = useState(null);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0);
  const [showSug, setShowSug] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [notifMode, setNotifMode] = useState('single'); 
  const [favoritos, setFavoritos] = useState([]);
  const [historial, setHistorial] = useState([]);
  const [showTooltip, setShowTooltip] = useState(false);

  const searchWrapperRef = useRef(null);
  const stepIntervalRef = useRef(null);

  useEffect(() => {
    const savedFavs = localStorage.getItem('fav_paraderos');
    const savedHist = localStorage.getItem('hist_paraderos');
    if (savedFavs) setFavoritos(JSON.parse(savedFavs));
    if (savedHist) setHistorial(JSON.parse(savedHist));

    const handleClickOutside = (e) => {
      if (searchWrapperRef.current && !searchWrapperRef.current.contains(e.target)) {
        setShowSug(false);
        setShowTooltip(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    localStorage.setItem('fav_paraderos', JSON.stringify(favoritos));
  }, [favoritos]);

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

  const consultarAPI = async (codigo) => {
    if (!codigo) return;
    const codFinal = String(codigo).trim().toUpperCase();
    setInput(codFinal);
    setShowSug(false);
    setLoading(true); setDatos(null); setStep(0);
    
    stepIntervalRef.current = setInterval(() => {
      setStep(s => (s < LOADING_STEPS.length - 1 ? s + 1 : s));
    }, 800);

    try {
      const res = await fetch(`${API_URL}/paradero/${codFinal}`);
      if (!res.ok) throw new Error("No encontrado");
      const data = await res.json();
      setDatos(data);
      if (!historial.includes(codFinal)) setHistorial(prev => [codFinal, ...prev].slice(0, 10));
    } catch (e) {
      setErrorMsg(e.message);
    } finally {
      setLoading(false);
      clearInterval(stepIntervalRef.current);
    }
  };

  return (
    <div className="monitor-container">
      {loading && (
        <div className="loading-screen">
          <div className="loading-content">
            <div className="spinner"></div>
            <p className="loading-text">{LOADING_STEPS[step]}</p>
          </div>
        </div>
      )}

      <div className="search-section" ref={searchWrapperRef}>
        <div className="search-group">
          <input 
            className="main-input" 
            value={input} 
            onFocus={() => setShowSug(true)}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                consultarAPI(selectedIndex >= 0 ? sugerencias[selectedIndex] : input);
              }
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setSelectedIndex(p => (p < sugerencias.length - 1 ? p + 1 : p));
              }
              if (e.key === "ArrowUp") {
                e.preventDefault();
                setSelectedIndex(p => (p > 0 ? p - 1 : -1));
              }
            }}
            placeholder="Paradero (ej: PB719)" 
          />
          <button className="btn-ir" onClick={() => consultarAPI(input)}>Ir</button>
          
          {/* RECOMENDACIONES: Ahora dentro de search-group para posicionamiento absoluto real */}
          {showSug && sugerencias.length > 0 && (
            <ul className="sug-list">
              {sugerencias.map((s, i) => (
                <li 
                  key={s} 
                  className={`sug-item ${i === selectedIndex ? 'active' : ''}`}
                  onMouseEnter={() => setSelectedIndex(i)}
                  onClick={() => consultarAPI(s)}
                >
                  <span className="sug-text">{favoritos.includes(s) ? '⭐' : '📍'} {s}</span>
                  <button 
                    className={`sug-fav-btn ${favoritos.includes(s) ? 'is-fav' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setFavoritos(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]);
                    }}
                  >
                    {favoritos.includes(s) ? '✕' : '☆'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="notif-bar-inline">
          <div className="notif-label-group">
            <span className="label-text">Notificaciones:</span>
            <div className="tooltip-wrapper">
              <button className="info-icon" onClick={() => setShowTooltip(!showTooltip)}>ⓘ</button>
              {showTooltip && (
                <div className="tooltip-popover">
                  <p><strong>Única:</strong> Una sola notificación que se actualiza.</p>
                  <p><strong>Múltiples:</strong> Nueva notificación por cada micro.</p>
                </div>
              )}
            </div>
          </div>
          
          <div className="mode-switch">
            <button className={`switch-btn ${notifMode === 'single' ? 'active' : ''}`} onClick={() => setNotifMode('single')}>Única</button>
            <button className={`switch-btn ${notifMode === 'multiple' ? 'active' : ''}`} onClick={() => setNotifMode('multiple')}>Múltiples</button>
          </div>
        </div>
      </div>

      <div className="content-area">
        {errorMsg && <div className="error-box">⚠️ {errorMsg}</div>}
        {datos && (
          <div className="bus-results">
            <h2 className="paradero-title">{datos.paradero}</h2>
            {datos.notificacion.split('\n').filter(l => l.trim()).map((line, i) => (
              <div key={i} className="bus-card">{line}</div>
            ))}
          </div>
        )}
      </div>

      <style>{`
        .monitor-container { max-width: 600px; margin: 0 auto; padding: 15px; background: #000; min-height: 100vh; color: #fff; font-family: system-ui, sans-serif; }

        .loading-screen { position: fixed; inset: 0; background: rgba(0,0,0,0.95); display: flex; align-items: center; justify-content: center; z-index: 3000; backdrop-filter: blur(8px); }
        .loading-content { display: flex; flex-direction: column; align-items: center; }
        .spinner { width: 40px; height: 40px; border: 4px solid #222; border-top-color: #e00; border-radius: 50%; animation: spin 1s infinite linear; margin-bottom: 15px; }

        .search-section { position: sticky; top: 0; z-index: 1000; background: #000; padding: 10px 0; border-bottom: 1px solid #111; }
        .search-group { display: flex; gap: 8px; position: relative; margin-bottom: 12px; }
        .main-input { flex: 1; background: #111; border: 2px solid #333; color: #fff; padding: 14px; border-radius: 12px; font-size: 1rem; outline: none; }
        .btn-ir { background: #e00; color: #fff; border: none; padding: 0 20px; border-radius: 12px; font-weight: 900; }

        /* RECOMENDACIONES SOBRE TODO */
        .sug-list { 
          position: absolute; 
          top: calc(100% + 5px); 
          left: 0; 
          right: 0; 
          background: #161616; 
          border: 1px solid #333; 
          border-radius: 12px; 
          z-index: 2000; 
          box-shadow: 0 15px 50px rgba(0,0,0,0.9); 
          max-height: 280px; 
          overflow-y: auto; 
          padding: 0; 
          margin: 0;
        }
        .sug-item { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; border-bottom: 1px solid #222; cursor: pointer; }
        .sug-item.active { background: #00d1ff15; color: #00d1ff; }
        .sug-fav-btn { background: none; border: none; color: #444; font-size: 1.2rem; cursor: pointer; }
        .sug-fav-btn.is-fav { color: #ffd700; }

        .notif-bar-inline { display: flex; align-items: center; justify-content: space-between; }
        .notif-label-group { display: flex; align-items: center; gap: 6px; }
        .label-text { font-size: 0.8rem; color: #666; font-weight: 600; }
        .info-icon { background: none; border: none; color: #00d1ff; font-size: 1.1rem; cursor: pointer; padding: 0; }
        
        .tooltip-popover { position: absolute; top: 100%; left: 0; width: 220px; background: #1a1a1a; border: 1px solid #333; padding: 12px; border-radius: 10px; z-index: 1500; margin-top: 10px; }
        .tooltip-popover p { margin: 0 0 6px 0; font-size: 0.75rem; color: #aaa; line-height: 1.4; }

        .mode-switch { display: flex; background: #111; padding: 2px; border-radius: 10px; border: 1px solid #222; }
        .switch-btn { border: none; background: none; color: #555; padding: 6px 12px; border-radius: 8px; font-size: 0.75rem; font-weight: 700; cursor: pointer; }
        .switch-btn.active { background: #222; color: #00d1ff; }

        .content-area { padding-top: 20px; }
        .paradero-title { color: #e00; font-size: 1.3rem; margin-bottom: 15px; }
        .bus-card { background: #0a0a0a; border: 1px solid #222; padding: 15px; border-radius: 12px; border-left: 4px solid #e00; margin-bottom: 10px; font-family: monospace; }

        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}