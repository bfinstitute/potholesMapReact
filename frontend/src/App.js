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
        <MapView
          geoData={geoData}
          params={customData || (profiles.map)}
          onAreaClick={handleAreaClick}
        />
        <FeedbackBubble />
      </div>
      <Footer />
      {/* <IndicatorChart data={indicators} indicatorKey="value" /> */}
      {/* <Profiles profile={profiles[selectedArea]} /> */}
    </div>
  );
}

export default App;
