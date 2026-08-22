/**
 * MiMi Nox — WebSocket Client for real-time chat
 *
 * Connects to the backend at localhost:8765 via WebSocket.
 * Handles reconnection, message streaming, and tool approval.
 */

import type { ToolApprovalRequest, WSMessage } from '@/types'

export type { ToolApprovalRequest, WSMessage }

type WSEventCallback = (data: WSMessage) => void
type ToolApprovalCallback = (request: ToolApprovalRequest) => void

export class WSClient {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts: number = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private messageCallback: WSEventCallback | null = null
  private toolApprovalCallback: ToolApprovalCallback | null = null
  private statusCallback: ((status: 'connected' | 'disconnected' | 'reconnecting') => void) | null = null
  private pingInterval: ReturnType<typeof setInterval> | null = null

  /**
   * Default: same-origin (PWA wird vom Backend serviert → API+WS auf dem
   * selben Port, keine hartkodierte 8765-Annahme). VITE_WS_URL überschreibt
   * für Dev-Setupps (Vite-Port ≠ API-Port, ohne Proxy).
   */
  constructor(baseUrl?: string) {
    const base =
      baseUrl ||
      import.meta.env.VITE_WS_URL ||
      (typeof window !== 'undefined'
        ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
        : 'ws://localhost:8765')
    this.url = `${base.replace(/\/$/, '')}/ws/chat`
  }

  connect(sessionId?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const url = sessionId ? `${this.url}?session_id=${sessionId}` : this.url
        this.ws = new WebSocket(url)

        this.ws.onopen = () => {
          console.log('[WS] Connected')
          this.reconnectAttempts = 0
          this.startPing()
          this.statusCallback?.('connected')
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as WSMessage

            if (data.type === 'tool_call' && this.toolApprovalCallback) {
              this.toolApprovalCallback({
                tool_name: data.tool_name || 'unknown',
                tool_args: data.tool_args || {},
                description: `Tool ${data.tool_name} wants to execute`,
                session_id: data.session_id || '',
              })
            } else {
              this.messageCallback?.(data)
            }
          } catch (error) {
            console.error('[WS] Failed to parse message:', error)
          }
        }

        this.ws.onclose = () => {
          console.log('[WS] Disconnected')
          this.stopPing()
          this.statusCallback?.('disconnected')
          this.attemptReconnect()
        }

        this.ws.onerror = (error) => {
          console.error('[WS] Error:', error)
          reject(error)
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  disconnect(): void {
    this.stopPing()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  send(message: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'chat', content: message }))
    } else {
      console.error('[WS] Cannot send: not connected')
    }
  }

  approveTool(sessionId: string, toolName: string, approved: boolean): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: 'tool_approval',
          session_id: sessionId,
          tool_name: toolName,
          approved,
        })
      )
    }
  }

  onMessage(callback: WSEventCallback): void {
    this.messageCallback = callback
  }

  onToolApproval(callback: ToolApprovalCallback): void {
    this.toolApprovalCallback = callback
  }

  onStatus(callback: (status: 'connected' | 'disconnected' | 'reconnecting') => void): void {
    this.statusCallback = callback
  }

  private startPing(): void {
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)
  }

  private stopPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WS] Max reconnect attempts reached')
      this.statusCallback?.('disconnected')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
    this.statusCallback?.('reconnecting')

    setTimeout(() => {
      console.log(`[WS] Reconnect attempt ${this.reconnectAttempts}`)
      this.connect().catch(() => {})
    }, delay)
  }
}

export default WSClient