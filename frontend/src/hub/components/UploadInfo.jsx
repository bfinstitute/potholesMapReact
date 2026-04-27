// src/components/UploadInfo.jsx

import React from 'react';
import '../styles/UploadInfo.css'; // Assuming you'll have a corresponding CSS file

const UploadInfo = () => {
  return (
    <div className="upload-info">
      <h1>Upload Your CSV to the Buffi V.01</h1>
      <p>
        First, attach your CSV file below. We'll then securely process your data and present a brief preview to ensure
        everything looks correct. Once you've confirmed your data, you'll use the 'Upload to Buffi' button to finalize the
        upload and proceed to your dashboard for visual insights.
      </p>
    </div>
  );
};

export default UploadInfo;