/**
 * ◑ MiMiNox v2 — Krisen-Dashboard
 * Outdoor-KI · 100% Offline · Gemma 4 E4B
 * Clean Black + NVIDIA Green · Mobile-First
 */
import { useState, useCallback, useRef } from 'react';
import { useDashboardData } from './hooks/useApi';
import { useSocket } from './hooks/useSocket';
import { AgentCard } from './components/AgentCard';
import { ChatPanel } from './components/ChatPanel';
import { KanbanBoard } from './components/KanbanBoard';
import { MetricsPanel } from './components/MetricsPanel';
import { TaskInput } from './components/TaskInput';
import { AgentDetailModal } from './components/AgentDetailModal';

const TABS = [
  { id: 'chat',   icon: '💬', label: 'Chat' },
  { id: 'kanban', icon: '📋', label: 'Board' },
  { id: 'agents', icon: '🤖', label: 'Team' },
];

function App() {
  const { agents, chat, kanban, isLive, setAgents, setChat, setKanban, setIsLive } = useDashboardData();
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [skillToast, setSkillToast] = useState(null);
  const [activeTab, setActiveTab] = useState('chat');
  const toastTimerRef = useRef(null);

  // Socket.io real-time events
  const handleSocketEvent = useCallback((event) => {
    switch (event.type) {
      case 'connected':
        setIsLive(true);
        break;
      case 'disconnected':
        setIsLive(false);
        break;
      case 'agent_updated':
        setAgents(prev => prev.map(a =>
          a.id === event.agentId ? { ...a, ...event.data } : a
        ));
        if (event.data?.skillGain) {
          const { skill, amount } = event.data.skillGain;
          showSkillToast(`+${amount} ${skill}!`);
        }
        break;
      case 'chat_message':
        setChat(prev => [...prev, event]);
        break;
      case 'ticket_moved':
        setKanban(prev => {
          const next = { ...prev };
          for (const col of Object.keys(next)) {
            next[col] = (next[col] || []).filter(t => t.id !== event.ticketId);
          }
          const targetCol = event.newStatus || 'backlog';
          next[targetCol] = [...(next[targetCol] || []), {
            id: event.ticketId,
            title: event.title || `Ticket #${event.ticketId}`,
            assignee: event.assignee || 'unknown',
          }];
          return next;
        });
        break;
      case 'agent_level_up':
        showSkillToast(`🎉 ${event.agentId} → Level ${event.newLevel}!`);
        break;
      default:
        break;
    }
  }, [setAgents, setChat, setKanban, setIsLive]);

  useSocket(handleSocketEvent);

  function showSkillToast(msg) {
    setSkillToast(msg);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setSkillToast(null), 3000);
  }

  function handleAgentClick(agentId) {
    if (selectedAgent === agentId && showModal) {
      setShowModal(false);
      setSelectedAgent(null);
    } else {
      setSelectedAgent(agentId);
      setShowModal(true);
    }
  }

  const activeAgent = agents.find(a => a.id === selectedAgent);
  const ticketCount = Object.values(kanban).reduce((s, c) => s + (c?.length || 0), 0);

  return (
    <div className="dashboard">
      {/* ── Header ──────────────────────────────────────────────── */}
      <header className="header" id="dashboard-header">
        <div className="header-logo">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="var(--green)" strokeWidth="2" fill="none" />
            <circle cx="12" cy="12" r="3" fill="var(--green)" />
          </svg>
          <span>Mimi</span>Nox
        </div>
        <div className="header-status">
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span className={`status-dot ${isLive ? 'running' : 'error'}`} />
            {isLive ? 'LIVE' : 'DEMO'}
          </span>
          <span>{agents.length} Agents · {ticketCount} Tasks</span>
        </div>
      </header>

      {/* ── Main Content ────────────────────────────────────────── */}
      <div className="main-content">
        {/* Agent Panel (visible on Desktop ≥1200px, or via Tab on Mobile) */}
        <div className={`panel-view panel-view--agents ${activeTab === 'agents' ? 'active' : ''}`} id="agent-panel">
          <div className="agent-list">
            {agents.map(agent => (
              <AgentCard
                key={agent.id}
                agent={agent}
                active={selectedAgent === agent.id}
                onClick={() => handleAgentClick(agent.id)}
              />
            ))}
          </div>
        </div>

        {/* Center: Chat + Kanban + Input */}
        <div className={`panel-view panel-view--center ${activeTab === 'chat' || activeTab === 'kanban' ? 'active' : ''}`} id="center-panel">
          <ChatPanel messages={chat} />
          <KanbanBoard kanban={kanban} />
          <TaskInput />
        </div>

        {/* Right: Metrics only (no 3D graph) */}
        <div className={`panel-view panel-view--right ${activeTab === 'agents' ? '' : 'active'}`} id="right-panel">
          <MetricsPanel agents={agents} kanban={kanban} />
        </div>
      </div>

      {/* ── Mobile Tab Bar ──────────────────────────────────────── */}
      <nav className="tab-bar" id="tab-bar">
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="tab-icon">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </nav>

      {/* ── Agent Detail Modal ──────────────────────────────────── */}
      {showModal && activeAgent && (
        <AgentDetailModal
          agent={activeAgent}
          thoughts={[]}
          onClose={() => { setShowModal(false); setSelectedAgent(null); }}
        />
      )}

      {/* ── Toast ───────────────────────────────────────────────── */}
      {skillToast && (
        <div className="skill-toast" id="skill-toast">{skillToast}</div>
      )}
    </div>
  );
}

export default App;
