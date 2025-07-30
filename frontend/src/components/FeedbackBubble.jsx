import { useState } from 'react';
import '../styles/FeedbackBubble.css';

export default function FeedbackBubble({ setHighlightData }) {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;
    const userMsg = { from: 'user', text: message };
    setChatHistory((prev) => [...prev, userMsg]);
    setLoading(true);
    if (setHighlightData) setHighlightData(null); // Clear highlights immediately
    try {
      const res = await fetch('http://localhost:5005/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();
      setChatHistory((prev) => [...prev, { from: 'bot', text: data.response }]);
      if (setHighlightData) {
        setHighlightData(data.highlight_data || null);
      }
    } catch (err) {
      setChatHistory((prev) => [...prev, { from: 'bot', text: 'Sorry, there was an error connecting to the chatbot.' }]);
      if (setHighlightData) {
        setHighlightData(null);
      }
    }
    setLoading(false);
    setMessage('');
  };

  return (
    <div className="feedback-sidebar">
      <div className="sidebar-header">
        <span>Buffi V.01</span>
        <div className="download-icon">⬇️</div>
      </div>
      <div className="sidebar-history">
        {chatHistory.map((msg, idx) => (
          <div key={idx} className={`message-container ${msg.from === 'user' ? 'user-container' : 'bot-container'}`}>
            {msg.from === 'bot' && (
              <div className="avatar bot-avatar">
                <img src="/Chat Message Icon.png" alt="Chat Bot" className="bot-icon" />
              </div>
            )}
            <div className={`message-bubble ${msg.from === 'user' ? 'user-message' : 'bot-message'}`}>
              {msg.text}
            </div>
            {msg.from === 'user' && (
              <div className="avatar user-avatar">
                <span>👤</span>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="message-container bot-container">
            <div className="avatar bot-avatar">
              <img src="/Chat Message Icon.png" alt="Chat Bot" className="bot-icon" />
            </div>
            <div className="message-bubble bot-message">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
      </div>
      <form onSubmit={handleSubmit} className="sidebar-form">
        <div className="input-container">
          <input
            type="text"
            placeholder="Write message here..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            required
            disabled={loading}
            className="message-input"
          />
          <button type="submit" disabled={loading || !message.trim()} className="send-button">
            <span>✈️</span>
          </button>
        </div>
      </form>
    </div>
  );
}
