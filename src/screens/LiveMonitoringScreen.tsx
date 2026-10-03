import { useHealthData } from '../context/HealthDataContext'
import DataSourcePanel from '../components/DataSourcePanel'
import DigitalTwinPanel from '../components/DigitalTwinPanel'
import PatientWorkspace from './PatientWorkspace'

export default function LiveMonitoringScreen() {
  const { normalizedTelemetry, replayState, deviceStatus } = useHealthData()
  const source = normalizedTelemetry?.source_type === 'SYNTHETIC_SIMULATOR' ? 'synthetic' : 'dataset'
  return (
    <div>
      <div className="mx-auto grid max-w-[1500px] grid-cols-1 gap-5 p-4 md:p-6 xl:grid-cols-[1.25fr_0.75fr]">
        <DigitalTwinPanel source={source} replayState={replayState} telemetry={normalizedTelemetry} deviceStatus={deviceStatus} />
        <DataSourcePanel />
      </div>
      <PatientWorkspace />
    </div>
  )
}
