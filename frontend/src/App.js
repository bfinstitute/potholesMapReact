import React, { useState, useEffect } from 'react';
import MapView from './components/MapView';
import FeedbackBubble from './components/FeedbackBubble';
import IndicatorChart from './components/IndicatorChart';
import Profiles from './components/Profiles';
import CsvUploader from './components/CsvUploader';
import Header from './components/header';
import logo from './logo.svg';
import './App.css';
import { fetchGeoData, fetchIndicators, fetchProfile } from './services/dataService';
import Footer from './components/Footer';

function App() {
  const [geoData, setGeoData] = useState(null);
  const [indicators, setIndicators] = useState([]);
  const [profiles, setProfiles] = useState({});
  const [selectedArea, setSelectedArea] = useState(null);
  const [customData, setCustomData] = useState(null);
  const [highlightData, setHighlightData] = useState(null);
  const [viewMode, setViewMode] = useState('district'); // NEW

  useEffect(() => {
    fetchGeoData().then(setGeoData);
    fetchIndicators().then(data => {
      setIndicators(data);
      const map = {};
      data.forEach(d => (map[d.areaId] = d.value));
      setProfiles(prev => ({ ...prev, map }));
    });
  }, []);

  const handleAreaClick = id => {
    fetchProfile(id).then(profile => {
      setProfiles(prev => ({ ...prev, [id]: profile }));
      setSelectedArea(id);
    });
  };

  const handleCsvLoad = rows => {
    const map = {};
    rows.forEach(r => map[r.areaId] = r.value);
    setCustomData(map);
  };

  return (
    <div>
      <Header />
      {/* <CsvUploader onCsvLoad={handleCsvLoad} /> */}
      <div style={{ position: 'relative' }}>
        <div style={{ margin: '10px 0', textAlign: 'center' }}>
          <button
            onClick={() => setViewMode(viewMode === 'district' ? 'circle' : 'district')}
            style={{ padding: '8px 16px', borderRadius: '5px', border: '1px solid #1E90FF', background: viewMode === 'district' ? '#1E90FF' : '#fff', color: viewMode === 'district' ? '#fff' : '#1E90FF', cursor: 'pointer', marginRight: '10px' }}
          >
            District/ZIP View
          </button>
          <button
            onClick={() => setViewMode(viewMode === 'circle' ? 'district' : 'circle')}
            style={{ padding: '8px 16px', borderRadius: '5px', border: '1px solid #FF4500', background: viewMode === 'circle' ? '#FF4500' : '#fff', color: viewMode === 'circle' ? '#fff' : '#FF4500', cursor: 'pointer' }}
          >
            Circle/Label View
          </button>
        </div>
        <MapView
          geoData={geoData}
          params={customData || (profiles.map)}
          onAreaClick={handleAreaClick}
          highlightData={highlightData}
          viewMode={viewMode} // NEW
        />
        <FeedbackBubble setHighlightData={setHighlightData} />
      </div>
      <Footer />
      {/* <IndicatorChart data={indicators} indicatorKey="value" /> */}
      {/* <Profiles profile={profiles[selectedArea]} /> */}
    </div>
  );
}

export default App;
