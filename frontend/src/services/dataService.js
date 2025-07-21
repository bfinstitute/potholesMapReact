// using public hardcoded files in public folder
import axios from 'axios';

export async function fetchGeoData() {
  const res = await axios.get('/geo.json'); // From /public
  return res.data;
}

export async function fetchIndicators() {
  const res = await axios.get('/indicators.json'); // From /public
  return res.data;
}

export async function fetchProfile(areaId) {
  const res = await axios.get(`/profiles/${areaId}.json`);
  return res.data;
}


// import axios from 'axios';

// export async function fetchGeoData() {
//   const res = await axios.get('/path/to/geojson'); 
//   return res.data;
// }

// export async function fetchIndicators() {
//   const res = await axios.get('/api/indicators');
//   return res.data;
// }

// export async function fetchProfile(areaId) {
//   const res = await axios.get(`/api/profiles/${areaId}`);
//   return res.data;
// }
