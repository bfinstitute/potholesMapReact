import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import AppLayout from './AppLayout';
import SubmissionContext from './SubmissionContext';
import ResolveView from './ResolveView';
import TosModal from './TosModal';
import { useCsv } from '../../context/CsvContext';
import '../styles/SubmissionsPage.css';

const DEFAULT_BUFFI_DESCRIPTION = 'Upload CSV files from Sources to begin the intake process. Buffi AI will review each file and flag any issues that need your attention before submission.';
const FOLDERS = ['Housing', 'Safety', 'Infrastructure'];
const CARD_FOLDERS = ['SA Land Use And Housing'];

const formatBytes = (bytes) => {
  if (!bytes) return 'N/A';
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const formatBatchDate = () => {
  const now = new Date();
  return now.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
    + ' ' + now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
    + ' from Sources';
};

const ChevronDown = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="6 9 12 15 18 9"/>
  </svg>
);

export default function SubmissionsPage() {
  const navigate   = useNavigate();
  const location   = useLocation();
  const routeState = location.state || {};
  const { batches, setBatches, csvData } = useCsv();

  const [viewMode, setViewMode]           = useState('list');
  const [typeFilter, setTypeFilter]       = useState('all');
  const [folderFilter, setFolderFilter]   = useState('all');
  const [sortFilter, setSortFilter]       = useState('default');
  const [batchSortState, setBatchSortState] = useState({});
  const [openDropdown, setOpenDropdown]   = useState(null);
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [contextOpen, setContextOpen]     = useState(!!routeState.showContext);
  const [contextFileName]                 = useState(routeState.fileName || '');
  const [resolveFile, setResolveFile]     = useState(null);
  const [pendingSubmit, setPendingSubmit] = useState(null); // { file, updatedRows }
  const [allResolved, setAllResolved]     = useState(false);
  const [submitDone, setSubmitDone]       = useState(false);
  const [showTos, setShowTos]             = useState(() => !localStorage.getItem('tos_agreed'));
  const [showPageMenu, setShowPageMenu]   = useState(false);

  const handleTosAgree = () => {
    localStorage.setItem('tos_agreed', 'true');
    setShowTos(false);
  };

  const toggleDropdown = (name) => setOpenDropdown(prev => prev === name ? null : name);

  // All files across all batches, with hasError derived from status
  const allFiles = batches.flatMap(b => b.files).map(f => ({ ...f, hasError: f.status === 'Error' }));
  const errorCount = allFiles.filter(f => f.hasError).length;
  const readyCount = allFiles.filter(f => !f.hasError).length;

  const resolveOne = (id) => {
    setBatches(prev => prev.map(b => ({
      ...b,
      files: b.files.map(f => f.id === id ? { ...f, status: 'Ready' } : f),
    })));
  };

  const resolveAll = () => {
    setBatches(prev => prev.map(b => ({
      ...b,
      files: b.files.map(f => ({ ...f, status: 'Ready' })),
    })));
    setAllResolved(true);
  };

  const parseSize = (s) => {
    if (!s || s === 'N/A') return 0;
    const num = parseFloat(s);
    if (s.includes('MB')) return num * 1024 * 1024;
    if (s.includes('KB')) return num * 1024;
    return num;
  };

  const handleColSort = (batchId, col) => {
    setBatchSortState(prev => {
      const cur = prev[batchId] || { col: null, dir: 'asc' };
      return {
        ...prev,
        [batchId]: {
          col,
          dir: cur.col === col && cur.dir === 'asc' ? 'desc' : 'asc',
        },
      };
    });
  };

  const getFilteredFiles = (files, batchId) => {
    let result = [...files];
    if (typeFilter   !== 'all') result = result.filter(f => f.status.toLowerCase() === typeFilter);
    if (folderFilter !== 'all') result = result.filter(f => f.folder === folderFilter);
    const { col: sortCol, dir: sortDir } = batchSortState[batchId] || { col: null, dir: 'asc' };
    if (sortCol) {
      result.sort((a, b) => {
        let aVal = a[sortCol];
        let bVal = b[sortCol];
        if (sortCol === 'size') {
          aVal = parseSize(aVal);
          bVal = parseSize(bVal);
          return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
        }
        aVal = String(aVal || '').toLowerCase();
        bVal = String(bVal || '').toLowerCase();
        const cmp = aVal.localeCompare(bVal);
        return sortDir === 'asc' ? cmp : -cmp;
      });
    } else {
      if (sortFilter === 'az') result.sort((a, b) => a.name.localeCompare(b.name));
      if (sortFilter === 'za') result.sort((a, b) => b.name.localeCompare(a.name));
    }
    return result;
  };

  // For grid view: all files across batches (filtered, no per-batch sort)
  const allFilteredFiles = getFilteredFiles(allFiles, '__grid__');

  const FileIcon = () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
    </svg>
  );

  return (
    <AppLayout>
      {showTos && (
        <TosModal
          onAgree={handleTosAgree}
          onCancel={() => navigate('/chat')}
        />
      )}
      <div className="queue-page" onClick={() => openDropdown && setOpenDropdown(null)}>

        {/* ── Top Bar ── */}
        <div className="sources-topbar">
          <div className="sources-topbar-left">
            <div className="sources-title-wrap">
              <h1 className="sources-title" onClick={() => setShowPageMenu(v => !v)}>
                Queue
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: showPageMenu ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </h1>
              {showPageMenu && (
                <div className="page-switcher-dropdown">
                  <button className="page-switcher-item" onClick={() => navigate('/sources')}>My Sources</button>
                  <button className="page-switcher-item page-switcher-item--active">Queue</button>
                </div>
              )}
            </div>
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
          <div className="filter-pill-wrap">
            <button className={`filter-pill${typeFilter !== 'all' ? ' filter-active' : ''}`} onClick={() => toggleDropdown('type')}>
              {typeFilter === 'all' ? 'Type' : typeFilter === 'error' ? 'Type: Error' : 'Type: Ready'}
              <ChevronDown />
            </button>
            {openDropdown === 'type' && (
              <div className="filter-dropdown">
                <button className={`filter-dropdown-item${typeFilter === 'all'   ? ' selected' : ''}`} onClick={() => { setTypeFilter('all');   setOpenDropdown(null); }}>All Types</button>
                <button className={`filter-dropdown-item${typeFilter === 'error' ? ' selected' : ''}`} onClick={() => { setTypeFilter('error'); setOpenDropdown(null); }}>Error</button>
                <button className={`filter-dropdown-item${typeFilter === 'ready' ? ' selected' : ''}`} onClick={() => { setTypeFilter('ready'); setOpenDropdown(null); }}>Ready</button>
              </div>
            )}
          </div>

          <div className="filter-pill-wrap">
            <button className={`filter-pill${folderFilter !== 'all' ? ' filter-active' : ''}`} onClick={() => toggleDropdown('people')}>
              {folderFilter === 'all' ? 'People' : folderFilter}
              <ChevronDown />
            </button>
            {openDropdown === 'people' && (
              <div className="filter-dropdown">
                <button className={`filter-dropdown-item${folderFilter === 'all' ? ' selected' : ''}`} onClick={() => { setFolderFilter('all'); setOpenDropdown(null); }}>All Folders</button>
                {FOLDERS.map(f => (
                  <button key={f} className={`filter-dropdown-item${folderFilter === f ? ' selected' : ''}`} onClick={() => { setFolderFilter(f); setOpenDropdown(null); }}>{f}</button>
                ))}
              </div>
            )}
          </div>

          <div className="filter-pill-wrap">
            <button className={`filter-pill${sortFilter !== 'default' ? ' filter-active' : ''}`} onClick={() => toggleDropdown('modified')}>
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
            <span className="buffi-banner-label">Buffi AI</span>
            <p className="buffi-banner-desc">
              {allFiles.length > 0
                ? `${allFiles.length} ${allFiles.length === 1 ? 'file' : 'files'} in queue across ${batches.length} ${batches.length === 1 ? 'batch' : 'batches'}.`
                : DEFAULT_BUFFI_DESCRIPTION}
            </p>
            {allFiles.length > 0 && (
              errorCount > 0 ? (
                <>
                  <p className="buffi-banner-warning"><strong>{errorCount} files need your attention</strong></p>
                  <p className="buffi-banner-sub">Issues found across {errorCount} files — resolve them before this dataset can be finalized.</p>
                </>
              ) : (
                <p className="buffi-banner-warning"><strong>All files are ready for submission</strong></p>
              )
            )}
          </div>
          <div className="buffi-banner-actions">
            {viewMode === 'grid' && allFiles.length > 0 && (
              <button className="buffi-btn-context" onClick={() => setContextOpen(true)}>Dataset Context</button>
            )}
            {errorCount > 0 && (
              <button className="buffi-btn-outline" onClick={() => setResolveFile(allFiles.find(f => f.hasError))}>
                Resolve {errorCount} Issues
              </button>
            )}
            {allFiles.length > 0 && (
              viewMode === 'grid'
                ? <button className="buffi-btn-primary">{allFiles.length} sources in batch</button>
                : <button className="buffi-btn-primary" onClick={() => setContextOpen(true)}>Submit {readyCount} Ready Files</button>
            )}
          </div>
        </div>

        {/* ── Card view ── */}
        {viewMode === 'grid' ? (
          <>
            <div className="sources-section-header">
              <span className="sources-section-title">Folders</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>
            </div>
            <div className="sources-folders-grid" style={{ marginBottom: 24 }}>
              {CARD_FOLDERS.map((folder, i) => (
                <div key={i} className="sources-folder-card">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                  </svg>
                  <span className="sources-folder-name">{folder}</span>
                  <button className="sources-more-btn">···</button>
                </div>
              ))}
            </div>
            <div className="sources-section-header">
              <span className="sources-section-title">Files</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>
            </div>
            {allFilteredFiles.length === 0 ? (
              <p className="queue-no-results">No files match the current filters.</p>
            ) : (
              <div className="pending-files-grid">
                {allFilteredFiles.map((file) => (
                  <div
                    key={file.id}
                    className={`pending-file-card${file.hasError ? ' has-error' : ''}`}
                    onClick={() => setResolveFile(file)}
                  >
                    <div className="pending-file-card-header">
                      <FileIcon />
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
          /* ── List view: one group per batch, each with its own date ── */
          <>
            {batches.length === 0 && (
              <div className="queue-empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="9" y1="13" x2="15" y2="13"/>
                  <line x1="9" y1="17" x2="15" y2="17"/>
                </svg>
                <p className="queue-empty-title">No files in queue yet</p>
                <p className="queue-empty-sub">Upload a CSV file from <button className="queue-empty-link" onClick={() => navigate('/sources')}>Sources</button> to get started.</p>
              </div>
            )}
            {batches.map((batch) => {
              const batchFiles = batch.files.map(f => ({ ...f, hasError: f.status === 'Error' }));
              const filtered = getFilteredFiles(batchFiles, batch.id);
              const batchSort = batchSortState[batch.id] || { col: null, dir: 'asc' };
              if (filtered.length === 0) return null;
              return (
                <div key={batch.id} className="queue-batch">
                  <div className="queue-batch-header" onClick={e => e.stopPropagation()}>
                    <span className="queue-batch-title">{batch.label}</span>

                    {/* Folder filter dropdown */}
                    <div className="filter-pill-wrap">
                      <button
                        className={`queue-batch-folder-tag${folderFilter !== 'all' ? ' tag-active' : ''}`}
                        onClick={() => toggleDropdown(`folderTag-${batch.id}`)}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                        </svg>
                        {folderFilter === 'all' ? 'Folder' : folderFilter}
                        {folderFilter !== 'all' && (
                          <span className="queue-batch-folder-remove" onClick={(e) => { e.stopPropagation(); setFolderFilter('all'); }}>×</span>
                        )}
                        <ChevronDown />
                      </button>
                      {openDropdown === `folderTag-${batch.id}` && (
                        <div className="filter-dropdown">
                          <button className={`filter-dropdown-item${folderFilter === 'all' ? ' selected' : ''}`} onClick={() => { setFolderFilter('all'); setOpenDropdown(null); }}>All Folders</button>
                          {FOLDERS.map(f => (
                            <button key={f} className={`filter-dropdown-item${folderFilter === f ? ' selected' : ''}`} onClick={() => { setFolderFilter(f); setOpenDropdown(null); }}>{f}</button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  <table className="queue-table">
                    <thead>
                      <tr>
                        {[
                          { label: 'Name',         col: 'name' },
                          { label: 'Folder',       col: 'folder' },
                          { label: 'Status',       col: 'status' },
                          { label: 'Tier',         col: 'tier' },
                          { label: 'File Size',    col: 'size' },
                          { label: 'AI Confidence',col: 'confidence' },
                        ].map(({ label, col }) => (
                          <th key={col} onClick={() => handleColSort(batch.id, col)}>
                            {label}
                            {batchSort.col === col ? (
                              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ marginLeft: 3, verticalAlign: 'middle' }}>
                                {batchSort.dir === 'asc'
                                  ? <polyline points="18 15 12 9 6 15"/>
                                  : <polyline points="6 9 12 15 18 9"/>}
                              </svg>
                            ) : (
                              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ marginLeft: 3, verticalAlign: 'middle', opacity: 0.35 }}>
                                <polyline points="18 15 12 9 6 15"/>
                              </svg>
                            )}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((file) => (
                        <tr key={file.id} className="queue-row" onClick={() => setResolveFile(file)}>
                          <td>
                            <div className="queue-col-name">
                              <FileIcon />
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
                </div>
              );
            })}
          </>
        )}

      </div>

      {/* ── Resolve View ── */}
      {resolveFile && (
        <ResolveView
          file={resolveFile}
          onClose={() => setResolveFile(null)}
          onSubmit={(updatedRows) => {
            setPendingSubmit({ file: resolveFile, updatedRows });
            setResolveFile(null);
            setContextOpen(true);
          }}
        />
      )}

      {/* ── All Resolved / Submit Done confirmation ── */}
      {(allResolved || submitDone) && (
        <div className="resolve-overlay" onClick={() => { setAllResolved(false); setSubmitDone(false); }}>
          <div className="resolve-modal" onClick={e => e.stopPropagation()}>
            <h2 className="resolve-modal-title">{allResolved ? 'All Issues Resolved' : 'File Resolved'}</h2>
            <p style={{ fontFamily: '"Saans TRIAL", sans-serif', fontSize: 14, color: 'var(--Grey-700)', margin: 0, lineHeight: 1.6 }}>
              {allResolved
                ? 'All files have been marked as resolved and are ready for submission.'
                : 'The file changes have been saved and the issue has been resolved.'}
            </p>
            <div className="resolve-modal-actions">
              <button className="resolve-confirm-btn" onClick={() => { setAllResolved(false); setSubmitDone(false); }}>Done</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Submit Confirmation Modal ── */}
      {showSubmitModal && (
        <div className="submit-modal-overlay" onClick={() => setShowSubmitModal(false)}>
          <div className="submit-modal" onClick={e => e.stopPropagation()}>
            <h2 className="submit-modal-title">Files Submitted</h2>
            <p className="submit-modal-body">
              {readyCount} {readyCount === 1 ? 'file has' : 'files have'} been successfully submitted to BFI for processing. You&rsquo;ll be notified once they&rsquo;ve been reviewed.
            </p>
            <button className="submit-modal-btn" onClick={() => setShowSubmitModal(false)}>Done</button>
          </div>
        </div>
      )}

      {/* ── Submission Context Modal ── */}
      <SubmissionContext
        isOpen={contextOpen}
        onClose={() => {
          setContextOpen(false);
          setPendingSubmit(null);
        }}
        onSubmit={() => {
          if (pendingSubmit) {
            // Coming from ResolveView Submit → remove file, show "File Resolved"
            const { file } = pendingSubmit;
            setBatches(prev =>
              prev
                .map(b => ({ ...b, files: b.files.filter(f => f.id !== file.id) }))
                .filter(b => b.files.length > 0)
            );
            setPendingSubmit(null);
            setContextOpen(false);
            setSubmitDone(true);
          } else {
            // Coming from "Submit X Ready Files" banner → remove all ready files, show "Files Submitted"
            setBatches(prev =>
              prev
                .map(b => ({ ...b, files: b.files.filter(f => f.status === 'Error') }))
                .filter(b => b.files.length > 0)
            );
            setContextOpen(false);
            setShowSubmitModal(true);
          }
        }}
        fileName={pendingSubmit?.file?.name || contextFileName}
      />

    </AppLayout>
  );
}
