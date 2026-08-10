import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SchedulerPanel from './SchedulerPanel'
import type { ScheduleJob } from '@/lib/api'

function makeJob(id: string, task: string, cron: string): ScheduleJob {
  return { id, task, cron, next_run: '2026-08-09 08:00' }
}

describe('SchedulerPanel', () => {
  it('renders the form inputs', () => {
    render(<SchedulerPanel jobs={[]} onCreate={vi.fn()} onDelete={vi.fn()} />)
    expect(screen.getByPlaceholderText('Aufgabe (natürliche Sprache)')).toBeTruthy()
    expect(screen.getByPlaceholderText('Cron (z.B. 0 8 * * *)')).toBeTruthy()
    expect(screen.getByTitle('Job anlegen')).toBeTruthy()
  })

  it('fires onCreate with task and cron', () => {
    const onCreate = vi.fn()
    render(<SchedulerPanel jobs={[]} onCreate={onCreate} onDelete={vi.fn()} />)
    fireEvent.change(screen.getByPlaceholderText('Aufgabe (natürliche Sprache)'), {
      target: { value: 'Tägliche Zusammenfassung' },
    })
    fireEvent.change(screen.getByPlaceholderText('Cron (z.B. 0 8 * * *)'), {
      target: { value: '0 8 * * *' },
    })
    fireEvent.click(screen.getByTitle('Job anlegen'))
    expect(onCreate).toHaveBeenCalledWith('Tägliche Zusammenfassung', '0 8 * * *')
  })

  it('lists scheduled jobs', () => {
    const { container } = render(
      <SchedulerPanel jobs={[makeJob('j1', 'Täglich', '0 8 * * *')]} onCreate={vi.fn()} onDelete={vi.fn()} />,
    )
    expect(screen.getByText('Täglich')).toBeTruthy()
    expect(container.querySelectorAll('[title="Job j1 löschen"]').length).toBe(1)
  })

  it('fires onDelete with the job id', () => {
    const onDelete = vi.fn()
    render(<SchedulerPanel jobs={[makeJob('j1', 'Täglich', '0 8 * * *')]} onCreate={vi.fn()} onDelete={onDelete} />)
    fireEvent.click(screen.getByTitle('Job j1 löschen'))
    expect(onDelete).toHaveBeenCalledWith('j1')
  })
})
