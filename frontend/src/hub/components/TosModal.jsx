import '../styles/TosModal.css';

export default function TosModal({ onAgree, onCancel }) {
  return (
    <div className="tos-overlay" onClick={onCancel}>
      <div className="tos-modal" onClick={e => e.stopPropagation()}>
        <div className="tos-modal-header">
          <h2 className="tos-title">Terms of Service</h2>
          <button className="tos-close-btn" onClick={onCancel} aria-label="Close">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div className="tos-body-area">
          <p className="tos-body">
            By clicking &ldquo;agree&rdquo; you acknowledge that you have read and understood the legal requirements of each policy.
          </p>
          <a href="#scope" className="tos-link" onClick={e => e.preventDefault()}>
            Scope of Exchange
          </a>
        </div>

        <div className="tos-footer">
          <button className="tos-cancel-btn" onClick={onCancel}>
            Cancel
          </button>
          <button className="tos-agree-btn" onClick={onAgree}>
            Agree
          </button>
        </div>
      </div>
    </div>
  );
}
