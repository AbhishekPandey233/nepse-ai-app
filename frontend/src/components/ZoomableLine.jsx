import { useRef } from "react";
import { Line } from "react-chartjs-2";

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
