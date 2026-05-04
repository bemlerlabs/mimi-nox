/**
 * ◑ MiMiNox — Lightweight Markdown Renderer
 * Zero-dependency inline markdown to React elements.
 * Handles: bold, italic, code, links, lists, headers, tables (basic).
 * No external library needed — stays offline-first.
 */

/**
 * Renders a markdown string as React-friendly JSX.
 * Returns an array of JSX elements.
 */
export function renderMarkdown(text) {
  if (!text) return null;

  const lines = text.split('\n');
  const elements = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Empty lines → spacer
    if (line.trim() === '') {
      i++;
      continue;
    }

    // Headers (### → h3, ## → h2, etc.)
    const headerMatch = line.match(/^(#{1,4})\s+(.+)/);
    if (headerMatch) {
      const level = headerMatch[1].length;
      const Tag = `h${level}`;
      elements.push(
        <Tag key={i} style={{ fontSize: level <= 2 ? '16px' : '14px', fontWeight: 600, margin: '12px 0 6px', color: '#E8E4DC' }}>
          {inlineFormat(headerMatch[2])}
        </Tag>
      );
      i++;
      continue;
    }

    // List items (- or *)
    if (/^\s*[-*]\s+/.test(line)) {
      const listItems = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        listItems.push(
          <li key={i} style={{ marginBottom: '4px' }}>
            {inlineFormat(lines[i].replace(/^\s*[-*]\s+/, ''))}
          </li>
        );
        i++;
      }
      elements.push(
        <ul key={`ul-${i}`} style={{ paddingLeft: '20px', margin: '6px 0' }}>
          {listItems}
        </ul>
      );
      continue;
    }

    // Numbered lists
    if (/^\s*\d+\.\s+/.test(line)) {
      const listItems = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        listItems.push(
          <li key={i} style={{ marginBottom: '4px' }}>
            {inlineFormat(lines[i].replace(/^\s*\d+\.\s+/, ''))}
          </li>
        );
        i++;
      }
      elements.push(
        <ol key={`ol-${i}`} style={{ paddingLeft: '20px', margin: '6px 0' }}>
          {listItems}
        </ol>
      );
      continue;
    }

    // Table (| ... | ... |)
    if (line.includes('|') && line.trim().startsWith('|')) {
      const tableRows = [];
      while (i < lines.length && lines[i].includes('|') && lines[i].trim().startsWith('|')) {
        const row = lines[i].trim();
        // Skip separator rows (|---|---|)
        if (/^\|[\s-:|]+\|$/.test(row)) {
          i++;
          continue;
        }
        const cells = row.split('|').filter(c => c.trim() !== '');
        tableRows.push(cells.map(c => c.trim()));
        i++;
      }
      if (tableRows.length > 0) {
        elements.push(
          <table key={`table-${i}`} style={{ borderCollapse: 'collapse', margin: '8px 0', fontSize: '13px', width: '100%' }}>
            <tbody>
              {tableRows.map((row, ri) => (
                <tr key={ri}>
                  {row.map((cell, ci) => (
                    <td key={ci} style={{ padding: '4px 8px', borderBottom: '1px solid rgba(255,255,255,0.06)', color: ri === 0 ? '#C4A265' : '#E8E4DC' }}>
                      {inlineFormat(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        );
      }
      continue;
    }

    // Regular paragraph
    elements.push(
      <p key={i} style={{ margin: '4px 0', lineHeight: '1.6' }}>
        {inlineFormat(line)}
      </p>
    );
    i++;
  }

  return elements;
}

/**
 * Inline formatting: **bold**, *italic*, `code`, [link](url)
 */
function inlineFormat(text) {
  if (!text) return text;

  // Split by inline patterns
  const parts = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Bold: **text**
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    // Italic: *text* (not **)
    const italicMatch = remaining.match(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/);
    // Code: `text`
    const codeMatch = remaining.match(/`(.+?)`/);
    // Emoji shortcut — keep as-is

    // Find earliest match
    let earliest = null;
    let earliestIndex = remaining.length;
    let earliestType = null;

    for (const [type, match] of [['bold', boldMatch], ['italic', italicMatch], ['code', codeMatch]]) {
      if (match && match.index < earliestIndex) {
        earliest = match;
        earliestIndex = match.index;
        earliestType = type;
      }
    }

    if (!earliest) {
      parts.push(remaining);
      break;
    }

    // Add text before match
    if (earliestIndex > 0) {
      parts.push(remaining.slice(0, earliestIndex));
    }

    // Add formatted element
    if (earliestType === 'bold') {
      parts.push(<strong key={key++} style={{ fontWeight: 600, color: '#E8E4DC' }}>{earliest[1]}</strong>);
    } else if (earliestType === 'italic') {
      parts.push(<em key={key++} style={{ fontStyle: 'italic', color: '#8899AA' }}>{earliest[1]}</em>);
    } else if (earliestType === 'code') {
      parts.push(
        <code key={key++} style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '13px',
          background: 'rgba(196, 162, 101, 0.1)',
          padding: '2px 6px',
          borderRadius: '4px',
          color: '#C4A265',
        }}>
          {earliest[1]}
        </code>
      );
    }

    remaining = remaining.slice(earliestIndex + earliest[0].length);
  }

  return parts.length === 1 && typeof parts[0] === 'string' ? parts[0] : parts;
}
