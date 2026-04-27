import { useState } from 'react';
import '../styles/GiveContextDrawer.css';
import apiService from '../../services/api';

const GOVERNANCE_TAGS = [
  'Public Works',
  'Infrastructure',
  'Parks and Rec',
  'Transportation',
  'Utilities',
  'Housing',
  'Custom',
];

export default function GiveContextDrawer({ isOpen, onClose, onSubmit, fileName }) {
  const [formData, setFormData] = useState({
    batchName: '',
    description: '',
    datasetType: 'full',
    governanceTags: [],
    owner: '',
    missingValues: '',
    governanceLevel: 'public',
    permissionAck: false,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const set = (field, value) => setFormData(prev => ({ ...prev, [field]: value }));

  const toggleTag = (tag) => {
    setFormData(prev => ({
      ...prev,
      governanceTags: prev.governanceTags.includes(tag)
        ? prev.governanceTags.filter(t => t !== tag)
        : [...prev.governanceTags, tag],
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.permissionAck) return;
    setIsSubmitting(true);
    try {
      await apiService.submitFeedback({
        batchName: formData.batchName,
        purpose: formData.description,
        datasetType: formData.datasetType,
        governanceTags: formData.governanceTags,
        stakeholders: formData.owner,
        incorrectFields: formData.missingValues,
        governanceLevel: formData.governanceLevel,
      });
      onSubmit();
    } catch (err) {
      console.error('Context submission failed:', err);
      onSubmit();
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="drawer-header">
          <div>
            <h2 className="drawer-title">Give Buffi more context</h2>
            <p className="drawer-subtitle">
              {fileName ? `${fileName} added.` : '1 file added.'} Takes 5 seconds.
            </p>
          </div>
          <button className="drawer-close-btn" onClick={onClose}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* Form */}
        <form className="drawer-form" onSubmit={handleSubmit}>
          {/* Batch Name */}
          <div className="drawer-field">
            <label className="drawer-label">Batch Name</label>
            <input
              className="drawer-input"
              type="text"
              placeholder="Infrastructure Assets"
              value={formData.batchName}
              onChange={(e) => set('batchName', e.target.value)}
            />
          </div>

          {/* Description */}
          <div className="drawer-field">
            <label className="drawer-label">Describe this dataset and its purpose</label>
            <div className="drawer-textarea-wrap">
              <textarea
                className="drawer-textarea"
                placeholder="Write message here..."
                value={formData.description}
                onChange={(e) => set('description', e.target.value)}
                rows={3}
              />
              {formData.description && (
                <button type="button" className="drawer-clear-btn" onClick={() => set('description', '')}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              )}
            </div>
          </div>

          {/* Dataset Type */}
          <div className="drawer-field">
            <label className="drawer-label">Dataset Type</label>
            <div className="drawer-radio-group">
              <label className="drawer-radio-item">
                <input type="radio" name="datasetType" value="full" checked={formData.datasetType === 'full'} onChange={() => set('datasetType', 'full')} />
                <span className="drawer-radio-label">Full Dataset</span>
                <span className="drawer-radio-hint">Flag missing required fields</span>
              </label>
              <label className="drawer-radio-item">
                <input type="radio" name="datasetType" value="partial" checked={formData.datasetType === 'partial'} onChange={() => set('datasetType', 'partial')} />
                <span className="drawer-radio-label">Partial Dataset</span>
                <span className="drawer-radio-hint">Only flag this partial dataset</span>
              </label>
            </div>
          </div>

          {/* Governance Tags */}
          <div className="drawer-field">
            <label className="drawer-label">Governance</label>
            <div className="drawer-tags">
              {GOVERNANCE_TAGS.map(tag => (
                <button
                  key={tag}
                  type="button"
                  className={`drawer-tag${formData.governanceTags.includes(tag) ? ' selected' : ''}`}
                  onClick={() => toggleTag(tag)}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>

          {/* Owner */}
          <div className="drawer-field">
            <label className="drawer-label">Who owns this data?</label>
            <div className="drawer-input-wrap">
              <input
                className="drawer-input"
                type="text"
                placeholder="Write message here..."
                value={formData.owner}
                onChange={(e) => set('owner', e.target.value)}
              />
              {formData.owner && (
                <button type="button" className="drawer-input-clear" onClick={() => set('owner', '')}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              )}
            </div>
          </div>

          {/* Missing Values */}
          <div className="drawer-field">
            <label className="drawer-label">Are there any missing values or incomplete fields?</label>
            <div className="drawer-textarea-wrap">
              <textarea
                className="drawer-textarea"
                placeholder="Write message here..."
                value={formData.missingValues}
                onChange={(e) => set('missingValues', e.target.value)}
                rows={3}
              />
              {formData.missingValues && (
                <button type="button" className="drawer-clear-btn" onClick={() => set('missingValues', '')}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              )}
            </div>
          </div>

          {/* Assign Governance */}
          <div className="drawer-field">
            <label className="drawer-label">Assign Governance to this data</label>
            <div className="drawer-radio-group">
              <label className="drawer-radio-item">
                <input type="radio" name="govLevel" value="public" checked={formData.governanceLevel === 'public'} onChange={() => set('governanceLevel', 'public')} />
                <span className="drawer-radio-label">Public</span>
                <span className="drawer-radio-hint">Flag any government...</span>
              </label>
              <label className="drawer-radio-item">
                <input type="radio" name="govLevel" value="internal" checked={formData.governanceLevel === 'internal'} onChange={() => set('governanceLevel', 'internal')} />
                <span className="drawer-radio-label">Internal</span>
                <span className="drawer-radio-hint">Only flag internal...</span>
              </label>
              <label className="drawer-radio-item">
                <input type="radio" name="govLevel" value="restricted" checked={formData.governanceLevel === 'restricted'} onChange={() => set('governanceLevel', 'restricted')} />
                <span className="drawer-radio-label">Restricted</span>
                <span className="drawer-radio-hint">Only flag restricted...</span>
              </label>
            </div>
          </div>

          {/* Permission Acknowledgement */}
          <div className="drawer-field drawer-ack">
            <label className="drawer-ack-label">
              <input
                type="checkbox"
                checked={formData.permissionAck}
                onChange={(e) => set('permissionAck', e.target.checked)}
              />
              <span>I consent to Better Futures Institute accessing this data the way I have described.</span>
            </label>
          </div>

          <button
            type="submit"
            className="drawer-submit-btn"
            disabled={isSubmitting || !formData.permissionAck}
          >
            {isSubmitting ? 'Submitting...' : 'Add to Queue'}
          </button>
        </form>
      </div>
    </div>
  );
}
