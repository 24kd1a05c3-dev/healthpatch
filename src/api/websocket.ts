type WSMessageType = 'health_data' | 'alert' | 'device_status' | 'normalized_telemetry' | 'replay_state';
type WSListener = (data: any) => void;

class HealthPatchWebSocket {
  private ws: WebSocket | null = null;
  private listeners: Map<WSMessageType, Set<WSListener>> = new Map();
  private reconnectTimeout: number | null = null;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private userId: string = '';
  private token: string = '';
  private enabled = false;

  connect(userId: string, token: string): void {
    this.disconnect();
    this.enabled = true;
    this.userId = userId;
    this.token = token;
    this.doConnect();
  }

  private doConnect(): void {
    if (!this.enabled) return;
    const base = import.meta.env.VITE_WS_BASE || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8000`;
    const resolvedBase = new URL(base, window.location.origin);
    resolvedBase.protocol = resolvedBase.protocol === 'https:' || resolvedBase.protocol === 'wss:' ? 'wss:' : 'ws:';
    const url = `${resolvedBase.toString().replace(/\/$/, '')}/ws/${this.userId}?token=${encodeURIComponent(this.token)}`;
    const socket = new WebSocket(url);
    this.ws = socket;
    socket.onopen = () => { this.reconnectDelay = 1000; };
    socket.onmessage = (event) => {
      if (this.ws !== socket) return;
      try {
        const msg = JSON.parse(event.data);
        const listeners = this.listeners.get(msg.type);
        if (listeners) listeners.forEach(fn => fn(msg.data));
      } catch (e) {
        console.error('WS parse error', e);
      }
    };
    socket.onclose = () => { if (this.ws === socket && this.enabled) this.scheduleReconnect(); };
    socket.onerror = () => { socket.close(); };
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) return;
    this.reconnectTimeout = window.setTimeout(() => {
      this.reconnectTimeout = null;
      this.doConnect();
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
    }, this.reconnectDelay);
  }

  on(type: WSMessageType, listener: WSListener): () => void {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)!.add(listener);
    return () => this.listeners.get(type)?.delete(listener);
  }

  disconnect(): void {
    this.enabled = false;
    if (this.reconnectTimeout) { clearTimeout(this.reconnectTimeout); this.reconnectTimeout = null; }
    if (this.ws) { this.ws.onclose = null; this.ws.close(); }
    this.ws = null;
  }

  get connected(): boolean { return this.ws?.readyState === WebSocket.OPEN; }
}

export const wsClient = new HealthPatchWebSocket();
export type { WSMessageType, WSListener };
