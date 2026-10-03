import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useAuth } from './AuthContext';
import { getLatestData } from '../api/health';
import { getAlerts } from '../api/alerts';
import { wsClient } from '../api/websocket';

interface HealthDataContextType {
  latestData: any;
  alerts: any[];
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
  deviceStatus: any;
  normalizedTelemetry: any;
  replayState: any;
  waveformHistory: WaveformHistory;
}

export type SignalPoint = { t: number; v: number | null };
export type WaveformHistory = Record<'ppg' | 'ecg' | 'ecg_v' | 'ecg_avr' | 'respiration', SignalPoint[]>;

const EMPTY_WAVEFORMS: WaveformHistory = { ppg: [], ecg: [], ecg_v: [], ecg_avr: [], respiration: [] };
const MAX_WAVEFORM_POINTS = 2500;

const HealthDataContext = createContext<HealthDataContextType | undefined>(undefined);

export const HealthDataProvider = ({ children }: { children: ReactNode }) => {
  const { isAuthenticated, user } = useAuth();
  const [latestData, setLatestData] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [deviceStatus, setDeviceStatus] = useState<any>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected');
  const [normalizedTelemetry, setNormalizedTelemetry] = useState<any>(null);
  const [replayState, setReplayState] = useState<any>(null);
  const [waveformHistory, setWaveformHistory] = useState<WaveformHistory>(EMPTY_WAVEFORMS);

  useEffect(() => {
    setLatestData(null); setNormalizedTelemetry(null); setReplayState(null);
    setDeviceStatus(null); setAlerts([]); setWaveformHistory(EMPTY_WAVEFORMS);
    if (!isAuthenticated || !user) { setConnectionStatus('disconnected'); return; }
    let lastRecord = '';
    let lastOffset = -1;

    setConnectionStatus('connecting');
    let isSubscribed = true;

    // Fetch initial data
    const fetchInitial = async () => {
      try {
        const [data, alertsData] = await Promise.all([
          getLatestData(user.id).catch(() => null),
          getAlerts(undefined, user.id).catch(() => [])
        ]);
        if (isSubscribed) {
          if (data) setLatestData(data);
          if (alertsData) setAlerts(alertsData);
        }
      } catch (err) {
        console.error('Failed to fetch initial health data', err);
      }
    };
    fetchInitial();

    // WebSocket Listeners
    const cleanupData = wsClient.on('health_data', (data) => {
      if (data.user_id && data.user_id !== user.id) return;
      setLatestData((prev: any) => ({ ...prev, ...data }));
      setConnectionStatus('connected');
    });
    const cleanupAlert = wsClient.on('alert', (alert) => {
      setAlerts((prev) => [alert, ...prev]);
    });
    const cleanupDevice = wsClient.on('device_status', (status) => {
      setDeviceStatus(status);
    });
    const cleanupTelemetry = wsClient.on('normalized_telemetry', (telemetry) => {
      if (telemetry.user_id !== user.id) return;
      const record = `${telemetry.source_type}:${telemetry.provenance?.record_id}:${telemetry.stream_id ?? ''}`;
      const offset = Number(telemetry.sequence_number ?? telemetry.waveforms?.start_offset_seconds ?? Date.parse(telemetry.timestamp));
      if (record === lastRecord && offset <= lastOffset) return;
      const reset = record !== lastRecord || offset < lastOffset;
      lastRecord = record; lastOffset = offset;
      setNormalizedTelemetry(telemetry);
      const waveforms = telemetry.waveforms;
      if (!waveforms) setWaveformHistory(EMPTY_WAVEFORMS);
      if (waveforms) {
        setWaveformHistory(previous => {
          const offset = Number(waveforms.start_offset_seconds ?? 0);
          const interval = Number(waveforms.sample_interval_ms ?? 8) / 1000;
          const priorEnd = previous.ppg.at(-1)?.t;
          const base = reset || (priorEnd !== undefined && offset <= priorEnd) ? EMPTY_WAVEFORMS : previous;
          const append = (channel: keyof WaveformHistory) => [
            ...base[channel],
            ...(waveforms[channel] ?? []).map((v: number | null, index: number) => ({ t: offset + index * interval, v })),
          ].slice(-MAX_WAVEFORM_POINTS);
          return { ppg: append('ppg'), ecg: append('ecg'), ecg_v: append('ecg_v'), ecg_avr: append('ecg_avr'), respiration: append('respiration') };
        });
      }
      setLatestData({
        heart_rate: telemetry.vitals?.heart_rate,
        pulse_rate: telemetry.vitals?.pulse_rate,
        spo2: telemetry.vitals?.spo2,
        respiratory_rate: telemetry.vitals?.respiratory_rate,
        timestamp: telemetry.timestamp,
        source_type: telemetry.source_type,
        provenance: telemetry.provenance,
      });
      setConnectionStatus('connected');
    });
    const cleanupReplay = wsClient.on('replay_state', setReplayState);

    const checkConnection = setInterval(() => {
      if (wsClient.connected) {
        setConnectionStatus('connected');
      } else {
        setConnectionStatus('disconnected');
      }
    }, 5000);

    return () => {
      isSubscribed = false;
      cleanupData();
      cleanupAlert();
      cleanupDevice();
      cleanupTelemetry();
      cleanupReplay();
      clearInterval(checkConnection);
    };
  }, [isAuthenticated, user?.id]);

  const value = {
    latestData,
    alerts,
    connectionStatus,
    deviceStatus,
    normalizedTelemetry,
    replayState,
    waveformHistory,
  };

  return <HealthDataContext.Provider value={value}>{children}</HealthDataContext.Provider>;
};

export const useHealthData = () => {
  const context = useContext(HealthDataContext);
  if (context === undefined) {
    throw new Error('useHealthData must be used within a HealthDataProvider');
  }
  return context;
};
