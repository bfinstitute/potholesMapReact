import { useNavigate } from 'react-router-dom';
import AppLayout from './AppLayout';
import '../styles/UploadPage.css';

export default function SuccessPage() {
  const navigate = useNavigate();

  return (
    <AppLayout>
      <div className="sources-page" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <div className="success-modal" style={{ position: 'relative', boxShadow: '0 4px 24px rgba(0,0,0,0.10)' }}>
          <h2 className="success-modal-title">Your dataset has been submitted</h2>
          <p className="success-modal-body">
            BFI has received your files and will begin the intake process shortly. You'll be notified if we need any clarification. In the meantime, you can track the status of this submission from your dashboard.
          </p>
          <button className="success-modal-btn" onClick={() => navigate('/queue')}>
            Back To Dashboard
          </button>
        </div>
      </div>
    </AppLayout>
  );
}
