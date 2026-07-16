import { useRef } from "react";
import { Line } from "react-chartjs-2";

// chartjs-plugin-zoom is registered globally in chartSetup.js. This wrapper merges wheel/pinch zoom
// + drag panning (x-axis, matching the 2+-year daily time series) into whatever options a chart
// already passes, and renders a "Reset zoom" button wired to the chart instance's resetZoom().
// Tooltips are untouched -- the zoom plugin doesn't interfere with hover interaction.
const ZOOM_CONFIG = {
  zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: "x" },
  pan: { enabled: true, mode: "x" },
};

export default function ZoomableLine({ data, options = {}, containerClassName }) {
  const chartRef = useRef(null);

  const merged = {
    ...options,
    plugins: {
      ...(options.plugins || {}),
      zoom: { ...(options.plugins?.zoom || {}), ...ZOOM_CONFIG },
    },
  };

  const chart = <Line ref={chartRef} data={data} options={merged} />;

  return (
    <div className="zoomable-chart">
      <div className="chart-toolbar">
        <button type="button" className="btn-reset-zoom" onClick={() => chartRef.current?.resetZoom()}>
          Reset zoom
        </button>
      </div>
      {containerClassName ? <div className={containerClassName}>{chart}</div> : chart}
    </div>
  );
}
