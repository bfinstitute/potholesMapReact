import { useState, useRef, useEffect } from 'react';
import '../styles/FeedbackBubble.css';
import arrowUpIcon from '../assets/images/Icons_Arrow_up.svg';
import attachIcon from '../assets/images/Icons_Attach.svg';
import copyIcon from '../assets/images/Icons=Copy.svg';
import thumbsUpIcon from '../assets/images/Icons=Thumbs_up.svg';
import thumbsDownIcon from '../assets/images/Icons=Thumbs_down.svg';
import moreHorizIcon from '../assets/images/Icons=More_Horizontal.svg';
import suiteChartsIcon from '../assets/images/SuiteIcons-Charts.svg';
import suiteDataIcon from '../assets/images/SuiteIcons-Data.svg';
import suiteMapsIcon from '../assets/images/SuiteIcons-Maps.svg';
import chevronDownIcon from '../assets/images/Icons=chevron_down.svg';
import loadIcon from '../assets/images/Icons=Load.svg';
import Markdown from 'markdown-to-jsx';

const SUGGESTED_QUESTIONS = [
  { text: "Are housing issues concentrated in specific neighborhoods in ZIP code 78207?",          icon: suiteMapsIcon   },
  { text: "What are the largest mental health needs in ZIP code 78207?",                           icon: suiteDataIcon   },
  { text: "How can we improve decision making on future funding to invest in the right services to address the highest needs on mental health in ZIP code 78207?", icon: suiteDataIcon },
  { text: "How can we improve decision making on future funding to invest in the right services to address the highest needs every category related to the social determinant of health in ZIP code 78207?", icon: suiteChartsIcon },
];


function deriveMaptitle(userText) {
  const t = userText.toLowerCase();
  const zipMatch = t.match(/\b(782\d{2})\b/);
  const zip = zipMatch ? zipMatch[1] : '';
  const suffix = zip ? ` in ${zip}` : '';

  // SDOH / community needs
  if (t.includes('social determinant') || t.includes('sdoh')) return `Community Needs by Domain${suffix}`;
  // Mental health
  if (t.includes('mental health') || t.includes('behavioral health')) return `Mental Health Needs${suffix}`;
  // Housing
  if (t.includes('housing') || t.includes('evict') || t.includes('rent')) return `Housing Needs${suffix}`;
  // Economic
  if (t.includes('economic') || t.includes('poverty') || t.includes('income') || t.includes('employment') || t.includes('job')) return `Economic Conditions${suffix}`;
  // Health / public health
  if (t.includes('health need') || t.includes('public health') || t.includes('diabetes') || t.includes('obesity') || t.includes('chronic')) return `Public Health Needs${suffix}`;
  // Funding / investment / services
  if (t.includes('fund') || t.includes('invest') || t.includes('service') || t.includes('decision')) return `Community Services${suffix}`;
  // Survey / needs assessment
  if (t.includes('survey') || t.includes('need') || t.includes('gap')) return `Needs Assessment${suffix}`;

  // Pothole-specific fallbacks
  if (zip) return `Map of Potholes in ${zip}`;
  if (t.includes('west')) return 'Map of West San Antonio Potholes';
  if (t.includes('worst') || t.includes('most')) return 'Map of Worst Pothole Areas';
  if (t.includes('pci')) return 'Map of Pavement Conditions';
  if (t.includes('complaint')) return 'Map of Active Complaints';
  if (t.includes('route') || t.includes('bus') || t.includes('via')) return 'Map of Transit Routes';
  return 'Map of Pothole Results';
}

function deriveConversationTitle(userText) {
  const clean = userText.replace(/\?$/, '').trim();
  return clean.length > 52 ? clean.slice(0, 49) + '…' : clean;
}

const VIZ_TYPES = [
  { key: 'map',   label: 'Map View of San Antonio' },
  { key: 'pie',   label: 'Pie Chart' },
  { key: 'radar', label: 'Radar Chart' },
  { key: 'bar',   label: 'Bar Chart' },
];

export default function FeedbackBubble({ setHighlightData, setChartData, restoreChartData, setMapTitle, chartType, setChartType, openVisualizationPanel, setIsLoading, setLastQuery, setLastBotResponse, initialQuery, chatHistory, setChatHistory }) {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingPhase, setLoadingPhase] = useState(1);
  const [openCitations, setOpenCitations] = useState({});
  const [openMoreIdx, setOpenMoreIdx] = useState(null);
  const [vizModalOpen, setVizModalOpen] = useState(false);
  const [vizModalMsg, setVizModalMsg] = useState(null);
  const moreDropdownRef = useRef(null);
  const [reactions, setReactions] = useState({});
  const [copiedIdx, setCopiedIdx] = useState(null);
  const historyRef = useRef(null);
  const textareaRef = useRef(null);
  const initialQuerySent = useRef(false);

  // Close "more" dropdown on outside click
  useEffect(() => {
    if (openMoreIdx === null) return;
    const handler = (e) => {
      if (moreDropdownRef.current && !moreDropdownRef.current.contains(e.target)) {
        setOpenMoreIdx(null);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [openMoreIdx]);

  useEffect(() => {
    if (historyRef.current) {
      historyRef.current.scrollTop = historyRef.current.scrollHeight;
    }
  }, [chatHistory, loading]);

  // Switch to phase 2 after 2.5s of loading
  useEffect(() => {
    if (!loading) { setLoadingPhase(1); return; }
    const timer = setTimeout(() => setLoadingPhase(2), 2500);
    return () => clearTimeout(timer);
  }, [loading]);

  // Auto-send query from URL ?q= param on first mount
  useEffect(() => {
    if (initialQuery && !initialQuerySent.current) {
      initialQuerySent.current = true;
      sendMessage(initialQuery);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sendMessage = async (text) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    const title = deriveMaptitle(trimmed);
    const userMsg = { from: 'user', text: trimmed };
    setChatHistory(prev => [...prev, userMsg]);
    if (setLastQuery) setLastQuery(trimmed);
    setMessage('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    setLoading(true);
    if (setIsLoading) setIsLoading(true);
    if (setHighlightData) setHighlightData(null);
    if (setChartData) setChartData(null);

    try {
      const res = await fetch(`/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed }),
      });
      const data = await res.json();
      const structured = data.structured || null;
      const answerText = structured?.answer ?? data.response ?? '';
      const hasMap = !!(data.highlight_data && data.highlight_data.length > 0);
      const hasChart = !!(data.chart_data);

      const citations = structured?.citations || [];
      setChatHistory(prev => [
        ...prev,
        {
          from: 'bot',
          text: answerText,
          structured,
          citations,
          mapTag: hasMap ? title : null,
          chartTag: hasChart ? data.chart_data.title : null,
          savedChartData: data.chart_data || null,
          savedHighlightData: data.highlight_data || null,
          savedTitle: hasChart ? data.chart_data.title : hasMap ? title : null,
        },
      ]);

      if (setHighlightData) setHighlightData(data.highlight_data || null);
      if (setChartData) setChartData(data.chart_data || null);
      if (setLastBotResponse) setLastBotResponse(answerText);
      if (setMapTitle) setMapTitle(deriveConversationTitle(trimmed));
    } catch (err) {
      console.error('Chat error:', err);
      setChatHistory(prev => [
        ...prev,
        { from: 'bot', text: `Error: ${err.message || 'Could not connect to chatbot at ' + (process.env.REACT_APP_BACKEND_URL || 'http://localhost:5005')}` },
      ]);
      if (setHighlightData) setHighlightData(null);
      if (setChartData) setChartData(null);
    }
    setLoading(false);
    if (setIsLoading) setIsLoading(false);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(message);
  };

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text).catch(() => {});
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const handleRegenerate = (idx) => {
    const userMsg = chatHistory.slice(0, idx).reverse().find(m => m.from === 'user');
    if (userMsg) sendMessage(userMsg.text);
    setOpenMoreIdx(null);
  };

  const handleCopyPlain = (text) => {
    const plain = text
      .replace(/\*\*(.+?)\*\*/g, '$1')
      .replace(/\*(.+?)\*/g, '$1')
      .replace(/#{1,6}\s/g, '')
      .replace(/\[(.+?)\]\(.+?\)/g, '$1')
      .replace(/`(.+?)`/g, '$1');
    navigator.clipboard.writeText(plain).catch(() => {});
    setOpenMoreIdx(null);
  };

  const handleReport = (idx) => {
    try {
      const reports = JSON.parse(localStorage.getItem('buffi_reports') || '[]');
      reports.push({ idx, text: chatHistory[idx]?.text, timestamp: Date.now() });
      localStorage.setItem('buffi_reports', JSON.stringify(reports));
    } catch {}
    setOpenMoreIdx(null);
  };

  const handleReaction = (idx, type) => {
    setReactions(prev => {
      const current = prev[idx];
      return { ...prev, [idx]: current === type ? null : type };
    });
  };

  // ── Landing State ──
  if (chatHistory.length === 0 && !loading) {
    return (
      <div className="chat-wrapper">
        <div className="landing-body">
          <div className="landing-greeting">Hi Buffi,</div>
          <div className="landing-heading">What should we dive into?</div>
          <div className="landing-questions">
            {SUGGESTED_QUESTIONS.map((q, i) => (
              <button
                key={i}
                className="landing-question-btn"
                onClick={() => sendMessage(q.text)}
              >
                <span className="landing-question-icon">
                  <img src={q.icon} alt="" className="landing-q-icon" />
                </span>
                {q.text}
              </button>
            ))}
          </div>
        </div>
        <ChatInput
          message={message}
          setMessage={setMessage}
          onSubmit={handleSubmit}
          loading={loading}
          textareaRef={textareaRef}
        />
      </div>
    );
  }

  // ── Chat State ──
  const lastChartIdx = chatHistory.reduce((acc, msg, i) => msg.chartTag ? i : acc, -1);
  const lastVizIdx = chatHistory.reduce((acc, msg, i) => (msg.chartTag || msg.mapTag) ? i : acc, -1);

  // Build a set of dataset names already shown in earlier bot messages (for dedup)
  const seenDatasets = [];
  chatHistory.forEach((msg) => {
    seenDatasets.push(new Set(msg.from === 'bot' ? (msg.citations || []).map(c => c.dataset) : []));
  });

  const restoreViz = (msg, mode = 'chart') => {
    // Use restoreChartData (raw setter) so chart type is NOT reset to 'bar'
    const chartSetter = restoreChartData || setChartData;
    if (mode === 'map') {
      // Clear chart so the map panel is revealed
      if (chartSetter) chartSetter(null);
    } else {
      if (msg.savedChartData && chartSetter) chartSetter(msg.savedChartData);
      else if (chartSetter) chartSetter(null);
    }
    if (msg.savedHighlightData && setHighlightData) setHighlightData(msg.savedHighlightData);
    else if (setHighlightData) setHighlightData(null);
    if (msg.savedTitle && setMapTitle) setMapTitle(msg.savedTitle);
    if (openVisualizationPanel) openVisualizationPanel();
  };

  return (
    <div className="chat-wrapper">
      <div className="chat-history" ref={historyRef}>
        {chatHistory.map((msg, idx) => (
          <div key={idx} className={`msg-row ${msg.from}`}>
            {msg.from === 'user' ? (
              <div className="user-pill">{msg.text}</div>
            ) : (
              <div className="bot-block">
                {msg.chartTag && (
                  <button className="map-tag chart-tag map-tag--clickable" onClick={() => restoreViz(msg, 'chart')} title="Click to show this chart">
                    <img src={suiteChartsIcon} alt="chart" className="suite-tag-icon" />
                    <span className="map-tag-label">{msg.chartTag}</span>
                  </button>
                )}
                {msg.mapTag && (
                  <button className="map-tag map-tag--clickable" onClick={() => restoreViz(msg, 'map')} title="Click to show this map">
                    <img src={suiteMapsIcon} alt="map" className="suite-tag-icon" />
                    <span className="map-tag-label">{msg.mapTag}</span>
                  </button>
                )}
                {!msg.chartTag && !msg.mapTag && (
                  <div className="map-tag data-tag">
                    <img src={suiteDataIcon} alt="data" className="suite-tag-icon" />
                    <span className="map-tag-label">Data Response</span>
                  </div>
                )}
                <div className="bot-text">
                  <Markdown options={{ forceBlock: true }}>
                    {String(msg.text).replace(/\n/g, '  \n')}
                  </Markdown>
                </div>
                {msg.structured?.reasoning_summary && (
                  <div className="structured-panel structured-reasoning">
                    <div className="structured-label">Reasoning</div>
                    <Markdown options={{ forceBlock: true }}>
                      {String(msg.structured.reasoning_summary).replace(/\n/g, '  \n')}
                    </Markdown>
                  </div>
                )}
                {msg.structured?.recommendations?.length > 0 && (
                  <div className="structured-panel structured-recs">
                    <div className="structured-label">Recommendations</div>
                    <ul>
                      {msg.structured.recommendations.map((line, ri) => (
                        <li key={ri}>{line}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {msg.structured?.limitations?.length > 0 && (
                  <div className="structured-panel structured-limits">
                    <div className="structured-label">Limitations</div>
                    <ul>
                      {msg.structured.limitations.map((line, ix) => (
                        <li key={ix}>{line}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {(() => {
                  // Only show citations not already displayed in a prior message
                  const priorSeen = new Set(
                    seenDatasets.slice(0, idx).flatMap(s => [...s])
                  );
                  const newCitations = (msg.citations || []).filter(
                    c => !priorSeen.has(c.dataset)
                  );
                  if (newCitations.length === 0) return null;
                  return (
                    <div className="citations-panel">
                      <button
                        className="citations-toggle"
                        onClick={() => setOpenCitations(prev => ({ ...prev, [idx]: !prev[idx] }))}
                      >
                        <span className="citations-toggle-label">Sources ({newCitations.length})</span>
                        <img
                          src={chevronDownIcon}
                          alt=""
                          className={`citations-toggle-arrow${openCitations[idx] ? ' citations-toggle-arrow--open' : ''}`}
                        />
                      </button>
                      {openCitations[idx] && (
                        <ol className="citations-list">
                          {newCitations.map((c, ci) => (
                            <li key={ci} className="citation-item">
                              <span className="citation-dataset">{c.dataset}</span>
                              {c.source && <span className="citation-source"> · {c.source}</span>}
                              <div className="citation-links">
                                {c.url && <a href={c.url} target="_blank" rel="noreferrer" className="citation-link">Source ↗</a>}
                                {c.data_link && <a href={c.data_link} target="_blank" rel="noreferrer" className="citation-link">Data ↗</a>}
                              </div>
                            </li>
                          ))}
                        </ol>
                      )}
                    </div>
                  );
                })()}
                {msg.structured?.follow_up_question && (
                  <div className="structured-followup">
                    <span className="structured-label">Try asking</span>
                    <span className="structured-followup-q">{msg.structured.follow_up_question}</span>
                  </div>
                )}
                <div className="reaction-bar">
                  <div className="reaction-copy-wrapper">
                    <button
                      className="reaction-btn"
                      title="Copy response"
                      onClick={() => handleCopy(msg.text, idx)}
                    >
                      <img src={copyIcon} alt="Copy" className="reaction-icon" />
                    </button>
                    {copiedIdx === idx && (
                      <span className="reaction-copied-toast">Copied!</span>
                    )}
                  </div>
                  <button
                    className={`reaction-btn${reactions[idx] === 'up' ? ' reaction-btn--active' : ''}`}
                    title="Helpful"
                    onClick={() => handleReaction(idx, 'up')}
                  >
                    <img src={thumbsUpIcon} alt="Helpful" className="reaction-icon" />
                  </button>
                  <button
                    className={`reaction-btn${reactions[idx] === 'down' ? ' reaction-btn--active' : ''}`}
                    title="Not helpful"
                    onClick={() => handleReaction(idx, 'down')}
                  >
                    <img src={thumbsDownIcon} alt="Not helpful" className="reaction-icon" />
                  </button>
                  <div
                    className="reaction-more-wrapper"
                    ref={openMoreIdx === idx ? moreDropdownRef : null}
                  >
                    <button
                      className={`reaction-btn${openMoreIdx === idx ? ' reaction-btn--active' : ''}`}
                      title="More options"
                      onClick={() => setOpenMoreIdx(openMoreIdx === idx ? null : idx)}
                    >
                      <img src={moreHorizIcon} alt="More" className="reaction-icon" />
                    </button>
                    {openMoreIdx === idx && (
                      <div className="reaction-more-dropdown">
                        <button className="reaction-more-item" onClick={() => handleRegenerate(idx)}>
                          Regenerate
                        </button>
                        <button className="reaction-more-item" onClick={() => handleCopyPlain(msg.text)}>
                          Copy as plain text
                        </button>
                        <button className="reaction-more-item reaction-more-item--danger" onClick={() => handleReport(idx)}>
                          Report
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="msg-row bot">
            <div className="bot-block">
              <div className={`loading-state loading-state--${loadingPhase}`}>
                <div className="loading-state-line1">
                  <img src={loadIcon} alt="" className="loading-state-icon" />
                  <span>Working</span>
                </div>
                <div className="loading-state-line2">Searching your sources</div>
              </div>
            </div>
          </div>
        )}
      </div>

      <ChatInput
        message={message}
        setMessage={setMessage}
        onSubmit={handleSubmit}
        loading={loading}
        textareaRef={textareaRef}
      />

      {/* Visualization picker modal */}
      {vizModalOpen && vizModalMsg && (
        <div className="viz-modal-overlay" onClick={() => setVizModalOpen(false)}>
          <div className="viz-modal" onClick={e => e.stopPropagation()}>
            <div className="viz-modal-header">
              <span className="viz-modal-title">Which way would you like me to visualize the data?</span>
              <button className="viz-modal-close" onClick={() => setVizModalOpen(false)}>✕</button>
            </div>
            <div className="viz-modal-list">
              {VIZ_TYPES.map((opt, i) => {
                const selectedKey = vizModalMsg.mapTag && !vizModalMsg.chartTag ? 'map' : chartType;
                const isSelected = selectedKey === opt.key;
                return (
                <div key={opt.key}>
                  <button
                    className={`viz-modal-option${isSelected ? ' viz-modal-option--selected' : ''}`}
                    onClick={() => {
                      if (openVisualizationPanel) openVisualizationPanel();
                      if (opt.key === 'map') {
                        restoreViz(vizModalMsg, 'map');
                      } else {
                        if (setChartType) setChartType(opt.key);
                        restoreViz(vizModalMsg, 'chart');
                      }
                      setVizModalOpen(false);
                    }}
                  >
                    <span className={`viz-modal-radio${isSelected ? ' viz-modal-radio--selected' : ''}`} />
                    <span className="viz-modal-label">{opt.label}</span>
                  </button>
                  {i < VIZ_TYPES.length - 1 && <div className="viz-modal-divider" />}
                </div>
              );
              })}
            </div>
            <div className="viz-modal-footer">
              <button className="viz-modal-skip" onClick={() => setVizModalOpen(false)}>Skip</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ChatInput({ message, setMessage, onSubmit, loading, textareaRef }) {
  const fileRef = useRef(null);
  const [attachedFile, setAttachedFile] = useState(null);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) setAttachedFile(file);
    e.target.value = '';
  };

  const handleRemoveFile = () => setAttachedFile(null);

  return (
    <div className="chat-input-area">
      <input
        ref={fileRef}
        type="file"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
        accept="image/*,.pdf,.doc,.docx,.txt,.csv,.xlsx"
      />
      <div className="chat-input-box">
        {attachedFile && (
          <div className="attached-file-chip">
            <span className="attached-file-name" title={attachedFile.name}>{attachedFile.name}</span>
            <button className="attached-file-remove" onClick={handleRemoveFile} title="Remove">✕</button>
          </div>
        )}
        <div className="chat-input-row">
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            placeholder="Write message here..."
            value={message}
            rows={1}
            disabled={loading}
            onChange={(e) => {
              setMessage(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = e.target.scrollHeight + 'px';
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!loading && message.trim()) onSubmit(e);
              }
            }}
          />
        </div>
        <div className="chat-input-actions">
          <button type="button" className="at-btn" tabIndex={-1} onClick={() => fileRef.current?.click()} title="Attach file">
            <img src={attachIcon} alt="Attach" className="send-icon" />
          </button>
          <button
            type="button"
            className="send-btn"
            disabled={loading || !message.trim()}
            onClick={onSubmit}
          >
            <img src={arrowUpIcon} alt="Send" className="send-icon" />
          </button>
        </div>
      </div>
    </div>
  );
}
