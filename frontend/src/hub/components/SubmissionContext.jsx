import { useState } from 'react';
import '../styles/SubmissionContext.css';
import minusIcon from '../../assets/images/iconoir_minus.svg';
import checkmarkIcon from '../../assets/images/Icons=Checkmark.svg';

const AGENCY_OPTIONS = [
  { value: 'accept',  label: 'Accept suggested classification' },
  { value: 'reject',  label: 'Reject suggested classification' },
  { value: 'manual',  label: 'Request manual review' },
];

export default function SubmissionContext({ isOpen, onClose, onSubmit, fileName }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    projectName:    '',
    description:    '',
    dataDomain:     '',
    coverageStart:  '',
    coverageEnd:    '',
    ongoing:        false,
    agencyResponse: 'accept',
    permissionAck:  false,
  });
  const [errors, setErrors] = useState({});

  if (!isOpen) return null;

  const set = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors(prev => ({ ...prev, [field]: false }));
  };

  const validateStep1 = () => {
    const e = {
      projectName:   !form.projectName.trim(),
      description:   !form.description.trim(),
      dataDomain:    !form.dataDomain.trim(),
      coverageStart: !form.coverageStart,
    };
    setErrors(e);
    return !Object.values(e).some(Boolean);
  };

  const validateStep2 = () => {
    const e = { permissionAck: !form.permissionAck };
    setErrors(e);
    return !Object.values(e).some(Boolean);
  };

  const handleNext = () => { if (validateStep1()) setStep(2); };
  const handleSubmit = () => { if (validateStep2()) onSubmit(form); };

  return (
    <div className="sc-overlay" onClick={onClose}>
      <div className="sc-modal" onClick={e => e.stopPropagation()}>

        {/* Title */}
        <h2 className="sc-title">
          {step === 1 ? 'Submission Context' : 'AI/ML Training Intent'}
        </h2>

        {/* Step indicator */}
        <div className="sc-steps">
          {/* Step 1: active on step 1, done on step 2 */}
          <div className={`sc-step ${step === 1 ? 'active' : 'done'}`}>
            <div className="sc-step-dot">
              <img
                src={step === 1 ? minusIcon : checkmarkIcon}
                alt=""
                className={step === 1 ? 'sc-step-icon' : 'sc-step-icon--checkmark'}
              />
            </div>
            <span className="sc-step-label">Submission Context</span>
          </div>
          <div className="sc-step-line" />
          {/* Step 2: inactive on step 1, active on step 2 */}
          <div className={`sc-step ${step === 2 ? 'active' : 'inactive'}`}>
            <div className="sc-step-dot">
              {step === 2 && <img src={minusIcon} alt="" className="sc-step-icon" />}
            </div>
            <span className="sc-step-label">
              {step === 1 ? 'AI/ML Training Intent' : 'Classification'}
            </span>
          </div>
        </div>

        {/* ── Step 1 ── */}
        {step === 1 && (
          <div className="sc-body">
            <div className="sc-field">
              <label className="sc-label">Project Name <span className="sc-required">*</span></label>
              <input
                className={`sc-input${errors.projectName ? ' sc-input--error' : ''}`}
                placeholder="Housing"
                value={form.projectName}
                onChange={e => set('projectName', e.target.value)}
              />
              {errors.projectName && <span className="sc-error-msg">This field is required</span>}
            </div>

            <div className="sc-field">
              <label className="sc-label">Submission Description <span className="sc-required">*</span></label>
              <textarea
                className={`sc-textarea${errors.description ? ' sc-input--error' : ''}`}
                placeholder="This is housing"
                rows={3}
                value={form.description}
                onChange={e => set('description', e.target.value)}
              />
              {errors.description && <span className="sc-error-msg">This field is required</span>}
            </div>

            <div className="sc-field">
              <label className="sc-label">Data Domain <span className="sc-required">*</span></label>
              <input
                className={`sc-input${errors.dataDomain ? ' sc-input--error' : ''}`}
                placeholder="BFI"
                value={form.dataDomain}
                onChange={e => set('dataDomain', e.target.value)}
              />
              {errors.dataDomain && <span className="sc-error-msg">This field is required</span>}
            </div>

            <div className="sc-dates">
              <div className="sc-field">
                <label className="sc-label">Temporal Coverage Start <span className="sc-required">*</span></label>
                <div className="sc-date-wrap">
                  <input
                    className={`sc-input${errors.coverageStart ? ' sc-input--error' : ''}`}
                    type="date"
                    value={form.coverageStart}
                    onChange={e => set('coverageStart', e.target.value)}
                  />
                  <svg className="sc-date-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                  </svg>
                </div>
                {errors.coverageStart && <span className="sc-error-msg">This field is required</span>}
              </div>
              <div className="sc-field">
                <label className="sc-label">End Date</label>
                <div className="sc-date-wrap">
                  <input
                    className="sc-input"
                    type="date"
                    value={form.coverageEnd}
                    onChange={e => set('coverageEnd', e.target.value)}
                  />
                  <svg className="sc-date-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                  </svg>
                </div>
              </div>
            </div>

            <label className="sc-checkbox-label">
              <input
                type="checkbox"
                className="sc-checkbox"
                checked={form.ongoing}
                onChange={e => set('ongoing', e.target.checked)}
              />
              <span>Ongoing/ continuously updated</span>
            </label>

            <button className="sc-next-btn" onClick={handleNext}>
              Next
            </button>
          </div>
        )}

        {/* ── Step 2 ── */}
        {step === 2 && (
          <div className="sc-body">
            <div className="sc-field">
              <label className="sc-label">Agency Response</label>
              <div className="sc-select-wrap">
                <select
                  className="sc-select"
                  value={form.agencyResponse}
                  onChange={e => set('agencyResponse', e.target.value)}
                >
                  {AGENCY_OPTIONS.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
                <svg className="sc-select-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </div>
            </div>

            <div className="sc-classification-card">
              <p className="sc-classification-title">
                Suggested Classification: Tier 2 — Internal Operational
              </p>
              <p className="sc-classification-desc">
                Default classification applied based on ambiguous sensitivity indicators.
              </p>
            </div>

            <div className="sc-field">
              <label className="sc-label">Permissions Acknowledgement <span className="sc-required">*</span></label>
              <label className={`sc-checkbox-label sc-ack-row${errors.permissionAck ? ' sc-ack-row--error' : ''}`}>
                <input
                  type="checkbox"
                  className="sc-checkbox"
                  checked={form.permissionAck}
                  onChange={e => set('permissionAck', e.target.checked)}
                />
                <span>BFI may use this dataset for AI or machine learning model training.</span>
              </label>
              {errors.permissionAck && <span className="sc-error-msg">You must acknowledge this to proceed</span>}
            </div>

            <div className="sc-step2-actions">
              <button className="sc-back-btn" onClick={() => setStep(1)}>Back</button>
              <button className="sc-submit-btn" onClick={handleSubmit}>Submit</button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
