import { useState } from 'react'
import { CalendarClock, Plus, Trash2 } from 'lucide-react'
import type { ScheduleJob } from '@/lib/api'

interface SchedulerPanelProps {
  jobs: ScheduleJob[]
  onCreate: (task: string, cron: string) => void
  onDelete: (id: string) => void
}

/**
 * Scheduler-Frontend (P2-8) — formularbasierte Anlage und Verwaltung
 * wiederkehrender Aufgaben. Jobs kommen vom lokalen Backend (/api/schedule).
 */
export default function SchedulerPanel({ jobs, onCreate, onDelete }: SchedulerPanelProps) {
  const [task, setTask] = useState('')
  const [cron, setCron] = useState('')

  const submit = () => {
    if (!task.trim() || !cron.trim()) return
    onCreate(task.trim(), cron.trim())
    setTask('')
    setCron('')
  }

  return (
    <div className="p-4 rounded-2xl liquid-glass space-y-3">
      <div className="flex items-center gap-2 text-green-400/80 text-sm font-medium">
        <CalendarClock className="h-4 w-4" />
        Wiederkehrende Aufgaben
      </div>
      <div className="flex items-center gap-2">
        <input
          value={task}
          onChange={(e) => setTask(e.target.value)}
          placeholder="Aufgabe (natürliche Sprache)"
          className="flex-1 min-w-0 bg-white/5 rounded-lg px-2 py-1.5 text-sm text-white placeholder:text-white/30 outline-none"
        />
        <input
          value={cron}
          onChange={(e) => setCron(e.target.value)}
          placeholder="Cron (z.B. 0 8 * * *)"
          className="flex-1 min-w-0 bg-white/5 rounded-lg px-2 py-1.5 text-sm text-white placeholder:text-white/30 outline-none"
        />
        <button
          onClick={submit}
          title="Job anlegen"
          disabled={!task.trim() || !cron.trim()}
          className="p-2 rounded-lg bg-green-500 hover:bg-green-600 disabled:opacity-30 disabled:cursor-not-allowed text-black transition-colors"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      {jobs.length > 0 && (
        <div className="space-y-1.5">
          {jobs.map((job) => (
            <div key={job.id} className="flex items-center gap-2 text-sm text-white/70">
              <span className="flex-1 min-w-0 truncate">{job.task}</span>
              <span className="font-mono text-[10px] text-white/35">{job.cron}</span>
              {job.next_run && (
                <span className="font-mono text-[10px] text-green-400/60">{job.next_run}</span>
              )}
              <button
                onClick={() => onDelete(job.id)}
                title={`Job ${job.id} löschen`}
                className="p-1 rounded hover:text-red-400 text-white/40 transition-colors"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
