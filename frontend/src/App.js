import React, { useState, useEffect } from 'react';
import MapView from './components/MapView';
import ChartView from './components/ChartView';
import FeedbackBubble from './components/FeedbackBubble';
import bfiIcon from './assets/images/BFI_LogoIcon.svg';
import menuIcon from './assets/images/iconoir_menu.svg';
import downloadIcon from './assets/images/iconoir_download.svg';
import enlargeIcon from './assets/images/iconoir_enlarge.svg';
import dataIcon from './assets/images/Icon=data-transfer-both.svg';
import './App.css';
import { fetchGeoData, fetchIndicators, fetchProfile } from './services/dataService';

function App() {
  const [geoData, setGeoData] = useState(null);
  const [indicators, setIndicators] = useState([]);
  const [profiles, setProfiles] = useState({});
  const [selectedArea, setSelectedArea] = useState(null);
  const [customData, setCustomData] = useState(null);
  const [highlightData, setHighlightData] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [chartType, setChartType] = useState('bar');
  const [mapTitle, setMapTitle] = useState('New conversation');
  const [viewMode] = useState('circle');

  // Reset chart type to bar whenever a new chart response arrives
  const handleSetChartData = (data) => {
    setChartData(data);
    if (data) setChartType('bar');
  };

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

  const handleCloseMap = () => {
    setMapTitle('New conversation');
    setHighlightData(null);
    handleSetChartData(null);
  };

  return (
    <div className="app-wrapper">
      {/* Top Bar */}
      <div className="top-bar">
        <div className="top-bar-left">
          <img src={bfiIcon} alt="Buffi" className="top-bar-logo" />
          <span className="top-bar-brand">Buffi nv.p.02</span>
          <button className="top-bar-icon-btn">
            <img src={menuIcon} alt="menu" className="top-bar-icon" />
          </button>
        </div>

        <div className="top-bar-center">
          {mapTitle !== 'New conversation' && (
            <>
              <button className="map-title-close" onClick={handleCloseMap}>✕</button>
              <span className="map-title-dot" />
            </>
          )}
          <span className="map-title-text">{mapTitle}</span>
          {mapTitle !== 'New conversation' && (
            <button className="map-title-chevron">∨</button>
          )}
        </div>

        <div className="top-bar-right">
          <button className="top-bar-icon-btn" title="Save">
            <img src={downloadIcon} alt="save" className="top-bar-icon" />
          </button>
          <button className="top-bar-icon-btn" title="Expand">
            <img src={enlargeIcon} alt="expand" className="top-bar-icon" />
          </button>
          <button className="top-bar-icon-btn" title="More">
            <img src={menuIcon} alt="more" className="top-bar-icon" />
          </button>
        </div>
      </div>

      {/* Main Layout */}
      <div className="main-layout">
        {/* Left icon strip */}
        <div className="left-icon-strip">
          <button className="icon-strip-btn" title="Menu">
            <img src={menuIcon} alt="menu" className="strip-icon" />
          </button>
          <button className="icon-strip-btn" title="Data">
            <img src={dataIcon} alt="data" className="strip-icon" />
          </button>
        </div>

        {/* Chat Panel */}
        <div className="chat-panel">
          <FeedbackBubble
            setHighlightData={setHighlightData}
            setChartData={handleSetChartData}
            setMapTitle={setMapTitle}
            chartType={chartType}
            setChartType={setChartType}
          />
        </div>

        {/* Visualization Panel — shows chart or map */}
        <div className="map-panel">
          {chartData ? (
            <ChartView chartData={chartData} chartType={chartType} />
          ) : (
            <MapView
              geoData={geoData}
              params={customData || profiles.map}
              onAreaClick={handleAreaClick}
              highlightData={highlightData}
              viewMode={viewMode}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
