/**
 * ◑ MiMiNox v2 — Agent Detail Modal (Radar-Chart + Learning-Log)
 * Task 4.2c: Radar-Chart
 * Task 4.5: Gedanken-Dekomposition-View
 */
import { useEffect, useRef } from 'react';

const SKILL_KEYS = ['codeQuality', 'bugDetection', 'architecture', 'research', 'speed', 'toolMastery', 'communication', 'testing'];
const SKILL_SHORT = ['Code', 'Bugs', 'Arch', 'Rsrch', 'Speed', 'Tools', 'Comms', 'Test'];

function drawRadar(canvas, skills) {
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  const cx = w / 2, cy = h / 2;
  const r = Math.min(w, h) / 2 - 40;
  const n = SKILL_KEYS.length;

  ctx.clearRect(0, 0, w, h);

  // Grid rings
  for (let ring = 1; ring <= 4; ring++) {
    const rr = r * (ring / 4);
    ctx.beginPath();
    for (let i = 0; i <= n; i++) {
      const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
      const x = cx + rr * Math.cos(angle);
      const y = cy + rr * Math.sin(angle);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  // Axes
  for (let i = 0; i < n; i++) {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + r * Math.cos(angle), cy + r * Math.sin(angle));
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.stroke();

    // Labels
    const lx = cx + (r + 20) * Math.cos(angle);
    const ly = cy + (r + 20) * Math.sin(angle);
    ctx.fillStyle = '#9CA3AF';
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(SKILL_SHORT[i], lx, ly);
  }

  // Data polygon
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const val = (skills[SKILL_KEYS[i]] || 0) / 100;
    const x = cx + r * val * Math.cos(angle);
    const y = cy + r * val * Math.sin(angle);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fillStyle = 'rgba(118, 185, 0, 0.12)';
  ctx.fill();
  ctx.strokeStyle = '#76B900';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Data dots
  for (let i = 0; i < n; i++) {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const val = (skills[SKILL_KEYS[i]] || 0) / 100;
    const x = cx + r * val * Math.cos(angle);
    const y = cy + r * val * Math.sin(angle);
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#76B900';
    ctx.fill();
  }
}

function ThoughtTree({ thoughts = [] }) {
  if (!thoughts.length) {
    return (
      <div style={{ color: 'var(--text-muted)', fontSize: '12px', padding: '8px' }}>
        Noch keine Gedankenflüsse aufgezeichnet.
      </div>
    );
  }

  return (
    <div className="thought-tree">
      {thoughts.map((t, i) => (
        <div key={i} className="thought-node">
          <div className="thought-branch" />
          <div className="thought-content">
            <span className="thought-marker">💭</span>
            {t.root || t}
            {t.children?.map((c, j) => (
              <div key={j} className="thought-child">
                <span className="thought-leaf">→</span>
                {c.text || c}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function AgentDetailModal({ agent, onClose, thoughts = [] }) {
  const canvasRef = useRef(null);
  const profile = agent?.skills || {};
  const skills = profile.skills || {};

  useEffect(() => {
    if (canvasRef.current && Object.keys(skills).length > 0) {
      drawRadar(canvasRef.current, skills);
    }
  }, [skills]);

  if (!agent) return null;

  return (
    <div className="modal-overlay" onClick={onClose} id="agent-detail-modal">
      <div className="modal-content glass" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 style={{ fontSize: '16px', fontWeight: 600 }}>
            {agent.id} — LV.{profile.level || 1}
          </h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          {/* Radar Chart */}
          <div className="radar-section">
            <canvas
              ref={canvasRef}
              width={280}
              height={280}
              style={{ display: 'block', margin: '0 auto' }}
            />
          </div>

          {/* Gedanken-Dekomposition */}
          <div className="thoughts-section">
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px' }}>
              🧠 Gedankenflüsse
            </div>
            <ThoughtTree thoughts={thoughts} />
          </div>
        </div>
      </div>
    </div>
  );
}
