'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Zap, Brain, Languages, Server, Shield,
  X, Check, Loader2,
} from 'lucide-react'
import { AppSettings, getSettings, updateSettings, healthCheck } from '@/lib/api'

interface SettingsPanelProps {
  isOpen: boolean
  onClose: () => void
}

type TabKey = 'model' | 'api' | 'memory' | 'language'

const tabs: { key: TabKey; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: 'model', label: 'Modell', icon: Zap },
  { key: 'api', label: 'API', icon: Server },
  { key: 'memory', label: 'Memory', icon: Brain },
  { key: 'language', label: 'Sprache', icon: Languages },
]

const modelOptions = [
  { id: 'gemma4:e4b', label: 'gemma4:e4b', desc: 'Default — schnell & effizient' },
  { id: 'llama3.1:8b', label: 'LLaMA 3.1 8B', desc: 'Open Source, stark' },
  { id: 'mistral:7b', label: 'Mistral 7B', desc: 'Zuverlässig, gut für Code' },
  { id: 'custom', label: 'Custom Ollama', desc: 'Eigenes Modell' },
]

const languageOptions = [
  { code: 'de', label: 'Deutsch', native: 'Deutsch' },
  { code: 'en', label: 'English', native: 'English' },
  { code: 'fr', label: 'Français', native: 'Français' },
  { code: 'es', label: 'Español', native: 'Español' },
]

export default function SettingsPanel({ isOpen, onClose }: SettingsPanelProps) {
  const [activeTab, setActiveTab] = useState<TabKey>('model')
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  // Custom model settings (visible when custom selected)
  const [customEndpoint, setCustomEndpoint] = useState('')
  const [customApiKey, setCustomApiKey] = useState('')

  useEffect(() => {
    if (!isOpen) return
    loadSettings()
  }, [isOpen])

  // Esc schließt das Panel (Standard-Dialog-Verhalten; a11y)
  useEffect(() => {
    if (!isOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isOpen, onClose])

  async function loadSettings() {
    try {
      setLoading(true)
      const data = await getSettings()
      setSettings(data)
      if (data.provider.type === 'custom_ollama') {
        setCustomEndpoint(data.provider.endpoint || '')
        setCustomApiKey(data.provider.api_key || '')
      }
    } catch {
      // Default settings
      setSettings({
        provider: { type: 'local_ollama', model: 'gemma4:e4b' },
        memory_enabled: true,
        language: 'de',
        theme: 'dark',
      })
    } finally {
      setLoading(false)
    }
  }

  async function saveSettings() {
    try {
      setSaving(true)
      const model = activeTab === 'model'
        ? settings?.provider.model || 'gemma4:e4b'
        : undefined
      const endpoint = activeTab === 'api' ? customEndpoint : undefined
      const apiKey = activeTab === 'api' ? customApiKey : undefined
      const type = activeTab === 'model' && model === 'custom'
        ? 'custom_ollama' as const
        : (settings?.provider.type || 'local_ollama') as 'local_ollama' | 'custom_ollama' | 'openai_compatible'

      const newSettings: Partial<AppSettings> = {
        provider: {
          ...(settings?.provider || {}),
          model: model || (settings?.provider.model ?? ''),
          type,
          endpoint,
          api_key: apiKey,
        },
        language: activeTab === 'language' ? (settings?.language ?? 'de') : settings?.language,
        memory_enabled: activeTab === 'memory' ? settings?.memory_enabled : undefined,
      }

      await updateSettings(newSettings)
      loadSettings()
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      console.error('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  async function checkHealth() {
    try {
      const result = await healthCheck()
      const provider = result.active_provider === 'openai_compatible' ? 'Remote (vLLM/DGX)' : result.active_provider
      alert(
        `Backend Status: ${result.status}\n` +
        `Engine: ${provider}\n` +
        `Modell: ${result.active_model}\n` +
        `Tier: ${result.active_tier}${result.dgx_online ? ' (DGX online)' : ''}`
      )
    } catch {
      alert('Backend nicht erreichbar. Läuft der Server?')
    }
  }

  const tabContent: Record<TabKey, React.ReactNode> = {
    model: (
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-white/60 mb-3">Modell wählen</h3>
        {modelOptions.map((opt) => (
          <button
            key={opt.id}
            onClick={() => {
              if (opt.id === 'custom') {
                setSettings(prev => prev ? { ...prev, provider: { ...prev.provider, type: 'custom_ollama' } } : { provider: { type: 'custom_ollama', model: '' }, memory_enabled: true, language: 'de', theme: 'dark' })
              } else {
                setSettings(prev => prev ? { ...prev, provider: { ...prev.provider, model: opt.id } } : prev!)
              }
            }}
            className={`w-full text-left rounded-xl p-4 transition-all duration-200 ${
              settings?.provider.model === opt.id || (opt.id === 'custom' && settings?.provider.type === 'custom_ollama')
                ? 'bg-green-500/10 border border-green-400/20'
                : 'liquid-glass hover:bg-green-500/5 border-transparent'
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-white/90">{opt.label}</p>
                <p className="text-xs text-white/30 mt-0.5">{opt.desc}</p>
              </div>
              {(settings?.provider.model === opt.id || (opt.id === 'custom' && settings?.provider.type === 'custom_ollama')) && (
                <Check className="h-4 w-4 text-green-400" />
              )}
            </div>
          </button>
        ))}

        {customEndpoint && (
          <div className="mt-4 space-y-3">
            <div>
              <label className="text-xs text-white/40 mb-1 block">Ollama Endpoint</label>
              <input
                value={customEndpoint}
                onChange={e => setCustomEndpoint(e.target.value)}
                placeholder="http://localhost:11434"
                className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 placeholder:text-white/20 outline-none focus:border-green-400/30 transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-white/40 mb-1 block">API Key (optional)</label>
              <input
                value={customApiKey}
                onChange={e => setCustomApiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 placeholder:text-white/20 outline-none focus:border-green-400/30 transition-colors"
              />
            </div>
          </div>
        )}
      </div>
    ),

    api: (
      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-medium text-white/60 mb-3">API Einstellungen</h3>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-white/40 mb-1 block">Ollama Endpoint</label>
              <input
                value={customEndpoint}
                onChange={e => setCustomEndpoint(e.target.value)}
                placeholder="http://localhost:11434"
                className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 placeholder:text-white/20 outline-none focus:border-green-400/30 transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-white/40 mb-1 block">API Key (optional)</label>
              <input
                value={customApiKey}
                onChange={e => setCustomApiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 placeholder:text-white/20 outline-none focus:border-green-400/30 transition-colors"
              />
            </div>
          </div>
        </div>

        {/* Connection test */}
        <div className="border-t border-white/5 pt-4">
          <h3 className="text-sm font-medium text-white/60 mb-3">Verbindung testen</h3>
          <button
            onClick={checkHealth}
            className="w-full liquid-glass rounded-xl h-10 text-sm font-medium text-white/70 hover:text-white hover:bg-green-500/5 transition-all flex items-center justify-center gap-2"
          >
            <Zap className="h-4 w-4" />
            Health Check
          </button>
        </div>

        {/* Security info */}
        <div className="border-t border-white/5 pt-4">
          <h3 className="text-sm font-medium text-white/60 mb-3 flex items-center gap-2">
            <Shield className="h-3.5 w-3.5 text-green-400/50" />
            Sicherheit
          </h3>
          <div className="space-y-2 text-xs text-white/30">
            <p>• Server bindet nur an 127.0.0.1 (localhost)</p>
            <p>• CORS auf lokale Domänen beschränkt</p>
            <p>• Tool-Ausführung erfordert Bestätigung</p>
            <p>• Keine Daten werden an externe Server gesendet</p>
          </div>
        </div>
      </div>
    ),

    memory: (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-white/60">Semantic Memory</h3>
            <p className="text-xs text-white/30 mt-0.5">ChromaDB Vektorspeicher</p>
          </div>
          <button
            onClick={() => {
              setSettings(prev => prev ? { ...prev, memory_enabled: !prev.memory_enabled } : prev!)
            }}
            className={`relative w-11 h-6 rounded-full transition-colors duration-200 ${
              settings?.memory_enabled ? 'bg-green-500' : 'bg-white/15'
            }`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform duration-200 ${
                settings?.memory_enabled ? 'translate-x-5' : ''
              }`}
            />
          </button>
        </div>

        {/* Stats */}
        <div className="liquid-glass rounded-xl p-4 space-y-3">
          <h4 className="text-xs font-medium text-white/40 uppercase tracking-wider">Memory-Statistik</h4>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-2xl font-semibold text-green-400">0</p>
              <p className="text-xs text-white/30">Vektoren</p>
            </div>
            <div>
              <p className="text-2xl font-semibold text-green-400">0 KB</p>
              <p className="text-xs text-white/30">Speicher</p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="space-y-2">
          <button className="w-full liquid-glass rounded-xl h-10 text-sm font-medium text-white/70 hover:text-white hover:bg-green-500/5 transition-all">
            Memory leeren
          </button>
        </div>
      </div>
    ),

    language: (
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-white/60 mb-3">Sprache wählen</h3>
        {languageOptions.map((opt) => (
          <button
            key={opt.code}
            onClick={() => setSettings(prev => prev ? { ...prev, language: opt.code } : prev!)}
            className={`w-full text-left rounded-xl p-3.5 transition-all duration-200 ${
              settings?.language === opt.code
                ? 'bg-green-500/10 border border-green-400/20'
                : 'liquid-glass hover:bg-green-500/5 border-transparent'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-white/90">{opt.label}</span>
              <span className="text-xs text-white/30">{opt.native}</span>
            </div>
          </button>
        ))}

        {/* Theme toggle */}
        <div className="mt-6 border-t border-white/5 pt-4">
          <h3 className="text-sm font-medium text-white/60 mb-3">Theme</h3>
          <div className="flex gap-2">
            <button className="flex-1 liquid-glass rounded-xl p-3 text-xs font-medium text-white/70 bg-green-500/10 border border-green-400/20">
              🌙 Dunkel
            </button>
            <button className="flex-1 liquid-glass rounded-xl p-3 text-xs font-medium text-white/40 hover:text-white/60 transition-colors">
              ☀️ Hell
            </button>
          </div>
        </div>
      </div>
    ),
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          {/* Panel */}
          <motion.aside
            initial={{ x: 320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 320, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            data-testid="settings-panel"
            className="fixed right-0 top-0 h-full w-80 max-w-[90vw] z-50 liquid-glass-strong border-l border-green-500/10 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/5">
              <h2 className="text-sm font-semibold text-white/90">Einstellungen</h2>
              <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/5 text-white/40 hover:text-white transition-colors">
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-white/5 px-2">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-3 text-xs font-medium transition-all relative ${
                    activeTab === tab.key ? 'text-green-400' : 'text-white/30 hover:text-white/50'
                  }`}
                >
                  <tab.icon className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">{tab.label}</span>
                  {activeTab === tab.key && (
                    <motion.div
                      layoutId="settingsTabIndicator"
                      className="absolute bottom-0 left-0 right-0 h-px bg-green-400"
                    />
                  )}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {loading ? (
                <div className="flex items-center justify-center h-32">
                  <Loader2 className="h-5 w-5 animate-spin text-green-400/50" />
                </div>
              ) : (
                <AnimatePresence mode="wait">
                  <motion.div
                    key={activeTab}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.15 }}
                  >
                    {tabContent[activeTab]}
                  </motion.div>
                </AnimatePresence>
              )}
            </div>

            {/* Footer save */}
            <div className="p-4 border-t border-white/5">
              {saved ? (
                <div className="flex items-center justify-center gap-2 h-10 text-sm text-green-400">
                  <Check className="h-4 w-4" />
                  Gespeichert
                </div>
              ) : (
                <button
                  onClick={saveSettings}
                  disabled={saving}
                  className="w-full bg-green-500 hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed text-black rounded-xl h-10 text-sm font-medium transition-all forest-glow flex items-center justify-center gap-2"
                >
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                  Speichern
                </button>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}