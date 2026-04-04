import { useState } from 'react';
import '../styles/FeedbackBubble.css';
import downloadIcon from '../assets/images/iconoir_download.svg';
import sendIcon from '../assets/images/iconoir_send-solid.svg';
import botIcon from '../assets/images/BFI_LogoIcon.svg';
import Markdown from 'markdown-to-jsx';

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
    if (setHighlightData) setHighlightData(null);
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

  const handleDownload = () => {
    if (chatHistory.length === 0) return;

    const formattedText = chatHistory
      .map((msg, index) => `${msg.from.toUpperCase()}: ${msg.text}`)
      .join('\n\n');

    const blob = new Blob([formattedText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = 'chat_history.txt';
    a.click();

    URL.revokeObjectURL(url); // Clean up
  };

  const renderMessageText = (text, from) => {
    if (from === 'bot') {
      // Convert single newlines to Markdown line breaks so spacing is preserved
      const withMdLineBreaks = String(text).replace(/\n/g, '  \n');
      return (
        <Markdown options={{ forceBlock: true }}>{withMdLineBreaks}</Markdown>
      );
    }
    return text;
  };

  return (
    <div className="feedback-sidebar">
      <div className="sidebar-header">
        <span>Buffi V.01</span>
        <div className="download-icon-container" onClick={handleDownload} title="Download chat history">
          <img className="download-icon" src={downloadIcon} alt="⬇️" style={{ cursor: 'pointer' }} />
        </div>
      </div>
      <div className="sidebar-history">
        {chatHistory.map((msg, idx) => (
          <div key={idx} className={`message-container ${msg.from === 'user' ? 'user-container' : 'bot-container'}`}>
            {msg.from === 'bot' && (
              <div className="avatar bot-avatar">
                <img src={botIcon} alt="Chat Bot" className="bot-icon" />
              </div>
            )}
            <div className={`message-bubble ${msg.from === 'user' ? 'user-message' : 'bot-message'}`}>
              {renderMessageText(msg.text, msg.from)}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message-container bot-container">
            <div className="avatar bot-avatar">
              <img src={botIcon} alt="Chat Bot" className="bot-icon" />
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
          <textarea
            placeholder="Write message here..."
            value={message}
            onChange={(e) => {
              setMessage(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = e.target.scrollHeight + 'px';
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault(); // Prevent newline
                if (!loading && message.trim()) {
                  handleSubmit(e);  // Submit the message
                }
              }
            }}
            required
            disabled={loading}
            className="message-input"
            rows={1}
          />
          <button type="submit" disabled={loading || !message.trim()} className="send-button">
            <img src={sendIcon} alt="Send" className="send-icon" />
          </button>
        </div>
      </form>
    </div>
  );
}
