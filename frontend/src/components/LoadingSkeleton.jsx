export default function LoadingSkeleton() {
  return (
    <div className="skeleton" aria-busy="true" aria-label="Loading">
      <div className="skeleton-line" style={{ width: "55%" }} />
      <div className="skeleton-line" style={{ width: "90%" }} />
      <div className="skeleton-line" style={{ width: "75%" }} />
      <div className="skeleton-line" style={{ width: "40%" }} />
    </div>
  );
}
