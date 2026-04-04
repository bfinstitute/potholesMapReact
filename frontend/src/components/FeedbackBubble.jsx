import { useState, useRef, useEffect } from 'react';
import '../styles/FeedbackBubble.css';
import sendIcon from '../assets/images/iconoir_send-solid.svg';
import botIcon from '../assets/images/BFI_LogoIcon.svg';
import checkIcon from '../assets/images/iconoir_check-circle.svg';
import Markdown from 'markdown-to-jsx';

const SUGGESTED_QUESTIONS = [
  "Show me potholes on the west side",
  "Which ZIP codes have the most potholes?",
  "What's the PCI score for ZIP code 78207?",
  "Show me the areas with the worst road conditions",
];

const QUICK_CHIPS = ['Zipcode', 'Neighborhood', 'District', 'Other'];

function deriveMaptitle(userText) {
  const t = userText.toLowerCase();
  const zipMatch = t.match(/\b(782\d{2})\b/);
  if (zipMatch) return `Map of Potholes in ${zipMatch[1]}`;
  if (t.includes('west')) return 'Map of West San Antonio Potholes';
  if (t.includes('worst') || t.includes('most')) return 'Map of Worst Pothole Areas';
  if (t.includes('pci')) return 'Map of Pavement Conditions';
  if (t.includes('complaint')) return 'Map of Active Complaints';
  if (t.includes('route') || t.includes('bus') || t.includes('via')) return 'Map of Transit Routes';
  return 'Map of Pothole Results';
}

const CHART_TYPES = [
  { key: 'bar',   label: 'Bar',   icon: '▊' },
  { key: 'pie',   label: 'Pie',   icon: '◔' },
  { key: 'radar', label: 'Radar', icon: '◎' },
];

export default function FeedbackBubble({ setHighlightData, setChartData, setMapTitle, chartType, setChartType }) {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const historyRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (historyRef.current) {
      historyRef.current.scrollTop = historyRef.current.scrollHeight;
    }
  }, [chatHistory, loading]);

  const sendMessage = async (text) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    const title = deriveMaptitle(trimmed);
    const userMsg = { from: 'user', text: trimmed };
    setChatHistory(prev => [...prev, userMsg]);
    setMessage('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    setLoading(true);
    if (setHighlightData) setHighlightData(null);
    if (setChartData) setChartData(null);

    try {
      const res = await fetch('http://localhost:5005/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed }),
      });
      const data = await res.json();
      const hasMap = !!(data.highlight_data && data.highlight_data.length > 0);
      const hasChart = !!(data.chart_data);

      setChatHistory(prev => [
        ...prev,
        {
          from: 'bot',
          text: data.response,
          mapTag: hasMap && !hasChart ? title : null,
          chartTag: hasChart ? data.chart_data.title : null,
          chips: (hasMap || hasChart) ? QUICK_CHIPS : null,
        },
      ]);

      if (setHighlightData) setHighlightData(data.highlight_data || null);
      if (setChartData) setChartData(data.chart_data || null);
      if (setMapTitle) {
        if (hasChart) setMapTitle(data.chart_data.title);
        else if (hasMap) setMapTitle(title);
        else setMapTitle('New conversation');
      }
    } catch {
      setChatHistory(prev => [
        ...prev,
        { from: 'bot', text: 'Sorry, there was an error connecting to the chatbot.' },
      ]);
      if (setHighlightData) setHighlightData(null);
      if (setChartData) setChartData(null);
    }
    setLoading(false);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(message);
  };

  const handleChipClick = (chip) => {
    sendMessage(chip);
  };

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text).catch(() => {});
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
                onClick={() => sendMessage(q)}
              >
                <span className="landing-question-icon">
                  <img src={botIcon} alt="" className="landing-q-icon" />
                </span>
                {q}
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
                  <div className="map-tag chart-tag">
                    <span className="chart-tag-icon">📊</span>
                    <span className="map-tag-label">{msg.chartTag}</span>
                  </div>
                )}
                {msg.mapTag && (
                  <div className="map-tag">
                    <span className="map-tag-dot" />
                    <span className="map-tag-label">{msg.mapTag}</span>
                  </div>
                )}
                <div className="bot-text">
                  <Markdown options={{ forceBlock: true }}>
                    {String(msg.text).replace(/\n/g, '  \n')}
                  </Markdown>
                </div>
                {/* Chart type toggle — only on the most recent chart response */}
                {msg.chartTag && idx === lastChartIdx && (
                  <div className="chart-type-row">
                    <span className="chart-type-label">Chart type</span>
                    <div className="chart-type-btns">
                      {CHART_TYPES.map(ct => (
                        <button
                          key={ct.key}
                          className={`chart-type-btn ${chartType === ct.key ? 'active' : ''}`}
                          onClick={() => setChartType && setChartType(ct.key)}
                        >
                          <span className="chart-type-icon">{ct.icon}</span>
                          {ct.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {msg.chips && (
                  <div className="chip-row">
                    {msg.chips.map((chip, ci) => (
                      <button
                        key={ci}
                        className="quick-chip"
                        onClick={() => handleChipClick(chip)}
                      >
                        {chip}
                      </button>
                    ))}
                  </div>
                )}
                <div className="reaction-bar">
                  <button className="reaction-btn" title="Helpful">👍</button>
                  <button className="reaction-btn" title="Not helpful">👎</button>
                  <button
                    className="reaction-btn"
                    title="Copy"
                    onClick={() => handleCopy(msg.text)}
                  >
                    <img src={checkIcon} alt="copy" className="reaction-icon" />
                  </button>
                  <button className="reaction-btn" title="More">···</button>
                </div>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="msg-row bot">
            <div className="bot-block">
              <div className="typing-indicator">
                <span /><span /><span />
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
    </div>
  );
}

function ChatInput({ message, setMessage, onSubmit, loading, textareaRef }) {
  return (
    <form className="chat-input-area" onSubmit={onSubmit}>
      <button type="button" className="at-btn" tabIndex={-1}>@</button>
      <textarea
        ref={textareaRef}
        className="chat-textarea"
        placeholder="Write a message..."
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
      <button
        type="submit"
        className="send-btn"
        disabled={loading || !message.trim()}
      >
        <img src={sendIcon} alt="Send" className="send-icon" />
      </button>
    </form>
  );
}
