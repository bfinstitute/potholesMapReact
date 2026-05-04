import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/UploadPage.css';
import { useCsv } from '../../context/CsvContext';
import AppLayout from './AppLayout';
import TosModal from './TosModal';
import apiService from '../../services/api';

const MOCK_FOLDERS = ['Housing'];

export default function UploadPage() {
  const fileInputRef = useRef(null);
  const navigate = useNavigate();
  const { setCsvData, setFileName, setCsvStats, setColumnDescriptions, setBatches } = useCsv();

  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [showTos, setShowTos] = useState(() => !localStorage.getItem('tos_agreed'));
  const [showPageMenu, setShowPageMenu] = useState(false);

  const hasFiles = uploadedFiles.length > 0;

  const handleFiles = async (fileList) => {
    const files = Array.from(fileList).filter(f => f.type === 'text/csv');
    if (files.length === 0) {
      setUploadError('Please upload valid CSV file(s).');
      return;
    }
    setIsUploading(true);
    setUploadError('');
    try {
      const results = await Promise.all(files.map(f => apiService.uploadCSV(f)));
      const succeeded = results.map((result, i) => ({ result, file: files[i] })).filter(({ result }) => result.success);

      if (succeeded.length === 0) {
        setUploadError('Upload failed. Please try again.');
        return;
      }

      // Use the last successful upload for the active CSV context
      const last = succeeded[succeeded.length - 1];
      setFileName(last.result.filename);
      setCsvData(last.result.data);
      setCsvStats(last.result.stats);
      setColumnDescriptions(last.result.column_descriptions || {});

      const now = new Date();
      const label = now.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
        + ' ' + now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
        + ' from Sources';

      const newBatch = {
        id: Date.now(),
        label,
        files: succeeded.map(({ result, file }, i) => ({
          id: Date.now() + i + 1,
          name: result.filename,
          folder: 'Uncategorized',
          status: 'Ready',
          tier: 'Tier 2: Internal Operational',
          size: file.size < 1024 * 1024
            ? `${(file.size / 1024).toFixed(1)} KB`
            : `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
          confidence: 'High',
          issue: '',
          csvData: result.data || [],
        })),
      };

      setBatches(prev => [newBatch, ...prev]);
      navigate('/queue');
    } catch (error) {
      setUploadError(error.message || 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);
  const handleFileSelect = (e) => handleFiles(e.target.files);

  const handleTosAgree = () => {
    localStorage.setItem('tos_agreed', 'true');
    setShowTos(false);
  };

  return (
    <AppLayout>

      {/* ── Terms of Service Modal (first visit only) ── */}
      {showTos && (
        <TosModal
          onAgree={handleTosAgree}
          onCancel={() => navigate('/chat')}
        />
      )}

      <div className="sources-page">

        {/* ── Top Bar ── */}
        <div className="sources-topbar">
          <div className="sources-topbar-left">
            <div className="sources-title-wrap">
              <h1 className="sources-title" onClick={() => setShowPageMenu(v => !v)}>
                My Sources
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: showPageMenu ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </h1>
              {showPageMenu && (
                <div className="page-switcher-dropdown">
                  <button className="page-switcher-item page-switcher-item--active">My Sources</button>
                  <button className="page-switcher-item" onClick={() => navigate('/queue')}>Queue</button>
                </div>
              )}
            </div>
            <div className="sources-view-icons">
              <button className="view-icon-btn active" title="Grid view">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
                  <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
                </svg>
              </button>
              <button className="view-icon-btn" title="List view">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/>
                  <line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
                </svg>
              </button>
              <button className="view-icon-btn" title="Recent">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                </svg>
              </button>
            </div>
          </div>
          <div className="sources-topbar-right">
            <div className="storage-indicator">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
              </svg>
              <span className="storage-text">Storage</span>
              <span className="storage-used">3 GB Used</span>
            </div>
            <button className="storage-info-btn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
            </button>
            <button className="upload-btn" onClick={() => fileInputRef.current.click()}>
              Upload
            </button>
          </div>
        </div>

        {/* ── Filter Pills ── */}
        <div className="sources-filters">
          <button className="filter-pill">Type <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg></button>
          <button className="filter-pill">People <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg></button>
          <button className="filter-pill">Modified <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg></button>
        </div>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          multiple
          onChange={handleFileSelect}
          className="upload-input-hidden"
        />

        {/* ── Content: with files or empty state ── */}
        {hasFiles ? (
          <div
            className={`sources-content${isDragging ? ' dragging-overlay' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            {/* Folders section */}
            <div className="sources-section-header">
              <span className="sources-section-title">Folders</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>
            </div>
            <div className="sources-folders-grid">
              {MOCK_FOLDERS.map((folder, i) => (
                <div key={i} className="sources-folder-card">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                  </svg>
                  <span className="sources-folder-name">{folder}</span>
                  <button className="sources-more-btn">···</button>
                </div>
              ))}
            </div>

            {/* Files section */}
            <div className="sources-section-header" style={{ marginTop: 24 }}>
              <span className="sources-section-title">Files</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>
            </div>
            <div className="sources-files-grid">
              {uploadedFiles.map((file, i) => (
                <div key={i} className="sources-file-card">
                  <div className="sources-file-card-header">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                    </svg>
                    <span className="sources-file-name">{file.name}</span>
                    <span className="sources-file-badge">{file.status}</span>
                  </div>
                  <div className="sources-file-preview">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ccc" strokeWidth="1">
                      <rect x="3" y="3" width="18" height="18" rx="2"/>
                      <path d="M3 9h18M9 21V9"/>
                    </svg>
                  </div>
                </div>
              ))}
            </div>

            {isUploading && <p className="upload-status-text" style={{ marginTop: 16 }}>Uploading...</p>}
            {uploadError && <p className="upload-error-text" style={{ marginTop: 8 }}>{uploadError}</p>}
          </div>
        ) : (
          /* ── Drop Zone / Empty State ── */
          <div
            className={`sources-dropzone${isDragging ? ' dragging' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current.click()}
            style={{ cursor: 'pointer' }}
          >
            {isDragging ? (
              <div className="dropzone-drag-active">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
                  <polyline points="16 16 12 12 8 16"/>
                  <line x1="12" y1="12" x2="12" y2="21"/>
                </svg>
                <h2 className="dropzone-drag-title">A place for all your files</h2>
                <p className="dropzone-drag-sub">Drop your CSV file to upload it to Sources</p>
                <button className="dropzone-drag-btn" onClick={() => fileInputRef.current.click()}>
                  Or click to select a file
                </button>
              </div>
            ) : (
              <div className="dropzone-empty-state">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
                  <ellipse cx="12" cy="5" rx="9" ry="3"/>
                  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                </svg>
                <h2 className="dropzone-empty-title">Build your sources</h2>
                <p className="dropzone-empty-sub">Click here or drag and drop a CSV file to upload</p>
                {isUploading && <p className="upload-status-text">Uploading...</p>}
                {uploadError && <p className="upload-error-text">{uploadError}</p>}
              </div>
            )}
          </div>
        )}
      </div>

    </AppLayout>
  );
}
