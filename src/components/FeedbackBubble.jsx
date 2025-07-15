import { useState } from 'react';
import '../styles/FeedbackBubble.css';

export default function FeedbackBubble() {
  const [isOpen, setIsOpen] = useState(false);
  const [feedback, setFeedback] = useState({ name: '', message: '' });

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log('Feedback submitted:', feedback);
    setIsOpen(false);
    setFeedback({ name: '', message: '' });
    alert('Thank you for your feedback!');
  };

  return (
    <div className="feedback-bubble">
      {!isOpen ? (
        <button className="open-button" onClick={() => setIsOpen(true)}>
          💬 Feedback
        </button>
      ) : (
        <div className="bubble-popup">
          <div className="bubble-header">
            <span>Send Feedback</span>
            <button onClick={() => setIsOpen(false)}>×</button>
          </div>
          <form onSubmit={handleSubmit} className="bubble-form">
            <input
              type="text"
              placeholder="Your name"
              value={feedback.name}
              onChange={(e) => setFeedback({ ...feedback, name: e.target.value })}
              required
            />
            <textarea
              placeholder="Your message"
              value={feedback.message}
              onChange={(e) => setFeedback({ ...feedback, message: e.target.value })}
              required
            />
            <button type="submit">Submit</button>
          </form>
        </div>
      )}
    </div>
  );
}
