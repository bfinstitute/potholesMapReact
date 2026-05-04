import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from './AppLayout';
import ResolveView from './ResolveView';
import { useCsv } from '../../context/CsvContext';
import '../styles/ClarificationPage.css';

const BUFFI_DESCRIPTION = 'Files in this dataset cover the distribution of residential, commercial, and industrial land use across San Antonio, along with data on where housing supply gaps are most severe.';

const MOCK_FOLDERS = ['SA Land Use And Housing'];

const ChevronDown = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="6 9 12 15 18 9"/>
  </svg>
);

export default function ClarificationPage() {
  const navigate = useNavigate();
  const { batchFiles, setBatchFiles } = useCsv();

  const [viewMode, setViewMode]         = useState('grid');
  const [typeFilter, setTypeFilter]     = useState('all');
  const [sortFilter, setSortFilter]     = useState('default');
  const [openDropdown, setOpenDropdown] = useState(null);
  const [resolveFile, setResolveFile]   = useState(null);
  const [allResolved, setAllResolved]   = useState(false);
  const [submitDone, setSubmitDone]     = useState(false);

  // Derive hasError from shared status field
  const files = batchFiles.map(f => ({ ...f, hasError: f.status === 'Error' }));
  const errorCount = files.filter(f => f.hasError).length;

  const toggleDropdown = (name) => setOpenDropdown(prev => prev === name ? null : name);

  const resolveOne = (id) => {
    setBatchFiles(prev => prev.map(f => f.id === id ? { ...f, status: 'Ready' } : f));
  };

  const resolveAll = () => {
    setBatchFiles(prev => prev.map(f => ({ ...f, status: 'Ready' })));
    setAllResolved(true);
  };

  const getFilteredFiles = (list) => {
    let result = [...list];
    if (typeFilter === 'error') result = result.filter(f => f.hasError);
    if (typeFilter === 'ok')    result = result.filter(f => !f.hasError);
    if (sortFilter === 'az') result.sort((a, b) => a.name.localeCompare(b.name));
    if (sortFilter === 'za') result.sort((a, b) => b.name.localeCompare(a.name));
    return result;
  };

  const displayedFiles = getFilteredFiles(files);

  return (
    <AppLayout>
      <div className="pending-page" onClick={() => openDropdown && setOpenDropdown(null)}>

        {/* ── Breadcrumb + top controls ── */}
        <div className="pending-topbar">
          <div className="pending-topbar-left">
            <h1 className="pending-breadcrumb">
              <span className="pending-breadcrumb-link" onClick={() => navigate('/queue')}>Submissions</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="9 18 15 12 9 6"/>
              </svg>
              <span className="pending-breadcrumb-current">Pending Review</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </h1>
            <div className="sources-view-icons">
              <button className={`view-icon-btn${viewMode === 'grid' ? ' active' : ''}`} title="Grid view" onClick={() => setViewMode('grid')}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
                  <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
                </svg>
              </button>
              <button className={`view-icon-btn${viewMode === 'list' ? ' active' : ''}`} title="List view" onClick={() => setViewMode('list')}>
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
            <button className="upload-btn" onClick={() => navigate('/sources')}>Upload</button>
          </div>
        </div>

        {/* ── Filter Pills ── */}
        <div className="sources-filters" onClick={e => e.stopPropagation()}>

          {/* Type filter */}
          <div className="filter-pill-wrap">
            <button
              className={`filter-pill${typeFilter !== 'all' ? ' filter-active' : ''}`}
              onClick={() => toggleDropdown('type')}
            >
              {typeFilter === 'all' ? 'Type' : typeFilter === 'error' ? 'Type: Error' : 'Type: OK'}
              <ChevronDown />
            </button>
            {openDropdown === 'type' && (
              <div className="filter-dropdown">
                <button className={`filter-dropdown-item${typeFilter === 'all'   ? ' selected' : ''}`} onClick={() => { setTypeFilter('all');   setOpenDropdown(null); }}>All</button>
                <button className={`filter-dropdown-item${typeFilter === 'error' ? ' selected' : ''}`} onClick={() => { setTypeFilter('error'); setOpenDropdown(null); }}>Error</button>
                <button className={`filter-dropdown-item${typeFilter === 'ok'    ? ' selected' : ''}`} onClick={() => { setTypeFilter('ok');    setOpenDropdown(null); }}>OK</button>
              </div>
            )}
          </div>

          {/* People filter (static labels for now) */}
          <div className="filter-pill-wrap">
            <button className="filter-pill" onClick={() => toggleDropdown('people')}>
              People <ChevronDown />
            </button>
            {openDropdown === 'people' && (
              <div className="filter-dropdown">
                <button className="filter-dropdown-item selected" onClick={() => setOpenDropdown(null)}>All People</button>
                <button className="filter-dropdown-item" onClick={() => setOpenDropdown(null)}>Me</button>
              </div>
            )}
          </div>

          {/* Modified / Sort filter */}
          <div className="filter-pill-wrap">
            <button
              className={`filter-pill${sortFilter !== 'default' ? ' filter-active' : ''}`}
              onClick={() => toggleDropdown('modified')}
            >
              {sortFilter === 'default' ? 'Modified' : sortFilter === 'az' ? 'Name A–Z' : 'Name Z–A'}
              <ChevronDown />
            </button>
            {openDropdown === 'modified' && (
              <div className="filter-dropdown">
                <button className={`filter-dropdown-item${sortFilter === 'default' ? ' selected' : ''}`} onClick={() => { setSortFilter('default'); setOpenDropdown(null); }}>Default</button>
                <button className={`filter-dropdown-item${sortFilter === 'az'      ? ' selected' : ''}`} onClick={() => { setSortFilter('az');      setOpenDropdown(null); }}>Name A–Z</button>
                <button className={`filter-dropdown-item${sortFilter === 'za'      ? ' selected' : ''}`} onClick={() => { setSortFilter('za');      setOpenDropdown(null); }}>Name Z–A</button>
              </div>
            )}
          </div>

        </div>

        {/* ── Buffi AI Banner ── */}
        <div className="buffi-banner">
          <div className="buffi-banner-body">
            <span className="buffi-banner-label">Buffi V.01</span>
            <p className="buffi-banner-desc">{BUFFI_DESCRIPTION}</p>
            {errorCount > 0 ? (
              <>
                <p className="buffi-banner-warning"><strong>{errorCount} files need your attention</strong></p>
                <p className="buffi-banner-sub">{errorCount} issues found — resolve them before this dataset can be finalized.</p>
              </>
            ) : (
              <p className="buffi-banner-warning"><strong>All issues resolved</strong></p>
            )}
          </div>
          <div className="buffi-banner-actions">
            <button className="buffi-btn-context">Dataset Context</button>
            {errorCount > 0 && (
              <button className="buffi-btn-outline" onClick={resolveAll}>Resolve All Issues</button>
            )}
            <button className="buffi-btn-primary">{files.length} sources in batch</button>
          </div>
        </div>

        {viewMode === 'grid' ? (
          <>
            {/* ── Folders section (card view only) ── */}
            <div className="sources-section-header">
              <span className="sources-section-title">Folders</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>
            </div>
            <div className="sources-folders-grid" style={{ marginBottom: 24 }}>
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

            {/* ── Files section (card view only) ── */}
            <div className="sources-section-header">
              <span className="sources-section-title">Files</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>
            </div>

            {displayedFiles.length === 0 ? (
              <p className="queue-no-results">No files match the current filters.</p>
            ) : (
              <div className="pending-files-grid">
                {displayedFiles.map((file) => (
                  <div
                    key={file.id}
                    className={`pending-file-card${file.hasError ? ' has-error' : ''}`}
                    onClick={() => file.hasError && setResolveFile(file)}
                    title={file.hasError ? 'Click to resolve issue' : ''}
                  >
                    <div className="pending-file-card-header">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                      </svg>
                      <span className="pending-file-name">{file.name}</span>
                      {file.hasError && <span className="pending-file-error-badge">Error</span>}
                    </div>
                    <div className="pending-file-preview">
                      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ccc" strokeWidth="1">
                        <rect x="3" y="3" width="18" height="18" rx="2"/>
                        <path d="M3 9h18M9 21V9"/>
                      </svg>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          /* ── List view: batch date header + table (same layout as Queue page) ── */
          <div className="queue-batch">
            <div className="queue-batch-header">
              <span className="queue-batch-title">April 2nd 2025 3:51 PM Queue</span>
              <span className="queue-batch-folder-tag">
                Housing
                <button className="queue-batch-folder-remove">×</button>
              </span>
            </div>

            {displayedFiles.length === 0 ? (
              <p className="queue-no-results">No files match the current filters.</p>
            ) : (
              <table className="queue-table">
                <thead>
                  <tr>
                    <th>Name <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="18 15 12 9 6 15"/></svg></th>
                    <th>Folder</th>
                    <th>Status</th>
                    <th>Tier</th>
                    <th>File Size</th>
                    <th>AI Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {displayedFiles.map((file) => (
                    <tr
                      key={file.id}
                      className="queue-row"
                      onClick={() => file.hasError && setResolveFile(file)}
                    >
                      <td>
                        <div className="queue-col-name">
                          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                          </svg>
                          {file.name}
                        </div>
                      </td>
                      <td className="queue-col-folder">{file.folder}</td>
                      <td><span className={`queue-status-badge ${file.hasError ? 'error' : 'ready'}`}>{file.hasError ? 'Error' : 'Ready'}</span></td>
                      <td className="queue-col-tier">{file.tier}</td>
                      <td className="queue-col-size">{file.size}</td>
                      <td><span className={`queue-confidence ${file.confidence === 'Low' ? 'low' : 'high'}`}>{file.confidence}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

      </div>

      {/* ── Full Resolve View (outside scroll container so position:fixed works) ── */}
      {resolveFile && (
        <ResolveView
          file={resolveFile}
          onClose={() => setResolveFile(null)}
          onSubmit={(updatedRows) => {
            const stillHasErrors = updatedRows.some(r => r.hasError);
            if (!stillHasErrors) resolveOne(resolveFile.id);
            setResolveFile(null);
            if (!stillHasErrors) setSubmitDone(true);
          }}
        />
      )}

      {/* ── Submit Done / All Resolved confirmation ── */}
      {(allResolved || submitDone) && (
        <div className="resolve-overlay" onClick={() => { setAllResolved(false); setSubmitDone(false); }}>
          <div className="resolve-modal" onClick={e => e.stopPropagation()}>
            <h2 className="resolve-modal-title">
              {allResolved ? 'All Issues Resolved' : 'File Submitted'}
            </h2>
            <p className="resolve-modal-filename" style={{ marginTop: 8 }}>
              {allResolved
                ? 'All files in this dataset have been marked as resolved and are ready for submission.'
                : 'The file changes have been saved and the issue has been resolved.'}
            </p>
            <div className="resolve-modal-actions">
              <button className="resolve-confirm-btn" onClick={() => { setAllResolved(false); setSubmitDone(false); navigate('/queue'); }}>
                Back to Queue
              </button>
            </div>
          </div>
        </div>
      )}

    </AppLayout>
  );
}
