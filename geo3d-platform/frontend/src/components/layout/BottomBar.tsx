import { useViewerStore } from '../../stores'

export default function BottomBar() {
  const { cameraPosition, cursorCoords, fps } = useViewerStore()

  const fmtDeg = (v: number, isLon = false) => {
    const dir = isLon ? (v >= 0 ? 'E' : 'W') : (v >= 0 ? 'N' : 'S')
    return `${Math.abs(v).toFixed(5)}° ${dir}`
  }

  const fmtAlt = (m: number) =>
    m >= 1000 ? `${(m / 1000).toFixed(2)} km` : `${m.toFixed(0)} m`

  return (
    <footer className="bottombar">
      {/* Cursor coordinates */}
      <div className="bottombar__item">
        <span style={{ color: 'var(--color-text-muted)' }}>🖱</span>
        <span>
          {cursorCoords
            ? `${fmtDeg(cursorCoords.lat)} / ${fmtDeg(cursorCoords.lon, true)}`
            : '— / —'}
        </span>
      </div>

      <div className="bottombar__divider" />

      {/* Camera altitude */}
      <div className="bottombar__item">
        <span style={{ color: 'var(--color-text-muted)' }}>📷</span>
        <span>
          {cameraPosition ? fmtAlt(cameraPosition.alt) : '—'}
        </span>
      </div>

      <div className="bottombar__divider" />

      {/* Camera position */}
      {cameraPosition && (
        <>
          <div className="bottombar__item">
            <span style={{ color: 'var(--color-text-muted)' }}>📍</span>
            <span>
              {fmtDeg(cameraPosition.lat)} / {fmtDeg(cameraPosition.lon, true)}
            </span>
          </div>
          <div className="bottombar__divider" />
        </>
      )}

      <div className="bottombar__spacer" />

      {/* FPS */}
      <div className="bottombar__item">
        <span style={{
          color: fps >= 50 ? 'var(--color-success)' : fps >= 30 ? 'var(--color-warning)' : 'var(--color-error)'
        }}>
          {fps} FPS
        </span>
      </div>

      <div className="bottombar__divider" />

      {/* CesiumJS credit */}
      <span style={{ color: 'var(--color-text-muted)', fontSize: 10 }}>
        Powered by CesiumJS
      </span>
    </footer>
  )
}
