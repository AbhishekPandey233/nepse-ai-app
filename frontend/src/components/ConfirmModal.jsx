export default function ConfirmModal({ message, onConfirm, onCancel }) {
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-dialog card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-icon">?</div>
        <p>{message}</p>
        <div className="button-group">
          <button type="button" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="btn-primary" onClick={onConfirm}>
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}
