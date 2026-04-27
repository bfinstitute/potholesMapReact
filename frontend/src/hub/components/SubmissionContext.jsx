import { useState } from 'react';
import '../styles/SubmissionContext.css';

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

  if (!isOpen) return null;

  const set = (field, value) => setForm(prev => ({ ...prev, [field]: value }));

  const handleSubmit = () => onSubmit(form);

  return (
    <div className="sc-overlay" onClick={onClose}>
      <div className="sc-modal" onClick={e => e.stopPropagation()}>

        {/* Title */}
        <h2 className="sc-title">
          {step === 1 ? 'Submission Context' : 'AI/ML Training Intent'}
        </h2>

        {/* Step indicator */}
        <div className="sc-steps">
          <div className={`sc-step ${step === 1 ? 'active' : 'done'}`}>
            <div className="sc-step-dot">
              {step > 1 && (
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              )}
            </div>
            <span className="sc-step-label">Submission Context</span>
          </div>
          <div className="sc-step-line" />
          <div className={`sc-step ${step === 2 ? 'active' : step > 2 ? 'done' : 'inactive'}`}>
            <div className="sc-step-dot" />
            <span className="sc-step-label">
              {step === 1 ? 'AI/ML Training Intent' : 'Classification'}
            </span>
          </div>
        </div>

        {/* ── Step 1 ── */}
        {step === 1 && (
          <div className="sc-body">
            <div className="sc-field">
              <label className="sc-label">Project Name</label>
              <input
                className="sc-input"
                placeholder="Housing"
                value={form.projectName}
                onChange={e => set('projectName', e.target.value)}
              />
            </div>

            <div className="sc-field">
              <label className="sc-label">Submission Description</label>
              <textarea
                className="sc-textarea"
                placeholder="This is housing"
                rows={3}
                value={form.description}
                onChange={e => set('description', e.target.value)}
              />
            </div>

            <div className="sc-field">
              <label className="sc-label">Data Domain</label>
              <input
                className="sc-input"
                placeholder="BFI"
                value={form.dataDomain}
                onChange={e => set('dataDomain', e.target.value)}
              />
            </div>

            <div className="sc-dates">
              <div className="sc-field">
                <label className="sc-label">Temporal Coverage Start</label>
                <div className="sc-date-wrap">
                  <input
                    className="sc-input"
                    type="date"
                    value={form.coverageStart}
                    onChange={e => set('coverageStart', e.target.value)}
                  />
                  <svg className="sc-date-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                  </svg>
                </div>
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

            <button className="sc-next-btn" onClick={() => setStep(2)}>
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
              <label className="sc-label">Permissions Acknowledgement</label>
              <label className="sc-checkbox-label sc-ack-row">
                <input
                  type="checkbox"
                  className="sc-checkbox"
                  checked={form.permissionAck}
                  onChange={e => set('permissionAck', e.target.checked)}
                />
                <span>BFI may use this dataset for AI or machine learning model training.</span>
              </label>
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
