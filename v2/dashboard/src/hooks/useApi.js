/**
 * ◑ MiMiNox v2 — API Hook
 * dashboard/src/hooks/useApi.js
 *
 * Fetcht Daten vom Backend und pollt alle 2 Sekunden.
 * Fallback: Statische Demo-Daten für Offline-Entwicklung.
 */
import { useState, useEffect, useCallback } from 'react';

const API_BASE = window.location.port === '5173'
  ? 'http://localhost:3001'   // Vite dev → proxy to backend
  : '';                        // Production → relative URLs

// Demo data for when backend is not running
const DEMO_DATA = {
  agents: [
    { id: 'medic_agent', role: 'medic', status: 'idle',
      skills: { level: 1, xp: 0, skills: { firstAid: 70, diagnosis: 60, trauma: 50, pharmacy: 45, communication: 70 } } },
    { id: 'engineer_agent', role: 'engineer', status: 'idle',
      skills: { level: 1, xp: 0, skills: { solar: 65, electronics: 70, mechanics: 60, networking: 55, communication: 50 } } },
    { id: 'navigator_agent', role: 'navigator', status: 'idle',
      skills: { level: 1, xp: 0, skills: { terrain: 70, compass: 65, mapping: 60, weather: 55, communication: 60 } } },
    { id: 'sensor_agent', role: 'sensor', status: 'idle',
      skills: { level: 1, xp: 0, skills: { monitoring: 75, alerting: 70, optimization: 60, communication: 80 } } },
  ],
  chat: [
    { from: 'system', to: 'all', content: '🚨 MiMiNox Krisen-KI gestartet. Team bereit.', type: 'message', timestamp: new Date().toISOString() },
    { from: 'user', to: 'medic_agent', content: '🚑 Jemand hat sich am Arm verbrannt', type: 'task', timestamp: new Date().toISOString() },
    { from: 'medic_agent', to: 'user', content: 'Sofort kühlen mit sauberem Wasser (15-20 Min). Keine Salben! Bei Blasen: steril abdecken.', type: 'message', timestamp: new Date().toISOString() },
    { from: 'user', to: 'engineer_agent', content: '🛠️ Solarpanel liefert keinen Strom mehr', type: 'task', timestamp: new Date().toISOString() },
    { from: 'engineer_agent', to: 'user', content: 'Prüfe die Steckverbindungen und reinige die Oberfläche. MC4-Stecker oft korrodiert.', type: 'message', timestamp: new Date().toISOString() },
  ],
  kanban: {
    backlog: [{ id: 1, title: 'Wundversorgung prüfen', assignee: 'medic_agent' }],
    in_progress: [{ id: 2, title: 'Solar-Panel diagnostizieren', assignee: 'engineer_agent' }],
    testing: [],
    done: [{ id: 3, title: 'Verbrennung behandelt', assignee: 'medic_agent' }],
  },
};

export function useApi(path, pollInterval = 2000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLive, setIsLive] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}${path}`, { signal: AbortSignal.timeout(1500) });
      if (!res.ok) throw new Error(`${res.status}`);
      const json = await res.json();
      setData(json);
      setIsLive(true);
      setError(null);
    } catch {
      setIsLive(false);
      // Use demo data only on first load
      if (!data) {
        const key = path.replace('/api/', '').replace('/history', '');
        if (DEMO_DATA[key]) setData(DEMO_DATA[key]);
      }
    }
  }, [path]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, pollInterval);
    return () => clearInterval(interval);
  }, [fetchData, pollInterval]);

  return { data, error, isLive };
}

export function useDashboardData() {
  const [agents, setAgents] = useState(DEMO_DATA.agents);
  const [chat, setChat] = useState(DEMO_DATA.chat);
  const [kanban, setKanban] = useState(DEMO_DATA.kanban);
  const [isLive, setIsLive] = useState(false);

  // Poll backend for initial data
  useEffect(() => {
    async function poll() {
      try {
        const [agRes, chRes, knRes] = await Promise.all([
          fetch(`${API_BASE}/api/agents`, { signal: AbortSignal.timeout(1500) }),
          fetch(`${API_BASE}/api/chat/history`, { signal: AbortSignal.timeout(1500) }),
          fetch(`${API_BASE}/api/kanban`, { signal: AbortSignal.timeout(1500) }),
        ]);
        if (agRes.ok) { setAgents(await agRes.json()); setIsLive(true); }
        if (chRes.ok) setChat(await chRes.json());
        if (knRes.ok) setKanban(await knRes.json());
      } catch {
        // Backend offline — demo data stays
      }
    }
    poll();
    const interval = setInterval(poll, 3000);
    return () => clearInterval(interval);
  }, []);

  return {
    agents, chat, kanban, isLive,
    setAgents, setChat, setKanban, setIsLive,
  };
}
