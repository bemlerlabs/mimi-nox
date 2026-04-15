/**
 * ◑ MiMiNox v2 — Agent Skill-Sheet Card
 * Task 4.2: Skill-Bars sichtbar
 */

const SKILL_LABELS = {
  codeQuality: 'Code',
  bugDetection: 'Bugs',
  architecture: 'Arch',
  research: 'Research',
  speed: 'Speed',
  toolMastery: 'Tools',
  communication: 'Comms',
  testing: 'Testing',
};

const ROLE_EMOJIS = { ceo: '👩', cto: '👨', developer: '👨‍💻', qa: '👩‍🔬' };
const ROLE_NAMES = { ceo: 'Alice CEO', cto: 'Bob CTO', developer: 'Charlie Dev', qa: 'Diana QA' };

function getBarClass(value) {
  if (value < 35) return 'low';
  if (value < 65) return 'mid';
  return 'high';
}

export function AgentCard({ agent, active, onClick }) {
  const profile = agent.skills || {};
  const skills = profile.skills || {};
  const level = profile.level || 1;
  const xp = profile.xp || 0;

  return (
    <div
      className={`glass-card agent-card ${active ? 'active' : ''}`}
      onClick={onClick}
      id={`agent-${agent.id}`}
    >
      <div className="agent-header">
        <div>
          <div className="agent-name">
            {ROLE_EMOJIS[agent.role] || '🤖'} {ROLE_NAMES[agent.role] || agent.id}
          </div>
          <div className="agent-role">{xp}/{level * 1000} XP</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="agent-level">LV.{level}</span>
          <span className={`status-dot ${agent.status}`} />
        </div>
      </div>

      <div className="skill-bars">
        {Object.entries(skills).map(([key, value]) => (
          <div className="skill-row" key={key}>
            <span className="skill-label">{SKILL_LABELS[key] || key}</span>
            <div className="skill-bar-track">
              <div
                className={`skill-bar-fill ${getBarClass(value)}`}
                style={{ width: `${value}%` }}
              />
            </div>
            <span className="skill-value">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
