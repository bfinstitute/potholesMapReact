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
      
      {/* New Layout Container with Fixed Width Chatbot */}
      <div className="layout-container" style={{ 
        display: 'flex', 
        height: 'calc(100vh - 85px)', // Adjusted for the new header height
        margin: '10px',
        gap: '10px'
      }}>
        
        {/* Left Side - Map (takes remaining space) */}
        <div className="map-section" style={{ 
          flex: 1,
          display: 'flex', 
          flexDirection: 'column',
          borderRadius: '12px',
          overflow: 'hidden',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)'
        }}>
          {/* View Mode Buttons */}
          <div style={{ 
            margin: '10px 0', 
            textAlign: 'center',
            padding: '10px',
            backgroundColor: '#f8f9fa',
            borderBottom: '1px solid #e9ecef'
          }}>
            <button
              onClick={() => setViewMode(viewMode === 'district' ? 'circle' : 'district')}
              style={{ 
                padding: '8px 16px', 
                borderRadius: '5px', 
                border: '1px solid #1E90FF', 
                background: viewMode === 'district' ? '#1E90FF' : '#fff', 
                color: viewMode === 'district' ? '#fff' : '#1E90FF', 
                cursor: 'pointer', 
                marginRight: '10px' 
              }}
            >
              District/ZIP View
            </button>
            <button
              onClick={() => setViewMode(viewMode === 'circle' ? 'district' : 'circle')}
              style={{ 
                padding: '8px 16px', 
                borderRadius: '5px', 
                border: '1px solid #FF4500', 
                background: viewMode === 'circle' ? '#FF4500' : '#fff', 
                color: viewMode === 'circle' ? '#fff' : '#FF4500', 
                cursor: 'pointer' 
              }}
            >
              Circle/Label View
            </button>
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
        <div className="sidebar-section" style={{ 
          borderRadius: '12px',
          overflow: 'hidden',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)'
        }}>
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
