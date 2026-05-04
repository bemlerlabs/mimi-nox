"""
◑ MiMi Nox – Chat Export
core/export.py

Formatiert eine Liste von Chat-Nachrichten als sauberes Markdown-Dokument.
"""
from datetime import datetime
from typing import List, Dict, Any

def format_chat_markdown(messages: List[Dict[str, Any]]) -> str:
    """
    Konvertiert eine Liste von Chat-Nachrichten in einen formatierten Markdown-String.
    
    Args:
        messages: Liste von Dictionaries mit 'role' und 'content'
        
    Returns:
        Markdown String
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md_lines = [
        "## Chat Export",
        f"**Datum:** {now}",
        "",
        "---",
        ""
    ]
    
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        # Name mappen
        if role == "user":
            name = "Nutzer"
        elif role == "assistant":
            name = "MiMi"
        elif role == "system":
            name = "System"
        else:
            name = role.capitalize()
            
        md_lines.append(f"**{name}:**")
        md_lines.append(content.strip())
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
        
    return "\n".join(md_lines)
