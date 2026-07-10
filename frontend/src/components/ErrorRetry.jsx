export default function ErrorRetry({ message, onRetry }) {
  return (
    <div className="error-box">
      <p className="error">{message}</p>
      <button type="button" className="btn-primary" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
}
