import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import MapView from '../components/MapView';
import ChartView from '../components/ChartView';
import FeedbackBubble from '../components/FeedbackBubble';
import AppSidebar from '../components/AppSidebar';
import bfiIcon from '../assets/images/BFI_LogoIcon.svg';
import downloadIcon from '../assets/images/iconoir_download.svg';
import html2canvas from 'html2canvas';
import domtoimage from 'dom-to-image-more';
import suiteDBIcon from '../assets/images/SuiteIcons-DB.svg';
import chevronDownIcon from '../assets/images/Icons=chevron_down.svg';
import moreHorizIcon from '../assets/images/Icons=More_Horizontal.svg';
import suiteChartsIcon from '../assets/images/SuiteIcons-Charts.svg';
import suiteDataIcon from '../assets/images/SuiteIcons-Data.svg';
import suiteMapsIcon from '../assets/images/SuiteIcons-Maps.svg';
import '../App.css';
import { fetchGeoData, fetchIndicators, fetchProfile } from '../services/dataService';

// Inline SVG icons for the sidebar
const IconEdit = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M13.0207 5.82839L15.8491 2.99996L20.7988 7.94971L17.9704 10.7781M13.0207 5.82839L3.41406 15.435C3.22659 15.6225 3.12134 15.8769 3.12134 16.1421V20.6776H7.65685C7.92207 20.6776 8.17642 20.5723 8.36388 20.3849L17.9704 10.7781M13.0207 5.82839L17.9704 10.7781"/>
  </svg>
);

const IconSearch = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="10.5" cy="10.5" r="6.5"/>
    <path d="M15.5 15.5L20 20"/>
  </svg>
);

const IconBookmark = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 6a2 2 0 012-2h10a2 2 0 012 2v14l-7-3.5L5 20V6z"/>
  </svg>
);

const IconDatabase = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <ellipse cx="12" cy="6" rx="8" ry="3"/>
    <path d="M4 6v6c0 1.657 3.582 3 8 3s8-1.343 8-3V6"/>
    <path d="M4 12v6c0 1.657 3.582 3 8 3s8-1.343 8-3v-6"/>
  </svg>
);

const IconDots = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="5" cy="12" r="1" fill="currentColor"/>
    <circle cx="12" cy="12" r="1" fill="currentColor"/>
    <circle cx="19" cy="12" r="1" fill="currentColor"/>
  </svg>
);

const IconBookmarkTop = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 6a2 2 0 012-2h10a2 2 0 012 2v14l-7-3.5L5 20V6z"/>
  </svg>
);

const _getStoredActive = () => {
  try { return JSON.parse(localStorage.getItem('buffi_active_conv')) || {}; } catch { return {}; }
};
const _getStoredSaved = () => {
  try { return JSON.parse(localStorage.getItem('buffi_saved_convs')) || []; } catch { return []; }
};

function ChatPage() {
  const navigate = useNavigate();
  const [geoData, setGeoData] = useState(null);
  const [indicators, setIndicators] = useState([]);
  const [profiles, setProfiles] = useState({});
  const [selectedArea, setSelectedArea] = useState(null);
  const [customData, setCustomData] = useState(null);
  const [highlightData, setHighlightData] = useState(() => _getStoredActive().highlightData || null);
  const [chartData, setChartData] = useState(() => _getStoredActive().chartData || null);
  const [chartType, setChartType] = useState(() => _getStoredActive().chartType || 'bar');
  const [mapTitle, setMapTitle] = useState(() => _getStoredActive().mapTitle || 'New conversation');
  const [viewMode] = useState('circle');
  const [isLoading, setIsLoading] = useState(false);
  const [lastQuery, setLastQuery] = useState(() => _getStoredActive().lastQuery || '');
  const [lastBotResponse, setLastBotResponse] = useState(() => _getStoredActive().lastBotResponse || '');
  const [shareCopied, setShareCopied] = useState(false);
  const [shareCopiedText, setShareCopiedText] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [dotsOpen, setDotsOpen] = useState(false);
  const [tableOpen, setTableOpen] = useState(false);
  const [undoState, setUndoState] = useState(null);
  const [chatHistory, setChatHistory] = useState(() => _getStoredActive().chatHistory || []);
  const [savedConversations, setSavedConversations] = useState(_getStoredSaved);
  const [activeConvId, setActiveConvId] = useState(() => _getStoredActive().id || Date.now());
  const [convSwitcherOpen, setConvSwitcherOpen] = useState(false);
  const [chatDotsOpen, setChatDotsOpen] = useState(false);
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState('');
  const panelRef = useRef(null);
  const dotsRef = useRef(null);
  const shareRef = useRef(null);
  const convSwitcherRef = useRef(null);
  const chatDotsRef = useRef(null);
  const undoTimerRef = useRef(null);

  // Read initial query from URL ?q= param
  const initialQuery = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('q') || '';
  }, []);

  // Close dots dropdown on outside click
  useEffect(() => {
    if (!dotsOpen) return;
    const handler = (e) => {
      if (dotsRef.current && !dotsRef.current.contains(e.target)) setDotsOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [dotsOpen]);

  // Close share dropdown on outside click
  useEffect(() => {
    if (!shareOpen) return;
    const handler = (e) => {
      if (shareRef.current && !shareRef.current.contains(e.target)) setShareOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [shareOpen]);

  // Persist saved conversations to localStorage
  useEffect(() => {
    try { localStorage.setItem('buffi_saved_convs', JSON.stringify(savedConversations)); } catch {}
  }, [savedConversations]);

  // Persist active conversation to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('buffi_active_conv', JSON.stringify({
        id: activeConvId, chatHistory, mapTitle, highlightData, chartData, chartType, lastQuery, lastBotResponse,
      }));
    } catch {}
  }, [activeConvId, chatHistory, mapTitle, highlightData, chartData, chartType, lastQuery, lastBotResponse]);

  // Close chat dots dropdown on outside click
  useEffect(() => {
    if (!chatDotsOpen) return;
    const handler = (e) => {
      if (chatDotsRef.current && !chatDotsRef.current.contains(e.target)) setChatDotsOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [chatDotsOpen]);

  // Close conversation switcher on outside click
  useEffect(() => {
    if (!convSwitcherOpen) return;
    const handler = (e) => {
      if (convSwitcherRef.current && !convSwitcherRef.current.contains(e.target)) setConvSwitcherOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [convSwitcherOpen]);

  // Reset chart type to bar whenever a new chart response arrives
  const handleSetChartData = (data) => {
    setChartData(data);
    if (data) setChartType('bar');
  };

  useEffect(() => {
    fetchGeoData().then(setGeoData);
    fetchIndicators().then(data => {
      setIndicators(data);
      const map = {};
      data.forEach(d => (map[d.areaId] = d.value));
      setProfiles(prev => ({ ...prev, map }));
    });
  }, []);

  const handleAreaClick = id => {
    fetchProfile(id).then(profile => {
      setProfiles(prev => ({ ...prev, [id]: profile }));
      setSelectedArea(id);
    });
  };

  const handleDownload = async () => {
    if (!panelRef.current || isLoading) return;
    const rawTitle = chartData?.title || mapTitle || 'visualization';
    const filename = `${rawTitle.replace(/[^a-z0-9]/gi, '_').replace(/_+/g, '_')}.png`;
    try {
      if (chartData) {
        // Charts: html2canvas works fine
        const canvas = await html2canvas(panelRef.current, { useCORS: true, logging: false });
        triggerDownload(canvas.toDataURL('image/png'), filename);
      } else {
        // Maps: dom-to-image-more uses the browser's SVG renderer which correctly
        // handles Leaflet's CSS transforms, keeping tiles and overlays aligned.
        const mapEl = panelRef.current.querySelector('.leaflet-container') || panelRef.current;
        const dataUrl = await domtoimage.toPng(mapEl, {
          width: mapEl.offsetWidth,
          height: mapEl.offsetHeight,
        });
        triggerDownload(dataUrl, filename);
      }
    } catch (e) {
      console.error('Download failed:', e);
    }
  };

  const triggerDownload = (dataUrl, filename) => {
    const link = document.createElement('a');
    link.download = filename;
    link.href = dataUrl;
    link.click();
  };

  const handleCloseMap = () => {
    // Save current state for undo
    setUndoState({ mapTitle, highlightData, chartData });
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
    undoTimerRef.current = setTimeout(() => setUndoState(null), 5000);

    setMapTitle('New conversation');
    setHighlightData(null);
    handleSetChartData(null);
    setTableOpen(false);
  };

  const handleUndo = () => {
    if (!undoState) return;
    setMapTitle(undoState.mapTitle);
    setHighlightData(undoState.highlightData);
    handleSetChartData(undoState.chartData);
    if (undoState.chatHistory) setChatHistory(undoState.chatHistory);
    setUndoState(null);
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
  };

  const handleClearConversation = () => {
    setUndoState({ mapTitle, highlightData, chartData, chatHistory });
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
    undoTimerRef.current = setTimeout(() => setUndoState(null), 5000);
    setActiveConvId(Date.now());
    setChatHistory([]);
    setMapTitle('New conversation');
    setHighlightData(null);
    setChartData(null);
    setChartType('bar');
    setLastQuery('');
    setLastBotResponse('');
    setTableOpen(false);
    setChatDotsOpen(false);
  };

  const handleExportConversation = () => {
    if (!chatHistory.length) return;
    const text = chatHistory
      .map(msg => msg.from === 'user' ? `You: ${msg.text}` : `Buffi: ${msg.text}`)
      .join('\n\n');
    copyToClipboard(text);
    setChatDotsOpen(false);
  };

  const handleStartRename = () => {
    setRenameValue(mapTitle);
    setIsRenaming(true);
    setChatDotsOpen(false);
  };

  const handleConfirmRename = () => {
    if (renameValue.trim()) setMapTitle(renameValue.trim());
    setIsRenaming(false);
  };

  const copyToClipboard = (text) => {
    try {
      navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
  };

  const handleShareCopyLink = async () => {
    if (!lastQuery) return;
    const url = `${window.location.origin}${window.location.pathname}?q=${encodeURIComponent(lastQuery)}`;
    copyToClipboard(url);
    setShareCopied(true);
    setTimeout(() => setShareCopied(false), 2000);
    setShareOpen(false);
  };

  const handleCopyResponse = () => {
    if (!lastBotResponse) return;
    copyToClipboard(lastBotResponse);
    setShareCopiedText(true);
    setTimeout(() => setShareCopiedText(false), 2000);
    setShareOpen(false);
  };

  const saveCurrentConv = () => {
    if (chatHistory.length === 0) return;
    const snapshot = { id: activeConvId, chatHistory, highlightData, chartData, chartType, lastQuery, lastBotResponse, mapTitle };
    setSavedConversations(prev => {
      const idx = prev.findIndex(c => c.id === activeConvId);
      if (idx >= 0) return prev.map((c, i) => i === idx ? snapshot : c);
      return [...prev, snapshot];
    });
  };

  const handleNewConversation = () => {
    saveCurrentConv();
    setActiveConvId(Date.now());
    setChatHistory([]);
    setHighlightData(null);
    setChartData(null);
    setChartType('bar');
    setLastQuery('');
    setLastBotResponse('');
    setMapTitle('New conversation');
    setConvSwitcherOpen(false);
  };

  const handleSwitchConversation = (conv) => {
    saveCurrentConv();
    setSavedConversations(prev => prev.filter(c => c.id !== conv.id));
    setActiveConvId(conv.id);
    setChatHistory(conv.chatHistory);
    setHighlightData(conv.highlightData || null);
    setChartData(conv.chartData || null);
    setChartType(conv.chartType || 'bar');
    setLastQuery(conv.lastQuery || '');
    setLastBotResponse(conv.lastBotResponse || '');
    setMapTitle(conv.mapTitle || 'New conversation');
    setConvSwitcherOpen(false);
  };

  const handleEmailShare = () => {
    if (!lastQuery) return;
    const url = `${window.location.origin}${window.location.pathname}?q=${encodeURIComponent(lastQuery)}`;
    const subject = encodeURIComponent(`Insight: ${mapTitle}`);
    const body = encodeURIComponent(`Check out this insight from Buffi:\n\n${lastBotResponse ? lastBotResponse.slice(0, 300) + '…' : ''}\n\nView it here: ${url}`);
    window.open(`mailto:?subject=${subject}&body=${body}`);
    setShareOpen(false);
  };

  const titleIconColor = chartData ? '#FF5C17' : '#00B89C';
  const hasVisualization = mapTitle !== 'New conversation';

  return (
    <div className="app-wrapper">
      {/* 3 vertical columns — each owns its header + body so borders always align */}

      {/* Column 1: Sidebar */}
      <AppSidebar />

      {/* Column 2: Chat */}
      <div className="col-chat">
        <div className="col-header col-header--chat">
          <img src={bfiIcon} alt="Buffi" className="chat-header-logo" />
          <span className="top-bar-brand">Buffi V.02</span>
          <div className="chat-dots-wrapper" ref={chatDotsRef}>
            <button
              className="top-bar-icon-btn"
              title="More options"
              onClick={() => setChatDotsOpen(o => !o)}
            >
              <img src={moreHorizIcon} alt="More" className="top-bar-icon" />
            </button>
            {chatDotsOpen && (
              <div className="chat-dots-dropdown">
                <button
                  className="chat-dots-item"
                  onClick={handleClearConversation}
                  disabled={!chatHistory.length}
                >
                  Clear conversation
                </button>
                <button
                  className="chat-dots-item"
                  onClick={handleExportConversation}
                  disabled={!chatHistory.length}
                >
                  Export conversation
                </button>
                <div className="chat-dots-divider" />
                <button
                  className="chat-dots-item"
                  onClick={handleStartRename}
                  disabled={mapTitle === 'New conversation'}
                >
                  Rename
                </button>
              </div>
            )}
          </div>
        </div>
        <div className="chat-panel">
          <FeedbackBubble
            key={activeConvId}
            chatHistory={chatHistory}
            setChatHistory={setChatHistory}
            setHighlightData={setHighlightData}
            setChartData={handleSetChartData}
            restoreChartData={setChartData}
            setMapTitle={setMapTitle}
            chartType={chartType}
            setChartType={setChartType}
            setIsLoading={setIsLoading}
            setLastQuery={setLastQuery}
            setLastBotResponse={setLastBotResponse}
            initialQuery={chatHistory.length === 0 && savedConversations.length === 0 ? initialQuery : ''}
          />
        </div>
      </div>

      {/* Column 3: Visualization */}
      <div className="col-map">
        <div className="col-header col-header--map">
          <div className="top-bar-map-left">
            <img src={suiteDBIcon} alt="DB" className="top-bar-db-icon" />
            {hasVisualization && (
              <button className="map-title-close" onClick={handleCloseMap}>✕</button>
            )}
            {isRenaming ? (
              <input
                className="map-title-input"
                value={renameValue}
                autoFocus
                onChange={e => setRenameValue(e.target.value)}
                onBlur={handleConfirmRename}
                onKeyDown={e => {
                  if (e.key === 'Enter') handleConfirmRename();
                  if (e.key === 'Escape') setIsRenaming(false);
                }}
              />
            ) : (
              <span className="map-title-text">{mapTitle}</span>
            )}
            <div className="conv-switcher-wrapper" ref={convSwitcherRef}>
              <button
                className="map-title-chevron"
                onClick={() => setConvSwitcherOpen(o => !o)}
                title="Switch conversation"
              >
                <img
                  src={chevronDownIcon}
                  alt="Switch conversation"
                  className={`map-title-chevron-icon${convSwitcherOpen ? ' map-title-chevron-icon--open' : ''}`}
                />
              </button>
              {convSwitcherOpen && (
                <div className="conv-switcher-dropdown">
                  <button className="conv-switcher-new" onClick={handleNewConversation}>
                    + New conversation
                  </button>
                  {savedConversations.length > 0 && (
                    <>
                      <div className="conv-switcher-divider" />
                      {[...savedConversations].reverse().map(conv => (
                        <button
                          key={conv.id}
                          className="conv-switcher-item"
                          onClick={() => handleSwitchConversation(conv)}
                        >
                          {conv.mapTitle || 'New conversation'}
                        </button>
                      ))}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="top-bar-map-right">
            <button className="top-bar-icon-btn top-bar-icon-btn--disabled" title="Bookmark" disabled>
              <IconBookmarkTop />
            </button>
            <button className="top-bar-icon-btn" title="Download" onClick={handleDownload} disabled={isLoading || !lastQuery}>
              <img src={downloadIcon} alt="download" className="top-bar-icon" />
            </button>
            <div className="dots-btn-wrapper" ref={dotsRef}>
              <button className="top-bar-icon-btn" title="More" onClick={() => lastQuery && setDotsOpen(o => !o)} disabled={!lastQuery}>
                <IconDots />
              </button>
              {dotsOpen && (
                <div className="dots-dropdown">
                  <button
                    className="dots-dropdown-item"
                    disabled={!chartData && !highlightData}
                    onClick={() => { setTableOpen(true); setDotsOpen(false); }}
                  >
                    View Data Table
                  </button>
                  <div className="dots-dropdown-divider" />
                  <button
                    className="dots-dropdown-item"
                    disabled={!hasVisualization}
                    onClick={() => { handleCloseMap(); setDotsOpen(false); }}
                  >
                    Clear View
                  </button>
                </div>
              )}
            </div>
            <div className="share-btn-wrapper" ref={shareRef}>
              <button
                className={`share-btn${shareCopied || shareCopiedText ? ' share-btn--copied' : ''}`}
                onClick={() => lastQuery && setShareOpen(o => !o)}
                disabled={!lastQuery}
                title={lastQuery ? 'Share options' : 'Ask a question first'}
              >
                <span className="share-btn-label">
                  {shareCopied ? '✓ Link copied!' : shareCopiedText ? '✓ Text copied!' : 'Share'}
                </span>
                <span className="share-btn-divider" />
                <span className="share-chevron-wrap">
                  <svg width="12" height="8" viewBox="0 0 12 8" fill="none">
                    <path d="M1 1.5L6 6.5L11 1.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
              </button>
              {shareOpen && (
                <div className="share-dropdown">
                  <button className="share-dropdown-item" onClick={handleShareCopyLink}>
                    Copy link
                  </button>
                  <button className="share-dropdown-item" onClick={handleCopyResponse} disabled={!lastBotResponse}>
                    Copy response text
                  </button>
                  <button className="share-dropdown-item" onClick={handleEmailShare} disabled={!lastQuery}>
                    Send via email
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
        <div className={`map-panel${isLoading ? ' map-panel--loading' : ''}`} ref={panelRef}>
          {isLoading ? (
            <div className="loading-visual">
              <div className="loading-visual-inner">
                <svg className="loading-spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
                </svg>
                <span className="loading-visual-text">Loading Visual...</span>
              </div>
              <div className="loading-progress-track">
                <div className="loading-progress-bar" />
              </div>
            </div>
          ) : !hasVisualization ? (
            <div className="viz-empty-state">
              <div className="viz-empty-icons">
                <img src={suiteChartsIcon} alt="Charts" className="viz-empty-icon" />
                <img src={suiteDataIcon}   alt="Data"   className="viz-empty-icon" />
                <img src={suiteMapsIcon}   alt="Maps"   className="viz-empty-icon" />
              </div>
              <div className="viz-empty-title">Visualization panel</div>
              <div className="viz-empty-subtitle">Ask any question and the best visual for your question will appear here.</div>
              <button className="viz-empty-btn">
                <img src={suiteDBIcon} alt="DB" className="viz-empty-btn-icon" />
                Review Sources
              </button>
            </div>
          ) : chartData ? (
            <ChartView chartData={chartData} chartType={chartType} />
          ) : (
            <MapView
              geoData={geoData}
              params={customData || profiles.map}
              onAreaClick={handleAreaClick}
              highlightData={highlightData}
              viewMode={viewMode}
            />
          )}
        </div>
      </div>
      {/* Undo Toast */}
      {undoState && (
        <div className="undo-toast">
          <span className="undo-toast-text">View cleared</span>
          <button className="undo-toast-btn" onClick={handleUndo}>Undo</button>
        </div>
      )}

      {/* Data Table Modal */}
      {tableOpen && (chartData || highlightData) && (
        <div className="data-table-overlay" onClick={() => setTableOpen(false)}>
          <div className="data-table-modal" onClick={e => e.stopPropagation()}>
            <div className="data-table-header">
              <span className="data-table-title">{chartData ? chartData.title : mapTitle}</span>
              <button className="data-table-close" onClick={() => setTableOpen(false)}>✕</button>
            </div>
            <div className="data-table-body">
              {chartData && chartData.data && chartData.data.length > 0 ? (
                <table className="data-table">
                  <thead>
                    <tr>
                      {Object.keys(chartData.data[0]).map(k => (
                        <th key={k}>{k}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {chartData.data.map((row, i) => (
                      <tr key={i}>
                        {Object.values(row).map((v, j) => (
                          <td key={j}>{typeof v === 'number' ? v.toLocaleString() : v}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : highlightData && highlightData.length > 0 ? (
                <table className="data-table">
                  <thead>
                    <tr>
                      {Object.keys(highlightData[0]).filter(k => !['color','marker_radius'].includes(k)).map(k => (
                        <th key={k}>{k}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {highlightData.slice(0, 200).map((row, i) => (
                      <tr key={i}>
                        {Object.entries(row).filter(([k]) => !['color','marker_radius'].includes(k)).map(([k, v]) => (
                          <td key={k}>{typeof v === 'number' ? v.toLocaleString() : String(v ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="data-table-empty">No data available.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ChatPage;
