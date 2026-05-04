/**
 * ◑ MiMiNox — Offline-Karte mit Echtzeit-Standort
 * components/MapView.jsx
 *
 * Leaflet.js + OpenStreetMap
 * GPS: Browser Geolocation API (funktioniert ohne Internet — Hardware-GPS)
 * Tiles: Werden beim Online-Sein gecacht → offline wiederverwenden
 *
 * Koordinaten werden im Memory gespeichert → Notruf kann sie lesen
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Leaflet-Marker-Icons fix (Webpack/Vite asset resolution)
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl:       'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl:     'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

const API_BASE = window.location.port === '5173' ? 'http://localhost:3001' : '';

// Puls-Icon für Echtzeit-Position
const pulseIcon = L.divIcon({
  className: '',
  html: `<div class="map-pulse-outer"><div class="map-pulse-inner"></div></div>`,
  iconSize:   [24, 24],
  iconAnchor: [12, 12],
});

export function MapView({ onClose }) {
  const mapRef       = useRef(null);    // Leaflet map instance
  const mapElRef     = useRef(null);    // DOM element
  const markerRef    = useRef(null);    // GPS-Marker
  const circleRef    = useRef(null);    // Accuracy circle
  const watchIdRef   = useRef(null);    // geolocation watchId
  const tilesRef     = useRef(null);    // tile layer

  const [position, setPosition]   = useState(null); // {lat, lng, accuracy}
  const [gpsStatus, setGpsStatus] = useState('suche…');
  const [mapStyle,  setMapStyle]  = useState('osm'); // osm | topo | satellite
  const [tracking,  setTracking]  = useState(true);
  const [copied,    setCopied]    = useState(false);

  // Karten-Tiles je nach Modus
  const TILE_LAYERS = {
    osm: {
      url:  'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      attr: '© OpenStreetMap',
      label: '🗺 Karte',
    },
    topo: {
      url:  'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
      attr: '© OpenTopoMap',
      label: '⛰ Topo',
    },
  };

  // Karte initialisieren
  useEffect(() => {
    if (mapRef.current || !mapElRef.current) return;

    const map = L.map(mapElRef.current, {
      center:          [51.1657, 10.4515], // Deutschland-Mitte Fallback
      zoom:            13,
      zoomControl:     true,
      attributionControl: true,
    });

    tilesRef.current = L.tileLayer(TILE_LAYERS.osm.url, {
      attribution: TILE_LAYERS.osm.attr,
      maxZoom:     19,
      // Tiles werden vom Service Worker gecacht → offline nutzbar
    }).addTo(map);

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Tile-Layer wechseln
  useEffect(() => {
    if (!mapRef.current || !tilesRef.current) return;
    tilesRef.current.remove();
    const layer = TILE_LAYERS[mapStyle] || TILE_LAYERS.osm;
    tilesRef.current = L.tileLayer(layer.url, {
      attribution: layer.attr,
      maxZoom: 19,
    }).addTo(mapRef.current);
  }, [mapStyle]);

  // GPS-Tracking
  const startTracking = useCallback(() => {
    if (!('geolocation' in navigator)) {
      setGpsStatus('GPS nicht verfügbar');
      return;
    }

    setGpsStatus('suche…');
    setTracking(true);

    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        const { latitude: lat, longitude: lng, accuracy } = pos.coords;
        setPosition({ lat, lng, accuracy });
        setGpsStatus(`±${Math.round(accuracy)}m`);

        const map = mapRef.current;
        if (!map) return;

        // Marker setzen oder bewegen
        if (!markerRef.current) {
          markerRef.current = L.marker([lat, lng], { icon: pulseIcon })
            .addTo(map)
            .bindPopup(`◑ Du bist hier<br/>${lat.toFixed(5)}, ${lng.toFixed(5)}`);
        } else {
          markerRef.current.setLatLng([lat, lng]);
          markerRef.current.setPopupContent(
            `◑ Du bist hier<br/>${lat.toFixed(5)}, ${lng.toFixed(5)}<br/>±${Math.round(accuracy)}m`
          );
        }

        // Genauigkeits-Kreis
        if (!circleRef.current) {
          circleRef.current = L.circle([lat, lng], {
            radius:      accuracy,
            color:       '#C4A265',
            fillColor:   '#C4A265',
            fillOpacity: 0.08,
            weight:      1,
          }).addTo(map);
        } else {
          circleRef.current.setLatLng([lat, lng]);
          circleRef.current.setRadius(accuracy);
        }

        // Karte zur Position schwenken
        map.panTo([lat, lng]);
      },
      (err) => {
        const msgs = { 1: 'Zugriff verweigert', 2: 'GPS nicht verfügbar', 3: 'Timeout' };
        setGpsStatus(msgs[err.code] || 'Fehler');
        setTracking(false);
      },
      { enableHighAccuracy: true, maximumAge: 3000, timeout: 15000 }
    );
  }, []);

  const stopTracking = useCallback(() => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    setTracking(false);
    setGpsStatus('pausiert');
  }, []);

  // Beim Öffnen direkt tracking starten
  useEffect(() => {
    startTracking();
    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
    };
  }, []);

  // Koordinaten in Zwischenablage + Memory speichern
  const handleCopyCoords = useCallback(async () => {
    if (!position) return;
    const coord = `${position.lat.toFixed(6)}, ${position.lng.toFixed(6)}`;
    try {
      await navigator.clipboard.writeText(coord);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}

    // Im Gedächtnis speichern → Gemma kann Koordinaten in Chat ausgeben
    fetch(`${API_BASE}/api/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: `Merke dir: Mein letzter bekannter Standort ist ${coord}` }),
    }).catch(() => {});
  }, [position]);

  // Zentrieren-Button
  const handleCenter = useCallback(() => {
    if (position && mapRef.current) {
      mapRef.current.setView([position.lat, position.lng], 15);
    }
  }, [position]);

  return (
    <div className="map-overlay" id="map-view">
      {/* ── Header ── */}
      <div className="map-header">
        <div className="map-header-left">
          <span className="map-title">🗺 Offline-Karte</span>
          <span className={`map-gps-badge ${tracking ? 'active' : ''}`}>
            {tracking ? '📍' : '⏸'} {gpsStatus}
          </span>
        </div>
        <div className="map-header-right">
          <button className="map-btn" onClick={handleCenter} title="Zentrieren" disabled={!position}>⊙</button>
          <button className="map-btn" onClick={onClose} title="Schließen" id="map-close">✕</button>
        </div>
      </div>

      {/* ── Tile-Style Switcher ── */}
      <div className="map-style-bar">
        {Object.entries(TILE_LAYERS).map(([key, layer]) => (
          <button
            key={key}
            className={`map-style-btn ${mapStyle === key ? 'active' : ''}`}
            onClick={() => setMapStyle(key)}
          >
            {layer.label}
          </button>
        ))}
      </div>

      {/* ── Karte ── */}
      <div ref={mapElRef} className="map-canvas" id="leaflet-map" />

      {/* ── Koordinaten-Leiste ── */}
      <div className="map-footer">
        {position ? (
          <>
            <span className="map-coords">
              {position.lat.toFixed(5)}°N &nbsp; {position.lng.toFixed(5)}°E
            </span>
            <button
              className="map-copy-btn"
              onClick={handleCopyCoords}
              id="map-copy-coords"
            >
              {copied ? '✓ Kopiert' : '📋 Kopieren'}
            </button>
            <button
              className={`map-track-btn ${tracking ? 'active' : ''}`}
              onClick={tracking ? stopTracking : startTracking}
            >
              {tracking ? '⏸ Pause' : '▶ Tracking'}
            </button>
          </>
        ) : (
          <span className="map-coords-empty">GPS wird gesucht…</span>
        )}
      </div>
    </div>
  );
}
