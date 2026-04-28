// src/components/CsvContext.jsx
import React, { createContext, useState, useContext } from 'react';

const CsvContext = createContext();

const INITIAL_BATCH_FILES = [
  { id: 1, name: 'zoning_classification_map.csv',     folder: 'Housing',        status: 'Error',  tier: 'Tier 1: Public',               size: '1.2 MB', confidence: 'Low',  issue: 'Row values unclear — the field "geo_ref" could not be interpreted. Please clarify what this column represents.' },
  { id: 2, name: 'housing_shortfall_by_district.csv', folder: 'Housing',        status: 'Error',  tier: 'Tier 1: Public',               size: '1.2 MB', confidence: 'Low',  issue: 'The field "geo_ref" could not be interpreted. Please clarify what this column represents.' },
  { id: 3, name: 'sa_housing_gap_analysis.csv',       folder: 'Housing',        status: 'Ready',  tier: 'Tier 2: Internal Operational', size: '1.2 MB', confidence: 'High', issue: '' },
  { id: 4, name: 'permit_activity_vs_demand.csv',     folder: 'Safety',         status: 'Ready',  tier: 'Tier 3: Restricted',           size: '1.2 MB', confidence: 'High', issue: '' },
  { id: 5, name: 'sa_landuse_zoning2026.csv',         folder: 'Infrastructure', status: 'Ready',  tier: 'Tier 3: Restricted',           size: '1.2 MB', confidence: 'High', issue: '' },
];

export const INITIAL_BATCHES = [
  { id: 1, label: 'April 2nd 2025 3:51 PM Queue', files: INITIAL_BATCH_FILES },
];

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
