import React, { useState, useEffect } from 'react';
import MapView from './components/MapView';
import FeedbackBubble from './components/FeedbackBubble';
import IndicatorChart from './components/IndicatorChart';
import Profiles from './components/Profiles';
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
      
      {/* New Layout Container with Fixed Width Chatbot */}
      <div className="layout-container">
        {/* Left Side - Map (takes remaining space) */}
        <div className="map-section">
          {/* View Mode Buttons */}
          <div className="toggle-container">
            <div className="toggle-buttons">
              <button
                className={`toggle-button ${viewMode === 'district' ? 'active-district' : ''}`}
                onClick={() => setViewMode('district')}
              >
                District/ZIP View
              </button>
              <button
                className={`toggle-button ${viewMode === 'circle' ? 'active-circle' : ''}`}
                onClick={() => setViewMode('circle')}
              >
                Circle/Label View
              </button>
            </div>
          </div>
          
          {/* Map Component */}
          <div className="map-container" style={{ flex: 1 }}>
            <MapView
              geoData={geoData}
              params={customData || (profiles.map)}
              onAreaClick={handleAreaClick}
              highlightData={highlightData}
              viewMode={viewMode}
            />
          </div>
        </div>
        
        {/* Right Side - Chatbot (20%) */}
        <div className="sidebar-section">
          <FeedbackBubble setHighlightData={setHighlightData} />
        </div>
      </div>
      
      {/* <Footer /> */}
      {/* <IndicatorChart data={indicators} indicatorKey="value" /> */}
      {/* <Profiles profile={profiles[selectedArea]} /> */}
    </div>
  );
}

export default App;
