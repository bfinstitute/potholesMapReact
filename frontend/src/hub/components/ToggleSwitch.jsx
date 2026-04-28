import React, { useState } from 'react';
import '../styles/ToggleSwitch.css';
import CSVPreview from './CSVPreview';
import CSVFeedbackForm from './CSVFeedbackForm';

const ToggleSwitch = () => {
  const [selected, setSelected] = useState('A');

  return (
    <div className="toggle-container">
      <div className="toggle-buttons">
        <button
          className={`toggle-button ${selected === 'A' ? 'active' : ''}`}
          onClick={() => setSelected('A')}
        >
          Table Preview
        </button>
        <button
          className={`toggle-button ${selected === 'B' ? 'active' : ''}`}
          onClick={() => setSelected('B')}
        >
          Feedback
        </button>
      </div>

      {selected === 'A' ? <CSVPreview /> : <CSVFeedbackForm />}
    </div>
  );
};

export default ToggleSwitch;
