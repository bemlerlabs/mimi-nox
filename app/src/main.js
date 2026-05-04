/**
 * ◑ MiMi Nox – Frontend Application
 * app/src/main.js
 *
 * NoxApp: alle Interaktionen, API-Calls, Streaming, UI-State.
 * Kein Framework. Pures JavaScript.
 *
 * API Base: http://127.0.0.1:8765/api
 */

const API = (window.location.protocol === 'file:' || window.location.protocol === 'tauri:') 
            ? 'http://127.0.0.1:8765/api' 
            : '/api';
const STORE_KEY_HISTORY = 'mimi_nox_history';
const DEFAULT_MODEL     = 'gemma4:e4b';

import { ArtifactStore, ArtifactPanel } from './artifact.js';
import { t, applyTranslations, setLanguage, currentLang, needsLanguageSelection } from './i18n.js';

/* ── ◑ NoxApp ────────────────────────────────────────────── */
class NoxApp {
  constructor() {
    this.model         = DEFAULT_MODEL;
    this.history       = [];   // aktuelle Session-Messages [{role,content}]
    this.sessionId     = Date.now();
    this.cmdHistory    = [];   // Tastatur-Verlauf ↑ Taste
    this.cmdIndex      = -1;
    this.isStreaming   = false;
    this.activityLog   = [];
    this.currentMsgId  = 0;
    this.panelCollapsed = false;
    // Audio Recording State
    this.isRecording   = false;
    this._mediaRecorder = null;
    this._audioChunks   = [];
    this._audioContext  = null;
    this._analyser      = null;
    this._waveAnimId    = null;
    this._micStream     = null;

    // TTS & Voice UX
    this._isVoiceConversation = false;
    this._currentAudio = null;
    this._currentSpeakingBtn = null;

    // Artifact System
    this.artifactStore = new ArtifactStore();
    this.artifactPanel = null; // wird in init() erstellt (DOM muss bereit sein)
  }

  // ── Initialisierung ─────────────────────────────────────
   async init() {
    window.noxApp = this;
    this._queryElements();
    this._bindEvents();
    applyTranslations();

    // ── Language Picker (First Launch) ──────────────────────
    if (needsLanguageSelection()) {
      this._showLanguagePicker();
    }

    // SOFORT tab-chat setzen damit Bottombar sichtbar ist
    document.body.classList.add('tab-chat');

    await this.checkHealth();
    this.loadSkillChips();

    this.artifactPanel = new ArtifactPanel(this.artifactStore);

    // Mobile: PWA-Flag + iOS-Keyboard-Fix + Kamera-Button
    if (window.innerWidth <= 768) {
      document.body.classList.add('mobile-pwa-mode');
      this.isMobilePWA = true;
      fetch(`${API}/mobile/ping`, {method: 'POST'}).catch(() => {});

      // iOS visualViewport Fix: Bottombar bleibt über Tastatur
      if (window.visualViewport) {
        const _fixViewport = () => {
          const bar = document.querySelector('.bottombar');
          const nav = document.querySelector('.mobile-bottomnav');
          if (!bar) return;
          const vv = window.visualViewport;
          const keyboardH = window.innerHeight - vv.height;
          if (keyboardH > 100) {
            // Tastatur sichtbar: Bottombar direkt über Tastatur
            bar.style.bottom = `${keyboardH}px`;
            if (nav) nav.style.display = 'none';
          } else {
            // Tastatur weg: zurück auf Mobile-Nav
            bar.style.bottom = '56px';
            if (nav) nav.style.display = 'flex';
          }
        };
        window.visualViewport.addEventListener('resize', _fixViewport);
        window.visualViewport.addEventListener('scroll', _fixViewport);
      }

      // Kamera-Button: direkter Kamera-Zugriff
      const camBtn = document.getElementById('camera-btn');
      const camInput = document.getElementById('camera-input');
      if (camBtn && camInput) {
        camBtn.addEventListener('click', () => camInput.click());
        camInput.addEventListener('change', (e) => {
          const file = e.target.files?.[0];
          if (file) {
            // Gleicher Flow wie der normale attach-btn
            document.getElementById('img-input').files; // reset
            const dt = new DataTransfer();
            dt.items.add(file);
            const imgInput = document.getElementById('img-input');
            imgInput.files = dt.files;
            imgInput.dispatchEvent(new Event('change'));
          }
          camInput.value = '';
        });
      }
    } else {
      this.isMobilePWA = false;
    }

    this.loadMemoryPanel();
    this._initOnboarding();
    this._initVoices();
    setInterval(() => this.checkHealth(), 30_000);
  }

  _queryElements() {
    this.el = {
      chatInput:    document.getElementById('chat-input'),
      sendBtn:      document.getElementById('send-btn'),
      messages:     document.getElementById('messages'),
      welcome:      document.getElementById('welcome-screen'),
      statusDot:    document.getElementById('status-dot'),
      statusText:   document.getElementById('status-text'),
      offlineBanner:document.getElementById('offline-banner'),
      offlineRetry: document.getElementById('offline-retry'),

      apToggle:     document.getElementById('ap-toggle'),
      activityPanel:document.getElementById('activity-panel'),
      apTerminal:   document.getElementById('ap-terminal'),
      memoryCards:  document.getElementById('memory-cards'),
      skillChips:   document.getElementById('skill-chips'),
      autonomToggle:document.getElementById('autonom-toggle'),
      btnMobile:    document.getElementById('btn-mobile-pairing'),
      btnHamburger: document.getElementById('btn-hamburger'),
      btnNewChat:   document.getElementById('btn-new-chat'),
      // Tabs
      tabBtns:      document.querySelectorAll('.tab'),
      tabViews:     document.querySelectorAll('.tab-content'),
      viewHistory:  document.getElementById('view-history'),
      viewMemory:   document.getElementById('view-memory'),
      viewProfile:  document.getElementById('view-profile'),
      // Profile form
      profileForm:  document.getElementById('profile-form'),
      pfName:       document.getElementById('pf-name'),
      pfExpertise:  document.getElementById('pf-expertise'),
      pfLanguage:   document.getElementById('pf-language'),
      pfStyle:      document.getElementById('pf-style'),
      pfVoice:      document.getElementById('pf-voice'),
      saveConfirm:  document.getElementById('save-confirm'),
      // Memory tab
      memSearchInput: document.getElementById('memory-search-input'),
      memSearchBtn:   document.getElementById('memory-search-btn'),
      memFullList:    document.getElementById('memory-full-list'),
      // History tab
      historyList:  document.getElementById('history-list'),
      clearHistory: document.getElementById('clear-history'),
      // Skills tab
      viewSkills:     document.getElementById('view-skills'),
      skillsGrid:     document.getElementById('skills-grid'),
      newSkillBtn:    document.getElementById('new-skill-btn'),
      skillFormWrap:  document.getElementById('skill-form-wrap'),
      skillFormTitle: document.getElementById('skill-form-title'),
      skillForm:      document.getElementById('skill-form'),
      sfName:         document.getElementById('sf-name'),
      sfTrigger:      document.getElementById('sf-trigger'),
      sfDescription:  document.getElementById('sf-description'),
      sfTools:        document.getElementById('sf-tools'),
      sfPrompt:       document.getElementById('sf-prompt'),
      skillSaveBtn:   document.getElementById('skill-save-btn'),
      skillCancelBtn: document.getElementById('skill-cancel-btn'),
      skillSaveConfirm: document.getElementById('skill-save-confirm'),
      // Onboarding
      onboardingOverlay: document.getElementById('onboarding-overlay'),
      obCategories:   document.getElementById('ob-categories'),
      obStartBtn:     document.getElementById('ob-start-btn'),
      // Audio
      micBtn:         document.getElementById('mic-btn'),
      micContainer:   document.getElementById('mic-container'),
      waveformBars:   document.getElementById('waveform-bars'),
      // Layout areas (needed for mobile close-menu handler)
      chatArea:       document.getElementById('chat-area'),
      bottombar:      document.querySelector('.bottombar'),
      // Image Attach (E4B Vision)
      imgInput:       document.getElementById('img-input'),
      attachBtn:      document.getElementById('attach-btn'),
      imgPreviewBar:  document.getElementById('img-preview-bar'),
      imgPreviewName: document.getElementById('img-preview-name'),
      imgPreviewThumb:document.getElementById('img-preview-thumb'),
      imgRemoveBtn:   document.getElementById('img-remove-btn'),
    };
  }

  _bindEvents() {
    // Send
    this.el.sendBtn.addEventListener('click', () => this.submitMessage());

    // Image Attach Button (E4B Vision)
    this._attachedImageB64 = null;
    if (this.el.attachBtn && this.el.imgInput) {
      this.el.attachBtn.addEventListener('click', () => this.el.imgInput.click());
      this.el.imgInput.addEventListener('change', (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
          // Base64 ohne Data-URL-Prefix
          const b64 = ev.target.result.split(',')[1];
          this._attachedImageB64 = b64;
          if (this.el.imgPreviewBar) {
            this.el.imgPreviewBar.style.display = 'flex';
            this.el.imgPreviewName.textContent = file.name;
            this.el.imgPreviewThumb.src = ev.target.result;
          }
        };
        reader.readAsDataURL(file);
      });
      if (this.el.imgRemoveBtn) {
        this.el.imgRemoveBtn.addEventListener('click', () => this._clearAttachedImage());
      }
    }
    
    // New Chat
    if (this.el.btnNewChat) {
      this.el.btnNewChat.addEventListener('click', () => this.clearSession());
    }

    // Mobile Pairing Button
    if (this.el.btnMobile) {
      this.el.btnMobile.addEventListener('click', () => this._showMobileModal());
    }

    // Mobile Menu Toggle
    if (this.el.btnHamburger) {
      this.el.btnHamburger.addEventListener('click', () => {
        this.el.activityPanel.classList.toggle('mobile-open');
      });
    }

    // Auto-close sidebar on mobile when touching chat or bottombar
    const closeMenu = () => {
      if (window.innerWidth <= 768 && this.el.activityPanel.classList.contains('mobile-open')) {
        this.el.activityPanel.classList.remove('mobile-open');
      }
    };
    if (this.el.chatArea) this.el.chatArea.addEventListener('click', closeMenu);
    if (this.el.bottombar) this.el.bottombar.addEventListener('click', closeMenu);

    // Mic Toggle
    if (this.el.micBtn) {
      this.el.micBtn.addEventListener('click', () => this._toggleRecording());
    }

    // Textarea: Enter senden, Shift+Enter Zeilenumbruch, ↑ letzter Befehl, Esc abbruch
    this.el.chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.submitMessage();
      } else if (e.key === 'Escape') {
        if (this.isRecording) {
          this._cancelRecording();
          e.preventDefault();
        } else {
          this.el.chatInput.value = '';
          this._autoResize();
        }
      } else if (e.key === 'ArrowUp' && this.el.chatInput.value === '') {
        e.preventDefault();
        this._navigateHistory(-1);
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        this._navigateHistory(1);
      }
    });

    // Auto-resize textarea
    this.el.chatInput.addEventListener('input', () => {
      this._autoResize();
      // Slash-Autocomplete
      const val = this.el.chatInput.value;
      if (val.startsWith('/')) {
        this._showSlashMenu(val.slice(1));
      } else {
        this._hideSlashMenu();
      }
    });

    // Escape schließt auch Slash-Menü
    this.el.chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this._hideSlashMenu();
    });

    // Klick außerhalb schließt Slash-Menü
    document.addEventListener('click', (e) => {
      if (!e.target.closest('#chat-input') && !e.target.closest('#slash-menu')) {
        this._hideSlashMenu();
      }
    });

    // Fix 16: Drag-and-Drop Images on Chat Area
    if (this.el.chatArea) {
      this.el.chatArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
        this.el.chatArea.style.outline = '2px dashed var(--green)';
        this.el.chatArea.style.outlineOffset = '-4px';
      });
      this.el.chatArea.addEventListener('dragleave', () => {
        this.el.chatArea.style.outline = '';
        this.el.chatArea.style.outlineOffset = '';
      });
      this.el.chatArea.addEventListener('drop', (e) => {
        e.preventDefault();
        this.el.chatArea.style.outline = '';
        this.el.chatArea.style.outlineOffset = '';
        const file = e.dataTransfer.files?.[0];
        if (file && file.type.startsWith('image/')) {
          const reader = new FileReader();
          reader.onload = (ev) => {
            this._attachedImageB64 = ev.target.result.split(',')[1];
            if (this.el.imgPreviewBar) {
              this.el.imgPreviewBar.style.display = 'flex';
              this.el.imgPreviewName.textContent = file.name;
              this.el.imgPreviewThumb.src = ev.target.result;
            }
          };
          reader.readAsDataURL(file);
        }
      });
    }

    // Activity panel toggle (◀)
    this.el.apToggle.addEventListener('click', () => this.toggleActivityPanel());

    // Skill Chips → Input befüllen
    this.el.skillChips.addEventListener('click', (e) => {
      const chip = e.target.closest('.skill-chip');
      if (!chip) return;
      const trigger = chip.dataset.trigger;
      this.el.chatInput.value = trigger + ' ';
      this.el.chatInput.focus();
      this._highlightChip(chip);
    });

    // Willkommens-Karten & interne Links
    document.getElementById('chat-area').addEventListener('click', (e) => {
      // 1) Willkommens-Karten
      const card = e.target.closest('.welcome-card');
      if (card) {
        this.el.chatInput.value = card.dataset.prompt;
        this.submitMessage();
        return;
      }

      // 2) Links abfangen (MD interne/externe Links)
      const link = e.target.closest('a');
      if (link && link.href) {
        // Falls es sich um eine Navigation innerhalb der SPA handelt (404-Vermeidung)
        const url = new URL(link.href, window.location.origin);
        if (url.origin === window.location.origin) {
          e.preventDefault();
          console.log("Interne Navigation abgewiesen:", url.pathname);
          // Man könnte hier optional eine API aufrufen, z.B. /api/open
        } else {
          // Externe verlinkungen im neuen Tab öffnen
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
        }
      }
    });

    // Desktop Tabs (topnav)
    this.el.tabBtns.forEach(btn => {
      btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
    });

    // Mobile Bottom Nav (mbn-tab)
    document.querySelectorAll('.mbn-tab').forEach(btn => {
      btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
    });

    // Autonom Toggle
    if (this.el.autonomToggle) {
      this.el.autonomToggle.addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        try {
          await fetch(`${API}/settings/autonomous`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
          });
          this._addActivity(enabled ? 'warning' : 'info', `🤖 Autonomer Modus ${enabled ? 'AKTIVIERT' : 'DEAKTIVIERT'}`);
          const chatInputWrap = this.el.chatInput.closest('.chat-input-wrap');
          if (chatInputWrap) chatInputWrap.classList.toggle('danger-mode-glow', enabled);
        } catch (err) {
          console.error('API Error:', err);
          e.target.checked = !enabled; // revert
        }
      });
    }

    // Offline Retry
    this.el.offlineRetry.addEventListener('click', () => this.checkHealth());

    // Profil-Formular
    this.el.profileForm.addEventListener('submit', (e) => {
      e.preventDefault();
      this.saveProfile();
    });

    // Memory Suche (Tab)
    this.el.memSearchBtn.addEventListener('click', () => this.searchMemoryFull());
    this.el.memSearchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.searchMemoryFull();
    });

    // Clear history
    this.el.clearHistory?.addEventListener('click', () => {
      if (confirm(t('history.confirmClear'))) {
        localStorage.removeItem(STORE_KEY_HISTORY);
        this._renderHistoryList();
      }
    });

    // Skills Tab
    this.el.newSkillBtn.addEventListener('click', () => this._openSkillForm(null));
    this.el.skillCancelBtn.addEventListener('click', () => this._closeSkillForm());
    this.el.skillForm.addEventListener('submit', (e) => { e.preventDefault(); this._saveSkill(); });

    // Onboarding
    this.el.obCategories.addEventListener('click', (e) => {
      const cat = e.target.closest('.ob-cat');
      if (!cat) return;
      this.el.obCategories.querySelectorAll('.ob-cat').forEach(c => c.classList.remove('selected'));
      cat.classList.add('selected');
      this._selectedCategory = cat.dataset.cat;
      this.el.obStartBtn.disabled = false;
    });
    this.el.obStartBtn.addEventListener('click', () => this._completeOnboarding(this._selectedCategory));
  }



  _autoResize() {
    const ta = this.el.chatInput;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
  }

  // ── 🗣️ Text-To-Speech (Neural Edge-TTS) ────────────────────
  
  _initVoices() {
      if (!this.el.pfVoice) return;
      
      const neuralVoices = [
        { uri: 'de-DE-KillianNeural', name: 'Killian (Lebensecht, Männlich)' },
        { uri: 'de-DE-AmalaNeural', name: 'Amala (Lebensecht, Weiblich)' },
        { uri: 'de-DE-ConradNeural', name: 'Conrad (Lebensecht, Männlich)' },
        { uri: 'en-US-AriaNeural', name: 'Aria (Lebensecht, Weiblich, Englisch)' },
        { uri: 'en-US-GuyNeural', name: 'Guy (Lebensecht, Männlich, Englisch)' }
      ];
      
      const savedUri = localStorage.getItem('mimi_nox_voice') || 'de-DE-KillianNeural';
      this.el.pfVoice.innerHTML = '';
      
      neuralVoices.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.uri;
        opt.textContent = v.name;
        if (v.uri === savedUri) opt.selected = true;
        this.el.pfVoice.appendChild(opt);
      });
  }

  async _speakText(text, btnId = null) {
    // Zweiter Klick = Stoppen
    if (this._currentAudio && !this._currentAudio.paused && this._currentSpeakingBtn === btnId && btnId) {
      this._currentAudio.pause();
      this._resetSpeakBtn(btnId);
      this._currentSpeakingBtn = null;
      return;
    }
    
    if (this._currentAudio) {
      this._currentAudio.pause();
    }
    
    // UI Button auf Loading setzen, falls manuell gedrückt
    if (btnId) {
      const btn = document.getElementById(btnId);
      if (btn) {
        btn.innerHTML = '⏳ Lade...';
        btn.classList.add('btn-speaking');
        this._currentSpeakingBtn = btnId;
      }
    }
    
    let cleanText = text
      .replace(/```[\s\S]*?```/g, ' Codeblock. ')
      .replace(/<[^>]+>/g, '') 
      .replace(/[*_~`#\[\]()]/g, '')
      .trim();

    if (!cleanText) {
      if (btnId) this._resetSpeakBtn(btnId);
      return;
    }

    const savedUri = localStorage.getItem('mimi_nox_voice') || 'de-DE-KillianNeural';

    try {
      const res = await fetch(`${API}/audio/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: cleanText, voice: savedUri })
      });
      if (!res.ok) throw new Error("TTS Fehler");
      
      const data = await res.json();
      this._currentAudio = new Audio(data.audio_url);
      
      if (btnId) {
        const btn = document.getElementById(btnId);
        if (btn) btn.innerHTML = '⏹ Stopp';
        
        this._currentAudio.onended = () => {
          this._resetSpeakBtn(btnId);
          this._currentSpeakingBtn = null;
        };
        this._currentAudio.onerror = this._currentAudio.onended;
      }
      
      await this._currentAudio.play();
      
    } catch (err) {
      console.error(err);
      if (btnId) this._resetSpeakBtn(btnId);
    }
  }

  _resetSpeakBtn(btnId) {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.innerHTML = `🔊 ${t('chat.readAloud')}`;
      btn.classList.remove('btn-speaking');
    }
  }

  /** Bild-Anhang entfernen (nach Send oder manuell) */
  _clearAttachedImage() {
    this._attachedImageB64 = null;
    if (this.el.imgInput) this.el.imgInput.value = '';
    if (this.el.imgPreviewBar) this.el.imgPreviewBar.style.display = 'none';
    if (this.el.imgPreviewThumb) this.el.imgPreviewThumb.src = '';
    if (this.el.imgPreviewName) this.el.imgPreviewName.textContent = '';
  }

  clearSession() {
    this.history = [];
    this.sessionId = Date.now();
    this.el.messages.innerHTML = '';
    this.currentMsgId = 0;
    this._addActivity('done_inline', t('activity.newContext'));
    if (this.el.welcome) this.el.welcome.style.display = 'flex';
    this.switchTab('chat');
    this.el.chatInput.focus();
    this.el.chatInput.value = '';
    this._autoResize();
    this._clearAttachedImage(); // Bild-Anhang beim neuen Chat zurücksetzen
  }

  // ── Health Check ────────────────────────────────────────
  async checkHealth() {
    try {
      const res = await fetch(`${API}/health`, { signal: AbortSignal.timeout(5000) });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();

      if (data.ollama) {
        this._setStatus('connected', data);
        this.el.offlineBanner.classList.add('hidden');
      } else {
        this._setStatus('offline', data);
        this.el.offlineBanner.classList.remove('hidden');
      }

    } catch {
      this._setStatus('offline', null);
      this.el.offlineBanner.classList.remove('hidden');
    }
  }

  _setStatus(state, healthData = null) {
    const dot  = this.el.statusDot;
    const text = this.el.statusText;
    text.removeAttribute('data-i18n');

    // Tier-Badge bestimmen
    const tierBadge = this._buildTierBadge(healthData);

    if (state === 'connected') {
      dot.className  = 'status-dot';
      text.className = 'status-text';
      text.innerHTML = `${t('status.connected')}${tierBadge}`;
    } else {
      dot.className  = 'status-dot offline';
      text.className = 'status-text offline';
      text.innerHTML = `${t('status.offline')}${tierBadge}`;
    }
  }

  /** Baut den Tier-Badge HTML-String für die Statusleiste */
  _buildTierBadge(healthData) {
    if (!healthData) return '';
    const tier = healthData.active_tier;
    if (!tier) return '';

    const configs = {
      power:   { icon: '⚡', label: 'DGX Power', color: '#a855f7' },
      fast:    { icon: '🚀', label: 'Fast',      color: '#22c55e' },
      offline: { icon: '📴', label: 'Offline',   color: '#f59e0b' },
    };
    const cfg = configs[tier] || configs['fast'];
    return ` <span id="tier-badge" style="
      font-size:10px; padding:2px 7px; border-radius:20px;
      background: ${cfg.color}22; color: ${cfg.color};
      border: 1px solid ${cfg.color}44;
      font-weight: 600; letter-spacing: 0.5px;
      vertical-align: middle; margin-left: 6px;
    ">${cfg.icon} ${cfg.label}</span>`;
  }


  // ── Skills ──────────────────────────────────────────────
  async loadSkillChips() {
    try {
      const res  = await fetch(`${API}/skills`);
      const data = await res.json();
      const chips = this.el.skillChips;
      chips.innerHTML = '';

      const icons = {
        '/research': '🔍',
        '/files':    '📁',
        '/write':    '✏️',
        '/review':   '💻',
        '/shell':    '>_',
      };

      (data.skills || []).forEach(skill => {
        const btn = document.createElement('button');
        btn.className = 'skill-chip';
        btn.dataset.trigger = skill.trigger;
        btn.title = skill.description;
        btn.textContent = (icons[skill.trigger] || '⚡') + ' ' + skill.trigger;
        btn.setAttribute('role', 'listitem');
        chips.appendChild(btn);
      });
    } catch {
      // Behalte die statischen HTML-Chips als Fallback
    }
  }

  _highlightChip(activeChip) {
    this.el.skillChips.querySelectorAll('.skill-chip')
      .forEach(c => c.classList.remove('active'));
    activeChip.classList.add('active');
    setTimeout(() => activeChip.classList.remove('active'), 1500);
  }

  // ── Slash-Command Autocomplete ───────────────────────────
  async _showSlashMenu(filter) {
    // Menü-Element erstellen oder wiederverwenden (früh, für Loading-State)
    let menu = document.getElementById('slash-menu');
    if (!menu) {
      menu = document.createElement('div');
      menu.id = 'slash-menu';
      menu.style.cssText = `
        position: absolute; bottom: 100%; left: 0; right: 0;
        background: rgba(4, 12, 6, 0.97);
        border: 1px solid rgba(34, 197, 94, 0.25);
        border-radius: 12px 12px 0 0;
        padding: 6px 0;
        z-index: 200;
        backdrop-filter: blur(16px);
        box-shadow: 0 -8px 32px rgba(0, 0, 0, 0.5);
        max-height: 240px;
        overflow-y: auto;
      `;
      const inputWrap = document.getElementById('input-wrap');
      if (inputWrap) {
        inputWrap.style.position = 'relative';
        inputWrap.appendChild(menu);
      }
    }

    // Skills einmalig laden + cachen
    if (!this._slashSkillCache) {
      // Sofortiger Loading-State — kein leeres Schweigen
      menu.innerHTML = `<div style="padding:10px 14px; color:var(--text-dim);
        font-size:12px; display:flex; align-items:center; gap:8px;">
        <span style="display:inline-block; animation:spin 1s linear infinite;">◑</span>
        Lade Skills…
      </div>`;
      menu.style.display = 'block';

      try {
        const res = await fetch(`${API}/skills`);
        const data = await res.json();
        this._slashSkillCache = (data.skills || []).map(s => ({
          trigger: s.trigger,
          description: s.description || '',
          icon: { '/research': '🔍', '/write': '✏️', '/review': '💻',
                  '/files': '📁', '/shell': '>_', '/scan': '⚡',
                  '/swarm': '🐝', '/learn': '🧠' }[s.trigger] || '⚡'
        }));
      } catch {
        menu.style.display = 'none';
        return;
      }
    }

    const matches = this._slashSkillCache.filter(s =>
      s.trigger.slice(1).startsWith(filter.toLowerCase())
    );

    if (matches.length === 0) { this._hideSlashMenu(); return; }

    menu.innerHTML = matches.map((s, i) => `
      <div class="slash-item" data-trigger="${s.trigger}" data-idx="${i}" style="
        display: flex; align-items: center; gap: 10px;
        padding: 8px 14px; cursor: pointer;
        transition: background 0.15s;
        font-size: 13px;
      " onmouseover="this.style.background='rgba(34,197,94,0.08)'"
         onmouseout="this.style.background=''"
      >
        <span style="font-size:15px; min-width:20px;">${s.icon}</span>
        <span style="color:var(--green); font-family:var(--font-mono); font-weight:600;">${s.trigger}</span>
        <span style="color:var(--text-dim); font-size:12px; margin-left:4px;">${s.description}</span>
      </div>
    `).join('');

    // Click-Handler
    menu.querySelectorAll('.slash-item').forEach(item => {
      item.addEventListener('click', () => {
        this.el.chatInput.value = item.dataset.trigger + ' ';
        this.el.chatInput.focus();
        this._hideSlashMenu();
        this._autoResize();
      });
    });

    menu.style.display = 'block';
  }

  _hideSlashMenu() {
    const menu = document.getElementById('slash-menu');
    if (menu) menu.style.display = 'none';
  }

  // ── Nachricht senden ────────────────────────────────────
  submitMessage(isVoiceMode = false) {
    if (this.isStreaming) {
      if (this._abortController) this._abortController.abort();
      return;
    }
    
    const text = this.el.chatInput.value.trim();
    if (!text) return;

    if (text === '/mobile') {
      this.el.chatInput.value = '';
      this._autoResize();
      this._showMobileModal();
      return;
    }

    if (text.startsWith('/schedule')) {
      this.el.chatInput.value = '';
      this._autoResize();
      this._handleScheduleCommand(text);
      return;
    }

    // Bei manueller Tastatur-Eingabe: Stummschaltung der Auto-Voice
    if (!isVoiceMode) {
      this._isVoiceConversation = false;
      if (this._currentAudio) this._currentAudio.pause();
      if (this._currentSpeakingBtn) this._resetSpeakBtn(this._currentSpeakingBtn);
    } else {
      this._isVoiceConversation = true;
    }

    // Verlauf für ↑ Taste
    this.cmdHistory.unshift(text);
    if (this.cmdHistory.length > 50) this.cmdHistory.pop();
    this.cmdIndex = -1;

    this.el.chatInput.value = '';
    this._autoResize();
    this._hideWelcome();
    this._streamStart = Date.now();

    this.renderUserBubble(text, this._attachedImageB64); // Bild in Bubble zeigen
    const imageToSend = this._attachedImageB64;          // Referenz sichern
    this._clearAttachedImage();                           // UI-Preview entfernen
    this._startStreaming(text, imageToSend);              // Gesichertes Bild senden
  }

  async _showMobileModal() {
    const modal = document.getElementById('mobile-qr-overlay');
    const img = document.getElementById('mobile-qr-img');
    const loader = document.getElementById('mobile-qr-loader');
    
    // Show modal immediately with loading state
    img.classList.add('hidden');
    img.style.display = 'none';
    loader.classList.remove('hidden');
    loader.style.display = 'flex';
    modal.classList.remove('hidden');

    try {
      const res = await fetch(`${API}/mobile/qr`);
      const data = await res.json();
      
      img.src = `data:image/png;base64,${data.qr_base64}`;
      
      // Hide loader, show img
      loader.classList.add('hidden');
      loader.style.display = 'none';
      img.classList.remove('hidden');
      img.style.display = 'block';

      // Start ping loop for connection
      if (this.mobilePollInterval) clearInterval(this.mobilePollInterval);
      this.mobilePollInterval = setInterval(async () => {
        try {
          const statusRes = await fetch(`${API}/mobile/status`);
          const statusData = await statusRes.json();
          if (statusData.connected) {
            clearInterval(this.mobilePollInterval);
            modal.classList.add('hidden');
            const bubble = this.renderAIBubble(Date.now());
            bubble.innerHTML = '<p style="color:var(--green-light)">📱 Smartphone erfolgreich via verschlüsseltem PWA-Tunnel verbunden!</p>';
            this.history.push({role: "assistant", content: "Smartphone erfolgreich via verschlüsseltem PWA-Tunnel verbunden!"});
          }
        } catch (e) {}
      }, 1500);

    } catch (err) {
      alert("Fehler beim Laden des QR Codes. Server offline?");
      modal.classList.add('hidden');
    }
  }

  // ── /schedule Command ───────────────────────────────────
  async _handleScheduleCommand(text) {
    // /schedule list
    if (text.trim() === '/schedule list') {
      try {
        const res = await fetch(`${API}/schedule`);
        const data = await res.json();
        const bubble = this.renderAIBubble(Date.now());
        if (!data.jobs.length) {
          bubble.innerHTML = '<p>📭 Keine geplanten Jobs vorhanden. Erstelle einen mit:<br><code>/schedule "Aufgabe" @ cron</code></p>';
          return;
        }
        let md = '## 📅 Geplante Hintergrund-Jobs\n\n';
        data.jobs.forEach(j => {
          md += `**${j.name}**\n- ID: \`${j.id}\`\n- Nächster Lauf: ${j.next_run || '–'}\n\n`;
        });
        bubble.innerHTML = marked.parse ? marked.parse(md) : md;
      } catch(e) {
        this._addActivity('error', e.message);
      }
      return;
    }

    // /schedule delete <id>
    const delMatch = text.match(/^\/schedule delete ([a-z0-9_-]+)$/i);
    if (delMatch) {
      try {
        const res = await fetch(`${API}/schedule/${delMatch[1]}`, {method: 'DELETE'});
        const data = await res.json();
        const bubble = this.renderAIBubble(Date.now());
        bubble.innerHTML = `<p>🗑️ Job <code>${delMatch[1]}</code> gelöscht.</p>`;
      } catch(e) { this._addActivity('error', e.message); }
      return;
    }

    // /schedule results
    if (text.trim() === '/schedule results') {
      try {
        const res = await fetch(`${API}/schedule/results`);
        const data = await res.json();
        const bubble = this.renderAIBubble(Date.now());
        if (!data.results.length) {
          bubble.innerHTML = '<p>📭 Noch keine Job-Ergebnisse vorhanden.</p>';
          return;
        }
        let md = '## 📊 Letzte Job-Ergebnisse\n\n';
        data.results.slice(0, 5).forEach(r => {
          md += `**${r.task}**\n- Ausgeführt: ${r.executed_at}\n- ${r.error ? '❌ Fehler: ' + r.error : '✅ Ergebnis: ' + (r.result || '').slice(0, 200)}\n\n`;
        });
        bubble.innerHTML = marked.parse ? marked.parse(md) : md;
      } catch(e) { this._addActivity('error', e.message); }
      return;
    }

    // /schedule "Aufgabe" @ cron
    const createMatch = text.match(/^\/schedule\s+"([^"]+)"\s+@\s+(.+)$/);
    if (createMatch) {
      try {
        const res = await fetch(`${API}/schedule`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({task: createMatch[1], cron: createMatch[2].trim()})
        });
        const data = await res.json();
        const bubble = this.renderAIBubble(Date.now());
        bubble.innerHTML = `<p>⏰ <strong>Job geplant!</strong><br>ID: <code>${data.job_id}</code><br>${data.message}</p>`;
      } catch(e) { this._addActivity('error', e.message); }
      return;
    }

    // Show help
    const bubble = this.renderAIBubble(Date.now());
    bubble.innerHTML = `<div style="font-family:monospace; line-height:1.8">
      <strong>📅 /schedule – Hintergrund-Jobs</strong><br><br>
      <code>/schedule "Aufgabe" @ 0 8 * * *</code> — täglich 08:00<br>
      <code>/schedule list</code> — alle Jobs anzeigen<br>
      <code>/schedule results</code> — letzte Ergebnisse<br>
      <code>/schedule delete &lt;id&gt;</code> — Job löschen<br><br>
      <em>Cron-Format: Minute Stunde Tag Monat Wochentag</em>
    </div>`;
  }

  async _startStreaming(text, imageB64 = null) {
    this.isStreaming = true;
    
    this.el.sendBtn.textContent = '⏹';
    this.el.sendBtn.classList.add('btn-danger');
    this.el.sendBtn.disabled = false; // "Stop" soll klickbar sein
    this.el.chatInput.disabled = true;

    this.currentMsgId++;
    const msgId = this.currentMsgId;
    const wrap   = this._createAIBubbleWrap(msgId);
    let   bubble = wrap.querySelector('.bubble-ai');
    let   thinkingBubble = wrap.querySelector('.thinking-panel');
    let   full   = '';
    let   thinkStartTime = 0;

    // Activity: Anfrage gestartet
    this._addActivity('cmd', `react_loop("${text.slice(0,40)}${text.length>40?'…':''}")`);
    this._addActivity('progress', t('chat.generating'));

    try {
      this._abortController = new AbortController();
      // Watchdog für langes Warten (Fallbacks)
      const timeoutId = setTimeout(() => {
        if (this._abortController) this._abortController.abort(new Error("Timeout"));
      }, 120_000);

      const res = await fetch(`${API}/chat/stream`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ 
          message: text, 
          model: this.model, 
          history: this.history,
          autonomous: this.isMobilePWA === true,
          images: imageB64 ? [imageB64] : [],
        }),
        signal:  this._abortController.signal,
      });
      clearTimeout(timeoutId);

      if (!res.ok) {
        const err = await res.json().catch(() => ({detail: 'HTTP ' + res.status}));
        throw new Error(err.detail || 'HTTP ' + res.status);
      }

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let   buffer  = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // unfertige Zeile behalten

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          let evt;
          try { evt = JSON.parse(raw); } catch { continue; }

          switch (evt.type) {

            case 'thinking_start':
              if (thinkingBubble) {
                thinkingBubble.classList.remove('hidden');
                thinkingBubble.classList.add('thinking-open');
                const tc = thinkingBubble.querySelector('.thinking-content');
                if (tc) tc.textContent = '';
                thinkStartTime = Date.now();
              }
              this._scrollToBottom();
              break;

            case 'chunk':
              // Token sofort anhängen via Markdown-Streaming
              full += evt.data;
              this._appendChunk(bubble, evt.data);
              // Thinking-Bubble bleibt geöffnet während Antwort kommt!
              // (User kann Gedanken noch lesen)
              this._scrollToBottom();
              break;

            case 'thinking':
              if (thinkingBubble) {
                thinkingBubble.classList.remove('hidden');
                thinkingBubble.classList.add('thinking-open');
                const tc2 = thinkingBubble.querySelector('.thinking-content');
                if (tc2) {
                  tc2.textContent += evt.data;
                  tc2.scrollTop = tc2.scrollHeight;
                }
              }
              break;

            case 'activity':
              // Tool-Call sichtbar im Terminal
              this._addActivity(
                evt.status === 'done' ? 'done_inline' : 'cmd',
                evt.cmd
              );
              break;

            case 'reflect':
              if (evt.status === 'running') {
                this._addActivity('cmd', 'reflect: Quality check…');
              } else if (evt.needs_revision === false) {
                this._addActivity('done', '✓ Quality OK');
              }
              break;

            case 'revision':
              // Falls sie schon losgeredet hat: Stille!
              if (this._currentAudio) this._currentAudio.pause();

              // Bubble zurücksetzen — überarbeitete Antwort kommt gleich
              this._addActivity('cmd', `🔄 Revision: ${(evt.reason || '').slice(0, 60)}`);
              full   = '';
              bubble.textContent = '';
              bubble.classList.add('streaming-cursor');
              break;

            case 'error':
              bubble.classList.remove('streaming-cursor');
              bubble.textContent = `⚠ ${evt.msg}`;
              this._addActivity('error', evt.msg);
              this._setStatus('offline');
              break;

            case 'done':
              // Streaming fertig → Markdown rendern
              bubble.classList.remove('streaming-cursor');
              if (window.marked && full) {
                try {
                  const rawHtml = window.marked.parse(full, { breaks: true, gfm: true });
                  bubble.innerHTML = window.DOMPurify
                    ? window.DOMPurify.sanitize(rawHtml)
                    : rawHtml;
                } catch { /* markdown parse fehler ignorieren */ }
              }
              
              // Walkie-Talkie: Automatisch vorlesen, wenn per Voice gefragt wurde
              if (this._isVoiceConversation && full) {
                this._speakText(full, `speak-${msgId}`);
              }
              break;

            case 'skill_created':
              // Neuer Skill via /learn → Chip sofort mit Animation einfügen
              if (evt.skill) {
                const chip = document.createElement('button');
                chip.className = 'skill-chip skill-chip-new';
                chip.dataset.trigger = evt.skill.trigger;
                chip.title = evt.skill.description || '';
                chip.textContent = '✨ ' + evt.skill.trigger;
                chip.setAttribute('role', 'listitem');
                this.el.skillChips.appendChild(chip);
                this._addActivity('done_inline', `✨ Neuer Skill: ${evt.skill.trigger}`);
                // Nach Animation: Chips sauber neu laden
                setTimeout(() => this.loadSkillChips(), 2000);
              }
              break;

            case 'file_result': {
              // Chart/PDF/SVG Tool-Output → direkt in Bubble anzeigen
              const fr = evt;
              const fileName = fr.path.split('/').pop();

              if (fr.file_type === 'chart') {
                // Chart als Bild einbetten
                const imgUrl = `/charts/${fileName}`;
                const imgWrap = document.createElement('div');
                imgWrap.className = 'file-result-chart';
                imgWrap.innerHTML = `
                  <img src="${imgUrl}" alt="${fr.label}" class="chart-img"
                       style="max-width:100%; border-radius:12px; margin:12px 0; display:block;"
                       onerror="this.style.display='none'" />
                  <a href="${imgUrl}" download="${fileName}" class="file-result-dl">
                    ⬇ Chart herunterladen
                  </a>
                `;
                bubble.appendChild(imgWrap);
                this._addActivity('done_inline', fr.label);

              } else if (fr.file_type === 'pdf') {
                // PDF als Download-Button
                const dlBtn = document.createElement('a');
                dlBtn.href = `/api/download?path=${encodeURIComponent(fr.path)}`;
                dlBtn.download = fileName;
                dlBtn.className = 'file-result-btn';
                dlBtn.innerHTML = `<span>📄</span><span>${fileName}</span><span class="file-result-dl">⬇ PDF öffnen</span>`;
                dlBtn.title = 'PDF in Downloads gespeichert: ' + fr.path;
                // Fallback: Pfad im Activity Panel zeigen
                bubble.appendChild(dlBtn);
                this._addActivity('done_inline', `${fr.label} → ${fr.path}`);

              } else if (fr.file_type === 'svg') {
                // SVG als Inline-Preview + Download
                const svgWrap = document.createElement('div');
                svgWrap.className = 'file-result-chart';
                svgWrap.innerHTML = `
                  <a href="/api/download?path=${encodeURIComponent(fr.path)}" download="${fileName}"
                     class="file-result-btn">
                    <span>🎨</span><span>${fileName}</span><span class="file-result-dl">⬇ SVG speichern</span>
                  </a>
                `;
                bubble.appendChild(svgWrap);
                this._addActivity('done_inline', `${fr.label} → ${fr.path}`);
              }
              break;
            }

            case 'replace_text':
              // Bubble-Text durch bereinigten Text ersetzen (Code durch Placeholder)
              full = evt.text;
              bubble.textContent = evt.text;
              break;

            case 'artifact':
              // Artifact empfangen → Panel öffnen + Artifact-Link in Chat einfügen
              if (evt.artifact && this.artifactPanel) {
                const art = evt.artifact;
                this._addActivity('done_inline', `📄 Artifact: ${art.filename}`);

                // Artifact-Link-Button im Chat erstellen
                const artLink = document.createElement('button');
                artLink.className = 'artifact-link';
                artLink.setAttribute('aria-label', `Artifact öffnen: ${art.title}`);
                artLink.innerHTML = `
                  <span class="artifact-link__icon">📄</span>
                  <span class="artifact-link__name">${art.filename}</span>
                  <span class="artifact-link__meta">${art.language} · ${art.content.split('\n').length} Zeilen</span>
                  <span style="margin-left:auto; color:#22c55e; font-size:11px">Öffnen →</span>
                `;
                artLink.addEventListener('click', () => {
                  this.artifactPanel.open(art);
                });
                bubble.appendChild(artLink);

                // Panel direkt öffnen
                this.artifactPanel.open(art);
              }
              break;

              
            // ── Swarm V2 Events ──────────────────────────────────────
            case 'swarm_status':
              this._addActivity('cmd', evt.message || `🐝 Swarm: ${evt.phase}`);
              // Swarm-Dashboard in Bubble einfügen (nur einmal)
              if (!wrap.querySelector('.swarm-dashboard')) {
                const dashboard = document.createElement('div');
                dashboard.className = 'swarm-dashboard';
                dashboard.innerHTML = `<div class="swarm-header">🐝 Swarm Pipeline <span class="swarm-phase">${evt.phase}</span></div><div class="swarm-agents"></div>`;
                wrap.querySelector('.msg-content').insertBefore(dashboard, bubble);
              } else {
                const phaseEl = wrap.querySelector('.swarm-phase');
                if (phaseEl) phaseEl.textContent = evt.phase;
              }
              this._scrollToBottom();
              break;

            case 'agent_spawned':
              this._addActivity('cmd', `⚡ Agent ${evt.agent_id} (${evt.role}): ${(evt.subtask || '').slice(0, 50)}`);
              {
                const agentsContainer = wrap.querySelector('.swarm-agents');
                if (agentsContainer) {
                  const card = document.createElement('div');
                  card.className = 'swarm-agent-card spawned';
                  card.id = `agent-${evt.agent_id}`;
                  card.innerHTML = `
                    <div class="agent-status-dot"></div>
                    <div class="agent-info">
                      <span class="agent-role">${evt.role}</span>
                      <span class="agent-task">${(evt.subtask || '').slice(0, 60)}</span>
                      <span class="agent-detail">Spawned…</span>
                    </div>
                  `;
                  agentsContainer.appendChild(card);
                }
              }
              this._scrollToBottom();
              break;

            case 'agent_progress':
              {
                const agentCard = document.getElementById(`agent-${evt.agent_id}`);
                if (agentCard) {
                  agentCard.className = `swarm-agent-card ${evt.status}`;
                  const detail = agentCard.querySelector('.agent-detail');
                  if (detail) detail.textContent = evt.detail || evt.status;
                }
                if (evt.status !== 'running') {
                  this._addActivity(
                    evt.status === 'done' ? 'done_inline' : (evt.status === 'error' ? 'error' : 'cmd'),
                    `Agent ${evt.agent_id}: ${evt.status} ${evt.detail ? '— ' + evt.detail.slice(0, 50) : ''}`
                  );
                }
              }
              break;

            case 'agent_terminated':
              {
                const termCard = document.getElementById(`agent-${evt.agent_id}`);
                if (termCard) {
                  termCard.className = 'swarm-agent-card terminated';
                  const detail = termCard.querySelector('.agent-detail');
                  if (detail) detail.textContent = '✓ Terminiert';
                }
                this._addActivity('done_inline', `🏁 Agent ${evt.agent_id} terminiert`);
              }
              break;

            case 'swarm_done':
              {
                const phaseElDone = wrap.querySelector('.swarm-phase');
                if (phaseElDone) phaseElDone.textContent = '✅ done';
                const header = wrap.querySelector('.swarm-header');
                if (header) header.classList.add('swarm-complete');
                this._addActivity('done', `🐝 Swarm abgeschlossen: ${evt.agent_count} Agenten`);
              }
              this._scrollToBottom();
              break;

            case 'vision_learning':
              this._playTone(350, 0.2, 'square');
              this._addActivity('warning', `🧠 HITL: Warte auf User-Klick für "${evt.target}"...`);
              
              const wrapLearn = document.createElement('div');
              wrapLearn.className = 'msg nox';
              wrapLearn.innerHTML = `
                <div class="msg-content" style="border: 1px solid var(--orange); background: rgba(249, 115, 22, 0.1); width: 100%; max-width: 400px; padding: 12px; border-radius: 4px;">
                  <strong style="color: var(--orange);">🧠 Aktives Lernen (HITL)</strong>
                  <p style="margin: 8px 0; font-size: 13px; color: var(--text-dim);">Ich bin mir nicht zu 100% sicher, wo <strong>"${evt.target}"</strong> ist.</p>
                  <p style="margin: 8px 0; font-size: 13px; font-weight: bold; color: white;">👉 Bitte klicke exakt jetzt einmal selbst auf das Element.</p>
                  <div style="font-size: 11px; color: var(--text-dim); margin-top: 8px; font-style: italic;">Nach deinem manuellen Klick speichere ich das Element für die nächste Ausführung!</div>
                </div>
              `;
              this.el.messages.appendChild(wrapLearn);
              this._scrollToBottom();
              break;

            case 'vision_learned_success':
              const learningBox = Array.from(document.querySelectorAll('.vision-learning-box')).pop();
              if (learningBox) {
                this._playTone(500, 0.1, 'sine');
                learningBox.innerHTML = `
                  <div class="msg-content" style="border: 1px solid var(--green); background: rgba(34, 197, 94, 0.1); width: 100%; max-width: 400px; padding: 12px; border-radius: 4px;">
                    <strong style="color: var(--green);">✅ Element erfolgreich gemerkt!</strong>
                    <p style="margin: 8px 0; font-size: 13px; color: var(--text-dim);">Ich habe das Aussehen von <strong>"${evt.target}"</strong> gelernt. Beim nächsten Mal finde ich es blind!</p>
                  </div>
                `;
              }
              break;

            case 'sandbox_confirm':
              // Sandboxing UI Event
              this._playTone(250, 0.2, 'sawtooth');
              this._addActivity('warning', `🚧 Erlaubnis benötigt für: ${evt.tool}`);
              
              let niceMessage = `MiMi fragt nach Erlaubnis, deinen Computer zu steuern:`;
              let niceCode = `${evt.tool}(${JSON.stringify(evt.args)})`;
              
              if (evt.tool === 'vision_click' && evt.args.target_description) {
                niceMessage = `MiMi möchte gerne die Computer-Maus bewegen und physisch auf folgenden Bereich klicken:`;
                niceCode = `👉  Element "${evt.args.target_description}" anklicken`;
              } else if (evt.tool === 'vision_type' && evt.args.text) {
                niceMessage = `MiMi möchte deine Tastatur bedienen und folgenden Text tippen:`;
                niceCode = `⌨️  Text "${evt.args.text}" tippen ${evt.args.press_enter ? '(+ Enter)' : ''}`;
              }
              
              const wrapConf = document.createElement('div');
              wrapConf.className = 'msg nox sandbox-confirm-box';
              wrapConf.innerHTML = `
                <div class="msg-content" style="border: 1px solid #f97316; background: rgba(249, 115, 22, 0.1); width: 100%; max-width: 400px; padding: 12px;">
                  <strong style="color: #f97316;">🛡️ Sandbox Bestätigung</strong>
                  <p style="margin: 8px 0; font-size: 13px; color: var(--text-dim);">${niceMessage}</p>
                  <div style="background: rgba(0,0,0,0.3); padding: 8px; border-radius: 4px; font-size: 12px; font-family: monospace; white-space: pre-wrap; word-break: break-all; border-left: 3px solid var(--orange);">${niceCode}</div>
                  <div style="display: flex; gap: 8px; margin-top: 12px;">
                    <button class="btn-allow" style="background: var(--green); color: black; padding: 6px 12px; border-radius: 4px; border: none; cursor: pointer; font-weight: bold; flex: 1;">✅ Erlauben</button>
                    <button class="btn-deny" style="background: var(--red); color: white; padding: 6px 12px; border-radius: 4px; border: none; cursor: pointer; font-weight: bold; flex: 1;">❌ Ablehnen</button>
                  </div>
                </div>
              `;
              
              const btnAllow = wrapConf.querySelector('.btn-allow');
              const btnDeny = wrapConf.querySelector('.btn-deny');
              
              const resolveSandbox = async (approved) => {
                btnAllow.disabled = true;
                btnDeny.disabled = true;
                wrapConf.style.opacity = '0.5';
                
                await fetch(`${API}/sandbox/approve`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ token: evt.token, approved })
                });
                
                this._addActivity(approved ? 'done' : 'error', approved ? '✅ GUI Freigabe erteilt' : '❌ GUI Aktion blockiert');
              };
              
              btnAllow.onclick = () => resolveSandbox(true);
              btnDeny.onclick  = () => resolveSandbox(false);
              
              // Remove old loading UI (Cursor / Bubble) temp
              if (thinkingBubble && !thinkingBubble.classList.contains('thinking-done')) {
                // sandbox_confirm bricht Thinking nicht ab — Panel bleibt offen
              }
              
              this.el.messages.appendChild(wrapConf);
              this._scrollToBottom();
              break;
          }
        }
      }

      // Finaler synchroner Markdown-Render (löscht Debounce-Timer)
      this._finalRender(bubble);
      bubble.classList.remove('streaming-cursor');

      // Thinking Panel: auf "Gedacht für Xs" umschalten
      if (thinkingBubble && !thinkingBubble.classList.contains('hidden')) {
        const secs = thinkStartTime
          ? ((Date.now() - thinkStartTime) / 1000).toFixed(0)
          : null;
        const lbl = thinkingBubble.querySelector('.thinking-label');
        const spinner = thinkingBubble.querySelector('.thinking-spinner');
        if (lbl) lbl.textContent = secs ? `Thought for ${secs}s` : 'Thought';
        if (spinner) spinner.style.display = 'none';
        // Zugeklappt nach kurzer Pause (User kann noch lesen)
        setTimeout(() => {
          thinkingBubble.classList.remove('thinking-open');
          thinkingBubble.classList.add('thinking-done');
        }, 1500);
      }

      // Aktionen anzeigen
      this._showBubbleActions(msgId, text, full);
      this._addActivity('done', `✓ Done in ${((Date.now() - this._streamStart) / 1000).toFixed(1)}s`);

      // Memory kurz danach aktualisieren
      setTimeout(() => this.loadMemoryPanel(), 1500);

    } catch (err) {
      bubble.classList.remove('streaming-cursor');
      if (err.name === 'AbortError') {
        this._addActivity('warning', '🛑 Generation durch Benutzer abgebrochen');
        this._appendChunk(bubble, '\n\n*[Verarbeitung gestoppt]*');
        if (!full) full = '[Gestoppt]';
      } else {
        if (!full) bubble.textContent = `⚠ ${err.message}`;
        this._addActivity('error', `Fehler: ${err.message}`);
        this._setStatus('offline');
      }
    } finally {
      this.history.push({ role: 'user',      content: text });
      this.history.push({ role: 'assistant', content: full });
      this._saveToHistory(text, full);

      this.isStreaming = false;
      this.el.sendBtn.textContent = '➤';
      this.el.sendBtn.classList.remove('btn-danger');
      this.el.sendBtn.disabled  = false;
      this.el.chatInput.disabled = false;
      this.el.chatInput.focus();
      this._scrollToBottom();
    }
  }

  // ── Render Funktionen ───────────────────────────────────
  _hideWelcome() {
    if (this.el.welcome) this.el.welcome.style.display = 'none';
  }

  _showLanguagePicker() {
    const overlay = document.getElementById('lang-overlay');
    if (!overlay) return;
    overlay.style.display = 'flex';

    const grid = document.getElementById('lang-grid');
    if (!grid) return;

    const LANG_NAMES = {
      de: 'Deutsch', en: 'English', es: 'Español',
      fr: 'Français', ja: '日本語', zh: '中文',
    };

    grid.addEventListener('click', (e) => {
      const btn = e.target.closest('.lang-btn');
      if (!btn) return;

      const lang = btn.dataset.lang;
      setLanguage(lang);
      applyTranslations();

      // Sync language to backend profile so MiMi responds in the right language
      fetch(`${API}/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preferred_language: LANG_NAMES[lang] || lang }),
      }).catch(() => {}); // fire-and-forget

      // Smooth fade-out
      overlay.classList.add('fade-out');
      overlay.addEventListener('animationend', () => {
        overlay.style.display = 'none';
        overlay.remove();
      }, { once: true });
    });
  }

  renderUserBubble(text, imageB64 = null) {
    const el = document.createElement('div');
    el.className = 'bubble-user';
    // Bild-Thumbnail in User-Bubble anzeigen
    if (imageB64) {
      const img = document.createElement('img');
      img.src = `data:image/jpeg;base64,${imageB64}`;
      img.style.cssText = 'max-width:220px;max-height:220px;object-fit:cover;border-radius:8px;display:block;margin-bottom:8px;border:1px solid rgba(34,197,94,0.3)';
      img.alt = 'Hochgeladenes Bild';
      el.appendChild(img);
    }
    const span = document.createElement('span');
    span.textContent = text;
    el.appendChild(span);
    this.el.messages.appendChild(el);
    this._scrollToBottom();
    return el;
  }

  /** Erstellt leeren AI-Wrap + Thinking-Panel (Claude-Style) + Antwort-Bubble */
  _createAIBubbleWrap(id) {
    const wrap = document.createElement('div');
    wrap.className    = 'bubble-ai-wrap';
    wrap.dataset.msgId = id;

    // ── Thinking Panel (Claude/Grok Style) ──────────────────
    const thinkDiv = document.createElement('div');
    thinkDiv.className = 'thinking-panel hidden';
    thinkDiv.innerHTML = `
      <button class="thinking-toggle" aria-expanded="true">
        <span class="thinking-spinner"></span>
        <span class="thinking-label">Nox is thinking…</span>
        <span class="thinking-chevron">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M3 5l4 4 4-4" stroke="currentColor" stroke-width="1.5"
              stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
      </button>
      <div class="thinking-body">
        <div class="thinking-content"></div>
      </div>
    `;

    // Toggle expand/collapse
    thinkDiv.querySelector('.thinking-toggle').addEventListener('click', () => {
      const isOpen = thinkDiv.classList.toggle('thinking-open');
      thinkDiv.querySelector('.thinking-toggle').setAttribute('aria-expanded', isOpen);
    });

    const bubble = document.createElement('div');
    bubble.className = 'bubble-ai streaming-cursor';
    bubble.id = `msg-${id}`;

    wrap.appendChild(thinkDiv);
    wrap.appendChild(bubble);
    this.el.messages.appendChild(wrap);
    this._scrollToBottom();
    return wrap;
  }

  /** Alias für Tests / backward compat */
  renderAIBubble(id) {
    return this._createAIBubbleWrap(id).querySelector('.bubble-ai');
  }

  _appendChunk(bubble, chunk) {
    // Rohtext akkumulieren
    bubble._rawText = (bubble._rawText || '') + chunk;

    // Debounced Markdown-Render (80ms) — verhindert Layout-Thrashing
    clearTimeout(bubble._renderTimer);
    bubble._renderTimer = setTimeout(() => {
      if (window.marked && window.DOMPurify) {
        bubble.innerHTML = DOMPurify.sanitize(
          marked.parse(bubble._rawText),
          { USE_PROFILES: { html: true } }
        );
      } else {
        // Fallback falls libs noch nicht geladen
        bubble.textContent = bubble._rawText;
      }
    }, 80);

    this._scrollToBottom();
  }

  /** Finaler synchroner Render nach Stream-Ende */
  _finalRender(bubble) {
    clearTimeout(bubble._renderTimer);
    if (!bubble._rawText) return;
    if (window.marked && window.DOMPurify) {
      bubble.innerHTML = DOMPurify.sanitize(
        marked.parse(bubble._rawText),
        { USE_PROFILES: { html: true } }
      );
    } else {
      bubble.textContent = bubble._rawText;
    }
  }

  _showBubbleActions(id, prompt, response) {
    const wrap = document.querySelector(`.bubble-ai-wrap[data-msg-id="${id}"]`);
    if (!wrap) return;

    const actions = document.createElement('div');
    actions.className = 'bubble-actions';
    actions.innerHTML = `
      <button class="bubble-action-btn" id="speak-${id}" aria-label="${t('chat.readAloud')}">🔊 ${t('chat.readAloud')}</button>
      <span class="action-sep">·</span>
      <button class="bubble-action-btn" id="copy-${id}" aria-label="${t('chat.copy')}">📋 ${t('chat.copy')}</button>
      <span class="action-sep">·</span>
      <button class="bubble-action-btn" id="up-${id}"   aria-label="Hilfreiche Antwort">👍</button>
      <span class="action-sep">·</span>
      <button class="bubble-action-btn" id="down-${id}" aria-label="Nicht hilfreiche Antwort">👎</button>
      <span class="action-sep">·</span>
      <button class="bubble-action-btn" id="deep-${id}" aria-label="${t('chat.deepen')}">↩ ${t('chat.deepen')}</button>
    `;

    wrap.appendChild(actions);

    document.getElementById(`speak-${id}`)
      .addEventListener('click', () => this._speakText(response, `speak-${id}`));
    document.getElementById(`copy-${id}`)
      .addEventListener('click', () => this.handleCopy(response, `copy-${id}`));
    document.getElementById(`up-${id}`)
      .addEventListener('click', () => this.handleFeedback('thumbs_up', prompt, response, `up-${id}`));
    document.getElementById(`down-${id}`)
      .addEventListener('click', () => this.handleFeedback('thumbs_down', prompt, response, `down-${id}`));
    document.getElementById(`deep-${id}`)
      .addEventListener('click', () => {
        this.el.chatInput.value = 'Erkläre das genauer: ';
        this.el.chatInput.focus();
      });
  }

  _scrollToBottom() {
    const area = document.getElementById('chat-area');
    area.scrollTop = area.scrollHeight;
  }

  // ── Feedback ────────────────────────────────────────────
  async handleFeedback(type, prompt, response, btnId) {
    let reason = null;

    // Bei Daumen-runter: Inline-Picker anzeigen
    if (type === 'thumbs_down') {
      reason = await this._showReasonPicker(btnId);
    }

    try {
      await fetch(`${API}/feedback/${type}`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ prompt, response, reason }),
      });
      const btn = document.getElementById(btnId);
      if (btn) {
        btn.style.color = type === 'thumbs_up' ? 'var(--green)' : '#fca5a5';
        btn.textContent = type === 'thumbs_up' ? '👍 ✓' : '👎 ✓';
        btn.disabled = true;
      }
    } catch {
      // Feedback trotzdem im UI bestätigen
      const btn = document.getElementById(btnId);
      if (btn) { btn.textContent = type === 'thumbs_up' ? '👍 ✓' : '👎 ✓'; btn.disabled = true; }
    }
  }

  /** Zeigt Inline-Reason-Picker unter btnId, gibt Promise<string|null> zurück */
  _showReasonPicker(btnId) {
    return new Promise((resolve) => {
      const btn = document.getElementById(btnId);
      if (!btn) { resolve(null); return; }

      // Entferne alten Picker falls vorhanden
      document.getElementById('reason-picker')?.remove();

      const reasons = ['Zu lang', 'Falsch', 'Unklar', 'Nicht hilfreich'];
      const picker = document.createElement('div');
      picker.id = 'reason-picker';
      picker.style.cssText = `
        display: flex; flex-wrap: wrap; gap: 6px;
        padding: 8px 0 4px 0;
        animation: slide-in 0.15s ease-out;
      `;

      const cleanup = (val) => {
        picker.remove();
        resolve(val);
      };

      reasons.forEach(r => {
        const rb = document.createElement('button');
        rb.textContent = r;
        rb.style.cssText = `
          background: rgba(239,68,68,0.08);
          border: 1px solid rgba(239,68,68,0.25);
          color: #fca5a5;
          font-family: var(--font-main);
          font-size: 11px;
          padding: 3px 10px;
          border-radius: 100px;
          cursor: pointer;
          transition: background 0.15s;
        `;
        rb.onmouseover = () => rb.style.background = 'rgba(239,68,68,0.18)';
        rb.onmouseout  = () => rb.style.background = 'rgba(239,68,68,0.08)';
        rb.onclick = () => cleanup(r);
        picker.appendChild(rb);
      });

      // Überspringen
      const skip = document.createElement('button');
      skip.textContent = '—';
      skip.title = 'Überspringen';
      skip.style.cssText = `
        background: transparent;
        border: 1px solid var(--panel-border);
        color: var(--text-dim);
        font-size: 11px;
        padding: 3px 8px;
        border-radius: 100px;
        cursor: pointer;
      `;
      skip.onclick = () => cleanup(null);
      picker.appendChild(skip);

      // Picker direkt nach dem Feedback-Button einfügen
      const actionsDiv = btn.closest('.bubble-actions');
      if (actionsDiv) {
        actionsDiv.insertAdjacentElement('afterend', picker);
      }
    });
  }

  // ── Copy ────────────────────────────────────────────────
  async handleCopy(text, btnId) {
    try {
      await navigator.clipboard.writeText(text);
      const btn = document.getElementById(btnId);
      if (btn) {
        const orig = btn.textContent;
        btn.textContent = t('chat.copied');
        setTimeout(() => { btn.textContent = orig; }, 2000);
      }
    } catch {
      // Fallback: select the text
    }
  }

  // ── Aktivitäts-Panel Terminal ────────────────────────────
  _addActivity(type, text, progress) {
    const terminal = this.el.apTerminal;

    // Placeholder entfernen
    const placeholder = terminal.querySelector('.terminal-placeholder');
    if (placeholder) placeholder.remove();

    const line = document.createElement('div');
    line.className = 'terminal-line';

    if (type === 'cmd') {
      line.innerHTML = `<span class="terminal-cmd">&gt; <span class="t-keyword">${this._escHtml(text)}</span></span>`;
    } else if (type === 'progress') {
      line.innerHTML = `
        <span class="terminal-status">${this._escHtml(text)}</span>
        <div class="terminal-progress"><div class="terminal-progress-bar" style="width:0%"></div></div>`;
      // Animiere die Leiste
      setTimeout(() => {
        const bar = line.querySelector('.terminal-progress-bar');
        if (bar) {
          let pct = 0;
          const timer = setInterval(() => {
            pct = Math.min(pct + Math.random() * 15, 90);
            bar.style.width = pct + '%';
            if (pct >= 90) clearInterval(timer);
          }, 300);
        }
      }, 50);
    } else if (type === 'done_inline') {
      line.innerHTML = `<span class="terminal-status done">  ✓ ${this._escHtml(text)}</span>`;
    } else if (type === 'done') {
      // Leiste auf 100%
      const lastBar = terminal.querySelector('.terminal-progress-bar');
      if (lastBar) lastBar.style.width = '100%';
      line.innerHTML = `<span class="terminal-status done">${this._escHtml(text)}</span>`;
    } else if (type === 'error') {
      line.innerHTML = `<span class="terminal-status" style="color:#ef4444">${this._escHtml(text)}</span>`;
    } else {
      line.innerHTML = `<span class="terminal-status">${this._escHtml(text)}</span>`;
    }

    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;

    // Max 20 Einträge
    while (terminal.children.length > 20) {
      terminal.removeChild(terminal.firstChild);
    }

    // ── Mobile Toast: Tool-Aktivität als diskretes Pill anzeigen ──
    if (this.isMobilePWA && (type === 'cmd' || type === 'progress' || type === 'done' || type === 'done_inline' || type === 'error')) {
      this._showMobileToast(text, type);
    }
  }

  _showMobileToast(text, type) {
    if (!this._toastEl) {
      this._toastEl = document.createElement('div');
      this._toastEl.className = 'mobile-toast';
      document.body.appendChild(this._toastEl);
    }
    const el = this._toastEl;
    const emoji = type === 'error' ? '⚠ ' : type === 'done' || type === 'done_inline' ? '✓ ' : '⬡ ';
    el.textContent = emoji + text;
    el.style.color = type === 'error' ? '#fca5a5' : type === 'done' || type === 'done_inline' ? 'var(--green)' : 'var(--green-light)';

    // Einblenden
    el.classList.add('show');
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => {
      el.classList.remove('show');
    }, 2500);
  }

  toggleActivityPanel() {
    this.panelCollapsed = !this.panelCollapsed;
    this.el.activityPanel.classList.toggle('collapsed', this.panelCollapsed);
  }

  // ── Memory Panel ─────────────────────────────────────────
  async loadMemoryPanel() {
    try {
      const res  = await fetch(`${API}/memory/list?limit=5`);
      const data = await res.json();
      const cards = this.el.memoryCards;

      if (!data.entries || data.entries.length === 0) {
        cards.innerHTML = `<div class="memory-placeholder">${t('activity.nothingSaved')}</div>`;
        return;
      }

      cards.innerHTML = '';
      data.entries.forEach(e => {
        const card = document.createElement('div');
        card.className = 'memory-card';
        card.textContent = e.text.slice(0, 120) + (e.text.length > 120 ? '…' : '');
        cards.appendChild(card);
      });
    } catch {
      // Ignorieren wenn Memory nicht erreichbar
    }
  }

  // ── Tab Navigation ──────────────────────────────────────
  switchTab(tabName) {
    // Desktop Tab-Buttons (topnav)
    this.el.tabBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
      btn.setAttribute('aria-selected', btn.dataset.tab === tabName);
    });

    // Mobile Bottom Nav Buttons
    document.querySelectorAll('.mbn-tab').forEach(btn => {
      const active = btn.dataset.tab === tabName;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-selected', active);
    });

    // body.tab-X Klasse für CSS-Sichtbarkeit (z.B. Bottombar nur im Chat)
    document.body.className = document.body.className
      .replace(/\btab-\w+\b/g, '').trim();
    document.body.classList.add(`tab-${tabName}`);

    this.el.tabViews.forEach(view => {
      const isActive = view.id === `view-${tabName}`;
      view.classList.toggle('active', isActive);
      view.hidden = !isActive;
    });

    // Tab-spezifische Aktion
    if (tabName === 'history')  this._renderHistoryList();
    if (tabName === 'memory')   this._loadMemoryList();
    if (tabName === 'profile')  this.loadProfile();
    if (tabName === 'skills')   this.loadSkillsTab();
  }

  // ── Verlauf (localStorage) ──────────────────────────────
  _saveToHistory(prompt, response) {
    const all = JSON.parse(localStorage.getItem(STORE_KEY_HISTORY) || '[]');
    let session = all.find(s => s.id === this.sessionId);
    if (!session) {
      session = {
        id:       this.sessionId,
        date:     new Date().toLocaleDateString('de-DE', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' }),
        title:    prompt.slice(0, 80),
        history:  []
      };
      all.unshift(session);
    }
    session.history = JSON.parse(JSON.stringify(this.history));
    
    if (all.length > 100) all.splice(100);
    localStorage.setItem(STORE_KEY_HISTORY, JSON.stringify(all));
  }

  _renderHistoryList() {
    const all  = JSON.parse(localStorage.getItem(STORE_KEY_HISTORY) || '[]');
    const list = this.el.historyList;
    list.innerHTML = '';

    if (all.length === 0) {
      list.innerHTML = '<div class="history-empty">Noch keine Unterhaltungen gespeichert.</div>';
      return;
    }

    all.forEach(item => {
      const div = document.createElement('div');
      div.className = 'history-item';
      div.style.display = 'flex';
      div.style.alignItems = 'center';
      
      const sessionLength = item.history ? Math.floor(item.history.length / 2) : 1;
      
      div.innerHTML = `
        <div style="flex-grow: 1;">
          <div class="history-title">${this._escHtml(item.title)}</div>
          <div class="history-date">${item.date} (${sessionLength} ${sessionLength === 1 ? (currentLang() === 'de' ? 'Nachricht' : 'message') : (currentLang() === 'de' ? 'Nachrichten' : 'messages')})</div>
        </div>
        <button class="btn-icon delete-history-btn" aria-label="Chat löschen" style="color: var(--text-dim); padding: 8px;">✖</button>
      `;
      
      const delBtn = div.querySelector('.delete-history-btn');
      delBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if(!confirm(currentLang() === 'de' ? 'Möchtest du diesen Chat wirklich dauerhaft löschen?' : 'Delete this chat permanently?')) return;
        const filtered = all.filter(s => s.id !== item.id);
        localStorage.setItem(STORE_KEY_HISTORY, JSON.stringify(filtered));
        this._renderHistoryList();
        if (this.sessionId === item.id) this.clearSession();
      });
      
      div.addEventListener('click', () => {
        this.clearSession(); // Clears DOM and sets new sessionId
        this.sessionId = item.id; // Restore old session ID
        this.history = JSON.parse(JSON.stringify(item.history || []));
        this.el.welcome.style.display = 'none';
        
        // Re-render UI
        this.history.forEach(msg => {
          if (msg.role === 'user') {
            this.renderUserBubble(msg.content);
          } else if (msg.role === 'assistant') {
            const aiBubble = this.renderAIBubble(Date.now() + Math.random());
            aiBubble.classList.remove('streaming-cursor');
            if (window.marked) {
              const rawHtml = window.marked.parse(msg.content, { breaks: true, gfm: true });
              aiBubble.innerHTML = window.DOMPurify ? window.DOMPurify.sanitize(rawHtml) : rawHtml;
            } else {
              aiBubble.textContent = msg.content;
            }
            
            // Re-Bind Syntax Highlighting inside restored bubbles
            if (window.hljs) {
              aiBubble.querySelectorAll('pre code').forEach(block => window.hljs.highlightElement(block));
            }
          }
        });
        
        this.switchTab('chat');
        this.el.chatInput.focus();
      });
      list.appendChild(div);
    });
  }

  // ── Memory Tab (Liste + Delete) ────────────────────────────
  async _loadMemoryList() {
    try {
      const res  = await fetch(`${API}/memory/list`);
      const data = await res.json();
      const list = this.el.memFullList;
      list.innerHTML = '';

      if (!data.entries || data.entries.length === 0) {
        list.innerHTML = `<div class="history-empty">${t('memory.noEntries')}</div>`;
        return;
      }

      data.entries.forEach(e => {
        const card = document.createElement('div');
        card.className = 'memory-full-card';
        card.innerHTML = `
          <span class="memory-full-card-text">${this._escHtml(e.text)}</span>
          <button class="memory-delete-btn" data-id="${this._escHtml(e.id)}" title="Löschen">🗑</button>
        `;
        card.querySelector('.memory-delete-btn').addEventListener('click', async (ev) => {
          const id = ev.target.dataset.id;
          await this._deleteMemoryEntry(id, card);
        });
        list.appendChild(card);
      });
    } catch {
      this.el.memFullList.innerHTML = '<div class="history-empty">Memory nicht erreichbar.</div>';
    }
  }

  async searchMemoryFull() {
    const q = this.el.memSearchInput.value.trim();
    if (!q) { this._loadMemoryList(); return; }
    try {
      const res  = await fetch(`${API}/memory/search?q=${encodeURIComponent(q)}&top_k=20`);
      const data = await res.json();
      const list = this.el.memFullList;
      list.innerHTML = '';

      if (!data.results || data.results.length === 0) {
        list.innerHTML = '<div class="history-empty">Keine Einträge gefunden.</div>';
        return;
      }

      data.results.forEach(r => {
        const card = document.createElement('div');
        card.className = 'memory-full-card';
        card.innerHTML = `<span class="memory-full-card-text">${this._escHtml(r.text)}</span>`;
        list.appendChild(card);
      });
    } catch {
      this.el.memFullList.innerHTML = '<div class="history-empty">Memory nicht erreichbar.</div>';
    }
  }

  async _deleteMemoryEntry(id, cardEl) {
    try {
      const res = await fetch(`${API}/memory/${encodeURIComponent(id)}`, { method: 'DELETE' });
      if (res.ok) cardEl.remove();
    } catch {
      alert('Eintrag konnte nicht gelöscht werden.');
    }
  }

  // ── Profil ──────────────────────────────────────────────
  async loadProfile() {
    try {
      const res  = await fetch(`${API}/profile`);
      const data = await res.json();
      if (data.name)               this.el.pfName.value       = data.name;
      if (data.expertise)          this.el.pfExpertise.value   = data.expertise;
      if (data.preferred_language) this.el.pfLanguage.value    = data.preferred_language;
      if (data.response_style)     this.el.pfStyle.value       = data.response_style;
    } catch {
      // Formular bleibt leer wenn API nicht erreichbar
    }
  }

  async saveProfile() {
    const payload = {
      name:               this.el.pfName.value.trim()     || null,
      expertise:          this.el.pfExpertise.value.trim() || null,
      preferred_language: this.el.pfLanguage.value,
      response_style:     this.el.pfStyle.value,
    };
    
    // Voice im LocalStorage sichern
    localStorage.setItem('mimi_nox_voice', this.el.pfVoice.value);
    
    try {
      const res = await fetch(`${API}/profile`, {
        method:  'PUT',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload),
      });
      if (res.ok) {
        this.el.saveConfirm.classList.remove('hidden');
        setTimeout(() => this.el.saveConfirm.classList.add('hidden'), 3000);
      }
    } catch {
      alert('Profil konnte nicht gespeichert werden. Ist der Server erreichbar?');
    }
  }

  // ── Tastatur Verlauf (↑/↓) ──────────────────────────────
  _navigateHistory(direction) {
    this.cmdIndex = Math.max(-1, Math.min(this.cmdIndex + direction, this.cmdHistory.length - 1));
    this.el.chatInput.value = this.cmdIndex >= 0 ? this.cmdHistory[this.cmdIndex] : '';
    this._autoResize();
  }

  // ── Hilfsfunktionen ─────────────────────────────────────
  _escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ── Skills Tab ──────────────────────────────────────────────
  async loadSkillsTab() {
    const grid = this.el.skillsGrid;
    grid.innerHTML = '<div class="history-empty">Skills werden geladen…</div>';
    try {
      const res  = await fetch(`${API}/skills`);
      const data = await res.json();
      grid.innerHTML = '';

      (data.skills || []).forEach(skill => grid.appendChild(this._renderSkillCard(skill)));
      if (data.skills.length === 0) {
        grid.innerHTML = '<div class="history-empty">Noch keine Skills verfügbar.</div>';
      }
    } catch {
      grid.innerHTML = '<div class="history-empty">Skills konnten nicht geladen werden.</div>';
    }
  }

  _renderSkillCard(skill) {
    const card = document.createElement('div');
    card.className = 'skill-card';
    const isBuiltin = skill.is_builtin;

    card.innerHTML = `
      <div class="skill-card-header">
        <span class="skill-card-name">${this._escHtml(skill.name)}</span>
        <span class="skill-card-trigger">${this._escHtml(skill.trigger)}</span>
      </div>
      <div class="skill-card-desc">${this._escHtml(skill.description)}</div>
      <div class="skill-card-footer">
        <span class="skill-badge ${isBuiltin ? 'builtin' : 'user'}">${isBuiltin ? t('skills.builtIn') : t('skills.userSkill')}</span>
        <div class="skill-card-actions">
          <button class="skill-action-btn edit-btn">${t('skills.editBtn')}</button>
          ${!isBuiltin ? `<button class="skill-action-btn delete delete-btn">🗑 ${t('skills.delete')}</button>` : ''}
        </div>
      </div>
    `;

    card.querySelector('.edit-btn').addEventListener('click', async () => {
      // Für Bearbeitung: Detail laden
      try {
        const res = await fetch(`${API}/skills/${encodeURIComponent(skill.name)}`);
        const detail = await res.json();
        this._openSkillForm(detail);
      } catch {
        alert('Skill konnte nicht geladen werden.');
      }
    });

    const delBtn = card.querySelector('.delete-btn');
    if (delBtn) {
      delBtn.addEventListener('click', async () => {
        if (!confirm(currentLang() === 'de' ? `Skill "${skill.name}" wirklich löschen?` : `Delete skill "${skill.name}"?`)) return;
        const res = await fetch(`${API}/skills/${encodeURIComponent(skill.name)}`, { method: 'DELETE' });
        if (res.ok) {
          card.remove();
          this.loadSkillChips(); // Chips aktualisieren
        } else {
          const err = await res.json();
          alert(err.detail || 'Löschen fehlgeschlagen.');
        }
      });
    }

    return card;
  }

  _openSkillForm(skill) {
    const isEdit = !!skill;
    this.el.skillFormTitle.textContent = isEdit ? `${t('skills.editTitle')}: ${skill.name}` : t('skills.createTitle');
    this.el.sfName.value        = isEdit ? skill.name        : '';
    this.el.sfName.disabled     = isEdit; // Name kann nicht geändert werden (Primary Key)
    this.el.sfTrigger.value     = isEdit ? skill.trigger     : '';
    this.el.sfDescription.value = isEdit ? skill.description : '';
    this.el.sfTools.value       = isEdit ? (skill.tools || []).join(', ') : '';
    this.el.sfPrompt.value      = isEdit ? skill.system_prompt : '';
    this._editingSkillName      = isEdit ? skill.name : null;
    this.el.skillFormWrap.classList.remove('hidden');
    this.el.skillFormWrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  _closeSkillForm() {
    this.el.skillFormWrap.classList.add('hidden');
    this.el.skillForm.reset();
    this.el.sfName.disabled = false;
    this._editingSkillName  = null;
  }

  async _saveSkill() {
    const name = this._editingSkillName || this.el.sfName.value.trim();
    const payload = {
      name:          name,
      trigger:       this.el.sfTrigger.value.trim(),
      description:   this.el.sfDescription.value.trim(),
      tools:         this.el.sfTools.value.split(',').map(t => t.trim()).filter(Boolean),
      system_prompt: this.el.sfPrompt.value.trim(),
    };

    const method = this._editingSkillName ? 'PUT' : 'POST';
    const url    = this._editingSkillName
      ? `${API}/skills/${encodeURIComponent(this._editingSkillName)}`
      : `${API}/skills`;

    try {
      const res = await fetch(url, {
        method, headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || 'Fehler beim Speichern.');
        return;
      }
      this.el.skillSaveConfirm.classList.remove('hidden');
      setTimeout(() => this.el.skillSaveConfirm.classList.add('hidden'), 2500);
      this._closeSkillForm();
      this.loadSkillsTab();
      this.loadSkillChips();
    } catch {
      alert('Skill konnte nicht gespeichert werden. Ist der Server erreichbar?');
    }
  }

  // ── Onboarding Wizard ───────────────────────────────────────
  _initOnboarding() {
    const done = localStorage.getItem('mimi_nox_onboarded');
    if (!done) {
      this.el.onboardingOverlay.classList.remove('hidden');
    }
  }

  _completeOnboarding(category) {
    // Kategorie → empfohlene Skill-Chips
    const skillMap = {
      dev:      ['/review', '/shell', '/files', '/research'],
      research: ['/research', '/files', '/write'],
      writer:   ['/write', '/research'],
      analyst:  ['/files', '/research', '/write'],
      medic:    ['/research', '/write'],
      allround: ['/research', '/files', '/write', '/review', '/shell'],
    };

    const preferred = skillMap[category] || skillMap.allround;
    localStorage.setItem('mimi_nox_preferred_skills', JSON.stringify(preferred));
    localStorage.setItem('mimi_nox_onboarded', '1');
    this.el.onboardingOverlay.classList.add('hidden');

    // Welcome-Text anpassen
    const sub = document.querySelector('.welcome-sub');
    const catLabels = { dev: 'Entwickler', research: 'Forscher', writer: 'Schreiber', analyst: 'Analyst', medic: 'Medizin/Pflege', allround: 'Allgemein' };
    if (sub) sub.textContent = `Modus: ${catLabels[category] || 'Allgemein'} — Tippe eine Frage oder wähle einen Skill`;

    this._addActivity('info', `⚡ Modus: ${catLabels[category] || category} aktiviert`);
    this.loadSkillChips();
  }

  // ── 🎙️ Audio Recording ───────────────────────────────────

  _toggleRecording() {
    if (this.isRecording) {
      this._stopRecording();
    } else {
      this._startRecording();
    }
  }

  async _startRecording() {
    try {
      // Mikrofon-Zugriff anfordern
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this._micStream = stream;

      this._playTone(400, 0.1); // Warm, friendly start tone

      // Format Fallbacks (Chrome → webm, Firefox → ogg, Safari → mp4/default)
      const types = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/mp4',
        'audio/ogg;codecs=opus',
        'audio/ogg',
        '' // Browser fallback default
      ];
      
      let mimeType = '';
      for (const t of types) {
        if (t === '' || MediaRecorder.isTypeSupported(t)) {
          mimeType = t;
          break;
        }
      }

      this._mediaRecorder = new MediaRecorder(stream, { mimeType });
      this._audioChunks = [];

      this._mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) this._audioChunks.push(e.data);
      };

      this._mediaRecorder.onstop = () => this._onRecordingComplete();
      this._mediaRecorder.start(250); // 250ms Chunks

      // AudioContext + AnalyserNode für Waveform
      this._audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = this._audioContext.createMediaStreamSource(stream);
      this._analyser = this._audioContext.createAnalyser();
      this._analyser.fftSize = 256;
      source.connect(this._analyser);

      // UI: Recording-State
      this.isRecording = true;
      this.el.micBtn.classList.add('recording');
      this.el.micContainer.classList.add('active');
      this.el.micBtn.textContent = '⏹';
      this.el.chatInput.placeholder = '🎙️ Aufnahme läuft… Klicke ⏹ zum Stoppen';
      this._addActivity('info', '🎙️ Aufnahme gestartet');

      // Waveform-Animation starten
      this._updateWaveform();

    } catch (err) {
      console.error('Mikrofon-Zugriff verweigert:', err);
      this._addActivity('error', '🎙️ Mikrofon-Zugriff verweigert');
    }
  }

  _stopRecording() {
    this._playTone(300, 0.1); // Lower tone to signal ending

    if (this._mediaRecorder && this._mediaRecorder.state !== 'inactive') {
      this._mediaRecorder.stop();
    }

    // Mic-Stream stoppen
    if (this._micStream) {
      this._micStream.getTracks().forEach(t => t.stop());
      this._micStream = null;
    }

    // AudioContext aufräumen
    if (this._audioContext) {
      this._audioContext.close();
      this._audioContext = null;
    }

    // Waveform-Animation stoppen
    if (this._waveAnimId) {
      cancelAnimationFrame(this._waveAnimId);
      this._waveAnimId = null;
    }

    // UI: Recording-State zurücksetzen
    this.isRecording = false;
    this.el.micBtn.classList.remove('recording');
    this.el.micContainer.classList.remove('active');
    this.el.micBtn.textContent = '🎙️';
    this.el.chatInput.placeholder = t('chat.placeholder');

    // Waveform-Balken zurücksetzen
    const bars = this.el.waveformBars?.querySelectorAll('span');
    if (bars) bars.forEach(b => b.style.height = '3px');
  }

  _cancelRecording() {
    this._isCanceling = true;
    this._playTone(200, 0.15, 'sawtooth'); // Error/Cancel tone
    this._audioChunks = []; 
    this._stopRecording();
    this._addActivity('warning', '🎙️ Aufnahme abgebrochen');
    this.el.chatInput.focus();
  }

  async _onRecordingComplete() {
    if (this._isCanceling) {
      this._isCanceling = false;
      this._audioChunks = [];
      return;
    }
    if (this._audioChunks.length === 0) {
      this._addActivity('info', '🎙️ Keine Audio-Daten aufgezeichnet');
      return;
    }

    // Blob zusammenbauen
    const mimeType = this._audioChunks[0]?.type || 'audio/webm';
    const blob = new Blob(this._audioChunks, { type: mimeType });
    this._audioChunks = [];

    if (blob.size < 1000) {
      this._addActivity('info', '🎙️ Aufnahme zu kurz');
      return;
    }

    this._addActivity('info', `🎙️ Aufnahme beendet (${(blob.size / 1024).toFixed(0)} KB)`);
    this._addActivity('tool_start', '📝 Transkribiere…');

    // UI Loading State
    this.el.chatInput.value = '';
    this.el.chatInput.placeholder = '⏳ Audio wird analysiert...';
    this.el.chatInput.disabled = true;

    // FormData + Upload
    const formData = new FormData();
    const ext = mimeType.includes('mp4') ? '.mp4' : '.webm';
    formData.append('file', blob, `recording${ext}`);

    try {
      const res = await fetch(`${API}/audio/transcribe`, {
        method: 'POST',
        body: formData,
      });

      // UI Config wiederherstellen
      this.el.chatInput.placeholder = t('chat.placeholder');
      this.el.chatInput.disabled = false;
      this.el.chatInput.focus();

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        this._addActivity('error', `❌ Transkription fehlgeschlagen: ${err.detail || res.status}`);
        return;
      }

      const data = await res.json();
      this._addActivity('done_inline', `✅ Transkription: "${data.text?.substring(0, 60) || '(leer)'}…"`);

      // Audio-Bubble im Chat anzeigen
      this._renderAudioBubble(data.audio_url, data.text);

      if (data.text && data.text.trim()) {
        // Transkription als Nachricht an Nox senden, mit Voice-Modus-Flag
        this.el.chatInput.value = data.text;
        this.submitMessage(true);
      } else {
        this._addActivity('info', '🎙️ Keine Sprache erkannt (Stille)');
      }

    } catch (err) {
      console.error('Audio-Upload fehlgeschlagen:', err);
      this._addActivity('error', '❌ Audio-Upload fehlgeschlagen');
      
      // Fallback UI Reset
      this.el.chatInput.placeholder = t('chat.placeholder');
      this.el.chatInput.disabled = false;
    }
  }

  _updateWaveform() {
    if (!this.isRecording || !this._analyser) return;

    const dataArray = new Uint8Array(this._analyser.frequencyBinCount);
    this._analyser.getByteFrequencyData(dataArray);

    const bars = this.el.waveformBars?.querySelectorAll('span');
    if (bars && bars.length >= 5) {
      // 5 Frequenz-Bänder auf die Balken mappen
      const step = Math.floor(dataArray.length / 6);
      for (let i = 0; i < 5; i++) {
        const val = dataArray[step * (i + 1)] || 0;
        const height = Math.max(3, (val / 255) * 24);
        bars[i].style.height = `${height}px`;
      }
    }

    this._waveAnimId = requestAnimationFrame(() => this._updateWaveform());
  }

  _renderAudioBubble(audioUrl, transcription) {
    // Audio-Nachricht im Chat als User-Bubble anzeigen
    const wrap = document.createElement('div');
    wrap.className = 'msg user';
    const escapedText = (transcription || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    wrap.innerHTML = `
      <div class="msg-content">
        <div class="audio-bubble">
          <audio controls preload="metadata" src="${audioUrl}"></audio>
          ${transcription ? `<div class="audio-transcription">📝 „${escapedText}“</div>` : ''}
        </div>
      </div>`;
    this.el.messages.appendChild(wrap);
    this.el.welcome?.classList.add('hidden');
    this.el.messages.scrollTop = this.el.messages.scrollHeight;
  }

  // ── Web Audio UX / Tones ─────────────────────────────────
  _playTone(frequency, duration, type = 'sine') {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(frequency, ctx.currentTime);
      gain.gain.setValueAtTime(0, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.1, ctx.currentTime + 0.02);
      gain.gain.linearRampToValueAtTime(0, ctx.currentTime + duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch { /* ignore if audio context blocked */ }
  }
}


// ── Start ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const app = new NoxApp();
  app.init();
  window._nox = app; // Debug-Zugriff in DevTools
});


// ── PWA Service Worker ──────────────────────────────────────────────────────
if ('serviceWorker' in navigator && window.location.protocol !== 'file:') {
  window.addEventListener('load', async () => {
    try {
      const reg = await navigator.serviceWorker.register('/service-worker.js');

      // Check for updates periodically
      setInterval(() => reg.update(), 60 * 60 * 1000); // every 1h

      // New SW waiting → show update toast
      reg.addEventListener('updatefound', () => {
        const newSW = reg.installing;
        if (!newSW) return;
        newSW.addEventListener('statechange', () => {
          if (newSW.state === 'installed' && navigator.serviceWorker.controller) {
            _showUpdateToast(newSW);
          }
        });
      });
    } catch(err) {
      console.warn('Service Worker registration failed:', err);
    }
  });
}

function _showUpdateToast(sw) {
  const toast = document.createElement('div');
  toast.style.cssText = `
    position:fixed; bottom:80px; left:50%; transform:translateX(-50%);
    background:rgba(34,197,94,0.15); border:1px solid rgba(34,197,94,0.4);
    color:#4ade80; padding:10px 20px; border-radius:12px; z-index:9999;
    font-size:13px; backdrop-filter:blur(12px); cursor:pointer;
    display:flex; align-items:center; gap:10px; white-space:nowrap;
  `;
  toast.innerHTML = '🔄 Update verfügbar <strong>→ Jetzt aktualisieren</strong>';
  toast.onclick = () => { sw.postMessage('skipWaiting'); window.location.reload(); };
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 12000);
}
