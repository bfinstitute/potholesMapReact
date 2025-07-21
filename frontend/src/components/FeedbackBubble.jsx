import { useState } from 'react';
import '../styles/FeedbackBubble.css';

export default function FeedbackBubble({ setHighlightData }) {
  const [isOpen, setIsOpen] = useState(false);
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
    <div className="feedback-bubble">
      {!isOpen ? (
        <button className="open-button" onClick={() => setIsOpen(true)}>
          🤖 Chatbot
        </button>
      ) : (
        <div className="bubble-popup">
          <div className="bubble-header">
            <span>Chat with us</span>
            <button onClick={() => setIsOpen(false)}>×</button>
          </div>
          <div className="bubble-history">
            {chatHistory.map((msg, idx) => (
              <div key={idx} className={msg.from === 'user' ? 'user-msg' : 'bot-msg'}>
                <b>{msg.from === 'user' ? 'You' : 'Bot'}:</b> {msg.text}
              </div>
            ))}
            {loading && <div className="bot-msg">Bot is typing...</div>}
          </div>
          <form onSubmit={handleSubmit} className="bubble-form">
            <textarea
              placeholder="Your message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              required
              disabled={loading}
            />
            <button type="submit" disabled={loading || !message.trim()}>Send</button>
          </form>
        </div>
      )}
    </div>
  );
}
