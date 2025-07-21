import Papa from 'papaparse';
import '../styles/CsvUploader.css';

export default function CsvUploader({ onCsvLoad }) {
  const handleUpload = e => {
    const file = e.target.files[0];
    if (!file) return;
    Papa.parse(file, {
      header: true,
      dynamicTyping: true,
      complete: results => onCsvLoad(results.data)
    });
  };

  return (
    <div className="upload-container" id="upload">
      <label htmlFor="csv-input" className="upload-label">
        Upload Custom CSV:
      </label>
      <input
        id="csv-input"
        type="file"
        accept=".csv"
        onChange={handleUpload}
        className="upload-input"
      />
    </div>
  );
}
