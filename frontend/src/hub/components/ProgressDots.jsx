import { useLocation } from 'react-router-dom';
import '../styles/ProgressDots.css';
import minus from '../../assets/images/iconoir_minus.svg'
import check from '../../assets/images/Icon=check.svg'

export default function ProgressDots() {
  const location = useLocation();
  const steps = ['/upload', '/edit', '/success'];
  const labels = ['Upload', 'Preview', 'Finalize'];

  const currentIndex = steps.indexOf(location.pathname);

  return (
    <div className="progress-dots-container">
      {steps.map((_, stepIndex) => (
        <div className="step-content-container" key={stepIndex}>
          <div className="step-wrapper">
            <div className={`step-dot ${stepIndex === currentIndex ? 'current' : ''} ${stepIndex < currentIndex ? 'completed' : ''}`}>
              {stepIndex < currentIndex ? <img src={ check } alt="✔" /> : ''}
              {stepIndex === currentIndex ? <img src={ minus } alt="-" /> : ''}
            </div>
            <div className="step-label">{labels[stepIndex]}</div>
          </div>
          
          {/* Conditional rendering for the connector */}
          {stepIndex < steps.length - 1 && (
            <div className="step-connector">
              {stepIndex < currentIndex ? (
                // This renders the solid line
                <div className="completed-connector" />
              ) : (
                // This renders the small dots for uncompleted steps
                Array.from({ length: 8 }).map((_, i) => (
                  <span key={i} className="small-dot" />
                ))
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}