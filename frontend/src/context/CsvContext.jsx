// src/components/CsvContext.jsx
import React, { createContext, useState, useContext } from 'react';

const CsvContext = createContext();

export const INITIAL_BATCHES = [];

export function CsvProvider({ children }) {
  const [csvData, setCsvData] = useState([]);
  const [fileName, setFileName] = useState('');
  const [csvStats, setCsvStats] = useState(null);
  const [csvAnalysis, setCsvAnalysis] = useState(null);
  const [columnDescriptions, setColumnDescriptions] = useState({});
  const [batches, setBatches] = useState(INITIAL_BATCHES);

  return (
    <CsvContext.Provider value={{
      csvData,
      setCsvData,
      fileName,
      setFileName,
      csvStats,
      setCsvStats,
      csvAnalysis,
      setCsvAnalysis,
      columnDescriptions,
      setColumnDescriptions,
      batches,
      setBatches,
    }}>
      {children}
    </CsvContext.Provider>
  );
}

// Custom hook for convenience
export function useCsv() {
  return useContext(CsvContext);
}
