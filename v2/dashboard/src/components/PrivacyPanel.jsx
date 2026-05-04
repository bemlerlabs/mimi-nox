/**
 * ◑ MiMiNox — Privacy Panel
 * DARPA Tompkins Auflage 2: Technisch prüfbare Privatsphäre beim ersten Start.
 * Shows where data is stored, that no network is active, how to delete data.
 */

export function PrivacyPanel({ onDismiss }) {
  return (
    <div className="privacy-panel" id="privacy-panel">
      <h3>🔒 Deine Privatsphäre — technisch geprüft</h3>

      <div className="privacy-item">
        <span className="check">✓</span>
        <span>
          <strong>Deine Daten liegen auf diesem Gerät.</strong><br />
          Gespeichert in einer lokalen SQLite-Datenbank. Kein Server, keine Cloud.
        </span>
      </div>

      <div className="privacy-item">
        <span className="check">✓</span>
        <span>
          <strong>Keine Netzwerk-Verbindung nötig.</strong><br />
          MiMiNox funktioniert komplett offline. Die KI (Gemma 4) läuft auf deinem Gerät.
        </span>
      </div>

      <div className="privacy-item">
        <span className="check">✓</span>
        <span>
          <strong>Daten löschen: Jederzeit.</strong><br />
          Lösche den Ordner <code style={{ color: '#C4A265' }}>~/.miminox/</code> — dann ist alles weg. Unwiderruflich.
        </span>
      </div>

      <div className="privacy-item">
        <span className="check">✓</span>
        <span>
          <strong>Open Source.</strong><br />
          Du kannst den gesamten Code prüfen. Kein versteckter Tracking-Code.
        </span>
      </div>

      <button className="privacy-dismiss" onClick={onDismiss}>
        Verstanden — los geht's
      </button>
    </div>
  );
}
