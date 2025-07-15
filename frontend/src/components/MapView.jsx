// ZipMap.jsx
import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import "leaflet/dist/leaflet.css";

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

export default function ZipMap() {
  const [zipData, setZipData] = useState(null);

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

  const style = {
    color: "#1E90FF",
    weight: 1.5,
    fillOpacity: 0.3,
  };

  const onEachFeature = (feature, layer) => {
    const zip = feature.properties.ZCTA5CE10 || feature.properties.ZIP || feature.properties.zip;
    layer.bindPopup(`ZIP Code: ${zip}`);
    layer.on({
      mouseover: (e) => {
        e.target.setStyle({
          weight: 3,
          color: "#FFD700",
          fillOpacity: 0.6,
        });
      },
      mouseout: (e) => {
        e.target.setStyle(style);
      },
    });
  };

  return (
    <MapContainer center={mapCenter} zoom={10} scrollWheelZoom={false} style={{ height: "100vh", width: "100%" }}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {zipData && (
        <GeoJSON data={zipData} style={style} onEachFeature={onEachFeature} />
      )}
    </MapContainer>
  );
}
