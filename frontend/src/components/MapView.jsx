// ZipMap.jsx
import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, Circle, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import * as turf from '@turf/turf';
import md5 from 'md5'; // for hashing
import L from 'leaflet'; // for divIcon

const targetZips = [
  "78201", "78202", "78203", "78204", "78205", "78206", "78207", "78208",
  "78209", "78210", "78211", "78212", "78213", "78214", "78215", "78216",
  "78217", "78218", "78219", "78220", "78221", "78222", "78223", "78224",
  "78225", "78226", "78227", "78228", "78229", "78230", "78231", "78232",
  "78233", "78234", "78235", "78236", "78237", "78238", "78239", "78240",
  "78241", "78242", "78243", "78244", "78245", "78246", "78247", "78248",
  "78249", "78250", "78251", "78252", "78253", "78254", "78255", "78256",
  "78257", "78258", "78259", "78260", "78261", "78262", "78263", "78264",
  "78265", "78266", "78268", "78269", "78270", "78275", "78278", "78279",
  "78280", "78283", "78284", "78285", "78286", "78287", "78288", "78289",
  "78291", "78292", "78293", "78294", "78295", "78296", "78297", "78298", "78299"
];

const mapCenter = [29.4252, -98.4946]; // Downtown San Antonio

export default function ZipMap({ highlightData, viewMode }) {
  const [zipData, setZipData] = useState(null);
  const [zipCounts, setZipCounts] = useState({}); // NEW

  useEffect(() => {
    fetch("/data/tx_zips.geojson")
      .then((res) => res.json())
      .then((data) => {
        const filtered = {
          type: "FeatureCollection",
          features: data.features.filter((f) =>
            targetZips.includes(f.properties.ZCTA5CE10 || f.properties.ZIP || f.properties.zip)
          ),
        };
        setZipData(filtered);
      });
  }, []);

  // Aggregate highlightData points to ZIPs using turf.js
  useEffect(() => {
    if (viewMode === 'district' && zipData && highlightData && Array.isArray(highlightData)) {
      const counts = {};
      highlightData.forEach((d) => {
        if (d.Latitude && d.Longitude) {
          const pt = turf.point([parseFloat(d.Longitude), parseFloat(d.Latitude)]);
          for (const feature of zipData.features) {
            if (turf.booleanPointInPolygon(pt, feature)) {
              const zip = feature.properties.ZCTA5CE10 || feature.properties.ZIP || feature.properties.zip;
              if (zip) {
                counts[zip] = (counts[zip] || 0) + (d.count || 1);
              }
              break;
            }
          }
        }
      });
      setZipCounts(counts);
    } else {
      setZipCounts({});
    }
  }, [highlightData, zipData, viewMode]);

  const highlightedZips = new Set(Object.keys(zipCounts));

  const style = (feature) => {
    if (viewMode !== 'district') return { color: '#1E90FF', weight: 1.5, fillOpacity: 0.3 };
    const zip = feature.properties.ZCTA5CE10 || feature.properties.ZIP || feature.properties.zip;
    if (highlightedZips.has(String(zip))) {
      return {
        color: "#FF4500",
        weight: 3,
        fillOpacity: 0.7,
      };
    }
    return {
      color: "#1E90FF",
      weight: 1.5,
      fillOpacity: 0.3,
    };
  };

  const onEachFeature = (feature, layer) => {
    const zip = feature.properties.ZCTA5CE10 || feature.properties.ZIP || feature.properties.zip;
    let label = `ZIP Code: ${zip}`;
    if (viewMode === 'district' && zipCounts[zip]) {
      label += `<br/>Count: ${zipCounts[zip]}`;
      // Add breakdown of streets for this ZIP
      if (highlightData && Array.isArray(highlightData)) {
        // Find all highlightData points in this ZIP
        const pointsInZip = highlightData.filter((d) => {
          if (d.Latitude && d.Longitude) {
            const pt = turf.point([parseFloat(d.Longitude), parseFloat(d.Latitude)]);
            return turf.booleanPointInPolygon(pt, feature);
          }
          return false;
        });
        // Aggregate by street name
        const streetCounts = {};
        pointsInZip.forEach((d) => {
          const street = d.MSAG_Name || d.name || d.Sensitive || 'Unknown';
          streetCounts[street] = (streetCounts[street] || 0) + (d.count || 1);
        });
        // Add breakdown to label
        Object.entries(streetCounts).forEach(([street, count]) => {
          label += `<br/>${street}: ${count}`;
        });
      }
    }
    layer.bindPopup(label);
    layer.on({
      mouseover: (e) => {
        e.target.setStyle({
          weight: 3,
          color: "#FFD700",
          fillOpacity: 0.6,
        });
      },
      mouseout: (e) => {
        // Restore the correct style based on highlight data
        e.target.setStyle(style(feature));
      },
    });
  };

  // Generate a unique key for GeoJSON to force re-render on highlightData/viewMode change
  const geoJsonKey = md5(JSON.stringify({ zipCounts, viewMode }));

  return (
    <MapContainer center={mapCenter} zoom={10} scrollWheelZoom={false} style={{ height: "100vh", width: "100%" }}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {zipData && viewMode === 'district' && (
        <>
          <GeoJSON key={geoJsonKey} data={zipData} style={style} onEachFeature={onEachFeature} />
        </>
      )}
      {highlightData && Array.isArray(highlightData) && viewMode === 'circle' && highlightData.map((d, i) => {
        if (d.Latitude && d.Longitude) {
          const color = d.color || '#FF0000';
          const radius = d.marker_radius || 12;
          const label = d.count || d.Count || d.complaint_count || d.value || 1;
          return (
            <Circle
              key={i}
              center={[d.Latitude, d.Longitude]}
              radius={radius * 10}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.7 }}
            >
              <Popup>
                {(d.MSAG_Name || d.name || d.Sensitive || 'Highlighted Location') + ` (Count: ${label})`}
              </Popup>
            </Circle>
          );
        }
        return null;
      })}
    </MapContainer>
  );
}
