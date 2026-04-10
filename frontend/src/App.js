import React, { useState, useEffect, useRef } from 'react';
import MapView from './components/MapView';
import ChartView from './components/ChartView';
import FeedbackBubble from './components/FeedbackBubble';
import bfiIcon from './assets/images/BFI_LogoIcon.svg';
import downloadIcon from './assets/images/iconoir_download.svg';
import html2canvas from 'html2canvas';
import domtoimage from 'dom-to-image-more';
import sparkIcon from './assets/images/Icon=spark.svg';
import './App.css';
import { fetchGeoData, fetchIndicators, fetchProfile } from './services/dataService';

// Inline SVG icons for the sidebar
const IconEdit = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M13.0207 5.82839L15.8491 2.99996L20.7988 7.94971L17.9704 10.7781M13.0207 5.82839L3.41406 15.435C3.22659 15.6225 3.12134 15.8769 3.12134 16.1421V20.6776H7.65685C7.92207 20.6776 8.17642 20.5723 8.36388 20.3849L17.9704 10.7781M13.0207 5.82839L17.9704 10.7781"/>
  </svg>
);

const IconSearch = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="10.5" cy="10.5" r="6.5"/>
    <path d="M15.5 15.5L20 20"/>
  </svg>
);

const IconBookmark = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 6a2 2 0 012-2h10a2 2 0 012 2v14l-7-3.5L5 20V6z"/>
  </svg>
);

const IconDatabase = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <ellipse cx="12" cy="6" rx="8" ry="3"/>
    <path d="M4 6v6c0 1.657 3.582 3 8 3s8-1.343 8-3V6"/>
    <path d="M4 12v6c0 1.657 3.582 3 8 3s8-1.343 8-3v-6"/>
  </svg>
);

const IconDots = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="5" cy="12" r="1" fill="currentColor"/>
    <circle cx="12" cy="12" r="1" fill="currentColor"/>
    <circle cx="19" cy="12" r="1" fill="currentColor"/>
  </svg>
);

const IconBookmarkTop = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 6a2 2 0 012-2h10a2 2 0 012 2v14l-7-3.5L5 20V6z"/>
  </svg>
);

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
  const [isLoading, setIsLoading] = useState(false);
  const panelRef = useRef(null);

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

  const handleDownload = async () => {
    if (!panelRef.current || isLoading) return;
    const filename = `${mapTitle.replace(/\s+/g, '_') || 'visualization'}.png`;
    try {
      if (chartData) {
        // Charts: html2canvas works fine
        const canvas = await html2canvas(panelRef.current, { useCORS: true, logging: false });
        triggerDownload(canvas.toDataURL('image/png'), filename);
      } else {
        // Maps: dom-to-image-more uses the browser's SVG renderer which correctly
        // handles Leaflet's CSS transforms, keeping tiles and overlays aligned.
        const mapEl = panelRef.current.querySelector('.leaflet-container') || panelRef.current;
        const dataUrl = await domtoimage.toPng(mapEl, {
          width: mapEl.offsetWidth,
          height: mapEl.offsetHeight,
        });
        triggerDownload(dataUrl, filename);
      }
    } catch (e) {
      console.error('Download failed:', e);
    }
  };

  const triggerDownload = (dataUrl, filename) => {
    const link = document.createElement('a');
    link.download = filename;
    link.href = dataUrl;
    link.click();
  };

  const handleCloseMap = () => {
    setMapTitle('New conversation');
    setHighlightData(null);
    handleSetChartData(null);
  };

  const titleIconColor = chartData ? '#FF5C17' : '#00B89C';
  const hasVisualization = mapTitle !== 'New conversation';

  return (
    <div className="app-wrapper">
      {/* Top Bar */}
      <div className="top-bar">
        <div className="top-bar-left">
          <img src={bfiIcon} alt="Buffi" className="top-bar-logo" />
          <span className="top-bar-brand">Buffi V.02</span>
          <button className="top-bar-icon-btn">
            <IconDots />
          </button>
        </div>

        <div className="top-bar-center">
          {hasVisualization && (
            <>
              <button className="map-title-close" onClick={handleCloseMap}>✕</button>
              <span className="map-title-dot" style={{ background: titleIconColor }} />
            </>
          )}
          <span className="map-title-text">{mapTitle}</span>
          {hasVisualization && (
            <button className="map-title-chevron">∨</button>
          )}
        </div>

        <div className="top-bar-right">
          <button className="top-bar-icon-btn" title="Bookmark">
            <IconBookmarkTop />
          </button>
          <button className="top-bar-icon-btn" title="Download" onClick={handleDownload} disabled={isLoading}>
            <img src={downloadIcon} alt="download" className="top-bar-icon" />
          </button>
          <button className="top-bar-icon-btn" title="More">
            <IconDots />
          </button>
          <button className="share-btn">
            Share <span className="share-chevron">∨</span>
          </button>
        </div>
      </div>

      {/* Main Layout */}
      <div className="main-layout">
        {/* Left icon strip */}
        <div className="left-icon-strip">
          <button className="icon-strip-btn" title="New chat">
            <IconEdit />
          </button>
          <button className="icon-strip-btn" title="Search">
            <IconSearch />
          </button>
          <button className="icon-strip-btn" title="Saved">
            <IconBookmark />
          </button>
          <button className="icon-strip-btn" title="Data">
            <IconDatabase />
          </button>
          <button className="icon-strip-btn" title="Spark">
            <img src={sparkIcon} alt="spark" className="strip-icon" />
          </button>
          <div className="strip-avatar" />
        </div>

        {/* Chat Panel */}
        <div className="chat-panel">
          <FeedbackBubble
            setHighlightData={setHighlightData}
            setChartData={handleSetChartData}
            setMapTitle={setMapTitle}
            chartType={chartType}
            setChartType={setChartType}
            setIsLoading={setIsLoading}
          />
        </div>

        {/* Visualization Panel — shows loading, chart, or map */}
        <div className={`map-panel${isLoading ? ' map-panel--loading' : ''}`} ref={panelRef}>
          {isLoading ? (
            <div className="loading-visual">
              <div className="loading-visual-inner">
                <svg className="loading-spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
                </svg>
                <span className="loading-visual-text">Loading Visual...</span>
              </div>
              <div className="loading-progress-track">
                <div className="loading-progress-bar" />
              </div>
            </div>
          ) : chartData ? (
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
