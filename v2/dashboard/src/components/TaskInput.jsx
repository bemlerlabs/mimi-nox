/**
 * ◑ MiMiNox v2 — Task Input Bar
 * Erlaubt dem User, neue Aufträge einzugeben.
 */
import { useState } from 'react';

export function TaskInput({ onSubmit }) {
  const [value, setValue] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!value.trim() || loading) return;

    setLoading(true);
    try {
      const apiBase = window.location.port === '5173' ? 'http://localhost:3001' : '';
      await fetch(`${apiBase}/api/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: value.trim() }),
      });
      setValue('');
      onSubmit?.();
    } catch (err) {
      console.warn('Backend offline:', err.message);
    }
    setLoading(false);
  };

  return (
    <form className="task-input-bar glass" onSubmit={handleSubmit} id="task-input">
      <input
        className="task-input"
        type="text"
        placeholder="Was brauchst du? z.B. /medic Verbrennung..."
        value={value}
        onChange={e => setValue(e.target.value)}
        disabled={loading}
      />
      <button className="task-submit" type="submit" disabled={loading}>
        {loading ? '...' : '◑ Senden'}
      </button>
    </form>
  );
}
