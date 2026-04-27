import { useState, useRef, useEffect } from 'react';
import '../styles/ResolveView.css';

const MOCK_COLUMNS = ['request_id', 'date_filled', 'zip_code', 'geo_ref', 'category', 'src_depart'];

const makeMockRows = () =>
  Array.from({ length: 14 }, (_, i) => ({
    rowIndex: i,
    request_id: '311-0001',
    date_filled: '2025-07-02',
    zip_code: '78221',
    geo_ref: i === 0 || i === 1 ? 'RES_UNKNWN' : 'GR-8802-TX',
    category: 'Land Use & Zoning',
    src_depart: 'Public Works',
    hasError: i === 0 || i === 1,
  }));

const INITIAL_MESSAGES = [
  {
    id: 1,
    role: 'ai',
    text: 'I found "RES-UNKNWN" which doesn\'t match the accepted classification format. I\'ve suggested R-4 based on the surrounding parcel classifications. The district boundary overlap with an adjacent commercial zone has low confidence — please verify before approving.',
    suggestions: [
      'Accept suggested value of R-4 for row 7',
      'Apply suggested fix to all similar errors',
      'Flag row 7 for manual review',
    ],
  },
];

export default function ResolveView({ file, onClose, onSubmit }) {
  const hasRealData = file?.csvData && file.csvData.length > 0;
  const columns = hasRealData ? Object.keys(file.csvData[0]) : MOCK_COLUMNS;

  const [rows, setRows] = useState(() => {
    if (hasRealData) {
      return file.csvData.map((row, i) => ({ ...row, rowIndex: i, hasError: false }));
    }
    return makeMockRows();
  });

  const [messages, setMessages]       = useState(INITIAL_MESSAGES);
  const [inputText, setInputText]     = useState('');
  const [highlight, setHighlight]     = useState(true);
  const [editingCell, setEditingCell] = useState(null); // { rowIndex, field }
  const [editValue, setEditValue]     = useState('');
  const chatBottomRef = useRef(null);

  const errorCount = rows.filter(r => r.hasError).length;

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addAiMessage = (text, suggestions) => {
    setMessages(prev => [...prev, { id: Date.now(), role: 'ai', text, suggestions }]);
  };

  const sendMessage = (text) => {
    if (!text.trim()) return;
    setMessages(prev => [...prev, { id: Date.now(), role: 'user', text }]);
    setInputText('');
    setTimeout(() => {
      addAiMessage("Thanks for the note. I've logged your feedback and will incorporate it into the review.");
    }, 700);
  };

  const applySuggestion = (suggestion) => {
    setMessages(prev => [...prev, { id: Date.now(), role: 'user', text: suggestion }]);
    if (suggestion.startsWith('Accept suggested value')) {
      setRows(prev => prev.map((r, i) => i === 0 ? { ...r, geo_ref: 'R-4', hasError: false } : r));
      setTimeout(() => addAiMessage('Done. Row 7 has been updated to R-4. The error is resolved.'), 500);
    } else if (suggestion.startsWith('Apply suggested fix')) {
      setRows(prev => prev.map(r => r.hasError ? { ...r, geo_ref: 'R-4', hasError: false } : r));
      setTimeout(() => addAiMessage('Done. The fix has been applied to all similar errors in this file.'), 500);
    } else if (suggestion.startsWith('Flag')) {
      setTimeout(() => addAiMessage('Row 7 has been flagged for manual review. A data steward will be notified.'), 500);
    }
  };

  const startEdit = (rowIndex, field, value) => {
    setEditingCell({ rowIndex, field });
    setEditValue(String(value ?? ''));
  };

  const saveEdit = () => {
    if (!editingCell) return;
    const { rowIndex, field } = editingCell;
    setRows(prev => prev.map((r, i) => {
      if (i !== rowIndex) return r;
      const updated = { ...r, [field]: editValue };
      // Only auto-clear error for mock geo_ref column
      if (!hasRealData && field === 'geo_ref') updated.hasError = editValue === 'RES_UNKNWN';
      return updated;
    }));
    setEditingCell(null);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') saveEdit();
    if (e.key === 'Escape') setEditingCell(null);
  };

  const handleSubmit = () => {
    onSubmit(rows);
  };

  return (
    <div className="rv-overlay" onClick={onClose}>
      <div className="rv-panel" onClick={e => e.stopPropagation()}>

        {/* ── Top Bar ── */}
        <div className="rv-topbar">
          <div className="rv-topbar-left">
            <button className="rv-close-btn" onClick={onClose}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
            <div className="rv-file-tab">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              <span className="rv-filename">{file?.name || 'file.csv'}</span>
            </div>
          </div>
          <div className="rv-topbar-right">
            <button className="rv-more-btn">···</button>
            <button
              className={`rv-highlight-btn${highlight ? ' active' : ''}`}
              onClick={() => setHighlight(p => !p)}
            >
              Highlight {errorCount} {errorCount === 1 ? 'Issue' : 'Issues'}
            </button>
            <button className="rv-submit-btn" onClick={handleSubmit}>Submit</button>
          </div>
        </div>

        {/* ── Body ── */}
        <div className="rv-body">

          {/* Left: Chat Panel */}
          <div className="rv-chat">
            <span className="rv-chat-label">BFI AI</span>
            <div className="rv-chat-messages">
              {messages.map((msg) => (
                <div key={msg.id} className={`rv-msg rv-msg-${msg.role}`}>
                  <p className="rv-msg-text">{msg.text}</p>
                  {msg.suggestions && msg.suggestions.length > 0 && (
                    <div className="rv-suggestions">
                      <span className="rv-suggestions-label">Suggested Actions:</span>
                      {msg.suggestions.map((s, j) => (
                        <button key={j} className="rv-suggestion-btn" onClick={() => applySuggestion(s)}>
                          {s}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              <div ref={chatBottomRef} />
            </div>
            <div className="rv-chat-input-row">
              <input
                className="rv-chat-input"
                placeholder="Ask a question..."
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendMessage(inputText)}
              />
              <button className="rv-chat-send" onClick={() => sendMessage(inputText)}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"/>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
              </button>
            </div>
          </div>

          {/* Right: Data Table */}
          <div className="rv-table-wrap">
            <table className="rv-table">
              <thead>
                <tr>
                  {columns.map(col => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={i} className={highlight && row.hasError ? 'rv-row-error' : ''}>
                    {columns.map(col => {
                      const isEditing = editingCell?.rowIndex === i && editingCell?.field === col;
                      const isError   = highlight && row.hasError && col === 'geo_ref';
                      return (
                        <td key={col} className={isError ? 'rv-cell-error' : 'rv-cell-editable'}>
                          {isEditing ? (
                            <input
                              className="rv-cell-input"
                              value={editValue}
                              onChange={e => setEditValue(e.target.value)}
                              onBlur={saveEdit}
                              onKeyDown={handleKeyDown}
                              autoFocus
                            />
                          ) : (
                            <span className="rv-cell-value">
                              {String(row[col] ?? '')}
                              <button
                                className="rv-edit-btn"
                                onClick={() => startEdit(i, col, row[col])}
                                title="Edit"
                              >
                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                                </svg>
                              </button>
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

        </div>
      </div>
    </div>
  );
}
