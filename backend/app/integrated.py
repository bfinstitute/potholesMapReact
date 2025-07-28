import pandas as pd
import folium
import geopandas as gpd
import requests
import json
import os
import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import hashlib
from functools import lru_cache
import inspect

global pothole_cases_df, pavement_latlon_df, complaint_df # Declare globals here

# Helper function to convert numeric types in DataFrame to native Python types
def _convert_dataframe_numerics_to_native_types(df):
    for col in df.columns:
        if pd.api.types.is_integer_dtype(df[col]):
            df[col] = df[col].apply(lambda x: int(x) if pd.notna(x) else None)
        elif pd.api.types.is_float_dtype(df[col]):
            df[col] = df[col].apply(lambda x: float(x) if pd.notna(x) else None)
    return df

# Initialize the base map globally in session state, only once
# if "m" not in st.session_state:
#     st.session_state.m = folium.Map(location=center, zoom_start=zoom_start)
#     st.session_state.highlight_feature_group = folium.FeatureGroup(name="Highlighted Streets").add_to(st.session_state.m)

# Access the map and feature group from session state
# m = st.session_state.m
# highlight_feature_group = st.session_state.highlight_feature_group

# ---------- Groq AI Configuration ----------
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Initialize global DataFrames
pothole_cases_df = pd.DataFrame()
pavement_latlon_df = pd.DataFrame()
complaint_df = pd.DataFrame()

# --- DATA STUBS FOR EXTERNAL DATASETS (replace with real data as available) ---
# Example: schools_df = pd.read_csv('Data/schools.csv')
schools_df = pd.DataFrame(columns=['name', 'lat', 'lon'])  # TODO: Replace with real school data
hospitals_df = pd.DataFrame(columns=['name', 'lat', 'lon'])  # TODO: Replace with real hospital data
senior_centers_df = pd.DataFrame(columns=['name', 'lat', 'lon'])  # TODO: Replace with real senior center data
injuries_df = pd.DataFrame(columns=['intersection', 'lat', 'lon', 'injury_count'])  # TODO: Replace with real injury data

# --- Load VIA stops and routes ---
if os.path.exists('../Data/VIA/stops_cleaned.csv'):
    via_stops_df = pd.read_csv('../Data/VIA/stops_cleaned.csv')
else:
    via_stops_df = pd.DataFrame()
if os.path.exists('../Data/VIA/via_routes_cleaned.csv'):
    via_routes_df = pd.read_csv('../Data/VIA/via_routes_cleaned.csv')
else:
    via_routes_df = pd.DataFrame()

# --- Load sensitive locations from extracted CSV ---
import re
try:
    sensitive_locations_df = pd.read_csv('../Data/possible_sensitive_locations.csv')
    # Extract lat/lon from GoogleMapView column
    def extract_lat_lon(url):
        if pd.isna(url) or url == 'Not Available':
            return None, None
        match = re.search(r'place/(\d+\.\d+)N (\d+\.\d+)W', url)
        if match:
            lat = float(match.group(1))
            lon = -float(match.group(2))  # West is negative
            return lat, lon
        return None, None
    sensitive_locations_df[['lat', 'lon']] = sensitive_locations_df['GoogleMapView'].apply(lambda x: pd.Series(extract_lat_lon(x)))
    sensitive_locations_df = sensitive_locations_df.dropna(subset=['lat', 'lon', 'MSAG_Name'])
    sensitive_locations_df = sensitive_locations_df.rename(columns={'MSAG_Name': 'name'})
    sensitive_locations_df = sensitive_locations_df[['name', 'lat', 'lon']]
except Exception as e:
    sensitive_locations_df = pd.DataFrame(columns=['name','lat','lon'])

# --- Utility: Geospatial join (point-in-radius) ---
def points_within_radius(points_df, center_lat, center_lon, radius_m):
    gdf_points = gpd.GeoDataFrame(points_df.copy(), geometry=gpd.points_from_xy(points_df.lon, points_df.lat), crs='EPSG:4326')
    center = gpd.GeoSeries([gpd.points_from_xy([center_lon], [center_lat])[0]], crs='EPSG:4326').to_crs(epsg=3857)
    gdf_points_proj = gdf_points.to_crs(epsg=3857)
    buffer = center.buffer(radius_m)
    return gdf_points_proj[gdf_points_proj.geometry.within(buffer.iloc[0])]

# --- Utility: Fast Geocoding with Caching ---
def geocode_address(address):
    @lru_cache(maxsize=1000) # Cache results to avoid repeated API calls
    def _geocode(addr):
        url = f"https://nominatim.openstreetmap.org/search"
        params = {"q": addr, "format": "json", "limit": 1}
        try:
            resp = requests.get(url, params=params, headers={"User-Agent": "pothole-bot"}, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception:
            return None, None
        return None, None
    return _geocode(address)

# --- Utility: Convert pavement_latlon_df to GeoDataFrame ---
def get_pavement_gdf():
    if not hasattr(get_pavement_gdf, "gdf"):
        if not pavement_latlon_df.empty and "Latitude" in pavement_latlon_df.columns and "Longitude" in pavement_latlon_df.columns:
            gdf = gpd.GeoDataFrame(
                pavement_latlon_df.copy(),
                geometry=gpd.points_from_xy(pavement_latlon_df.Longitude, pavement_latlon_df.Latitude),
                crs="EPSG:4326"
            )
            get_pavement_gdf.gdf = gdf
        else:
            get_pavement_gdf.gdf = gpd.GeoDataFrame()
    return get_pavement_gdf.gdf

# --- Improved Handler: Active pothole complaints within the area of a school zone, senior center, or hospital ---
def handle_active_complaints_near_sensitive_areas(radius_m=300, sensitive_type='school'):
    # Map user type to possible keywords in the name
    type_keywords = {
        'school': ['school'],
        'hospital': ['hospital', 'medical', 'clinic'],
        'senior': ['senior', 'elder', 'center', 'elderberry', 'elderwood', 'elderpath']
    }
    keywords = type_keywords.get(sensitive_type, [sensitive_type])
    # Filter unresolved complaints (active)
    if complaint_df.empty or 'Latitude' not in complaint_df.columns or 'Longitude' not in complaint_df.columns:
        return "Complaint data with location is required for this analysis.", None, pd.DataFrame()
    unresolved = complaint_df[complaint_df['CLOSEDDATETIME'].isna() & complaint_df['Latitude'].notna() & complaint_df['Longitude'].notna()]
    print(f"DEBUG: Number of unresolved complaints: {len(unresolved)}")
    # Use extracted sensitive locations, filter for any keyword in name
    pattern = '|'.join(keywords)
    sensitive = sensitive_locations_df[sensitive_locations_df['name'].str.contains(pattern, case=False, na=False)].copy()
    print(f"DEBUG: Number of sensitive locations ({sensitive_type}): {len(sensitive)}")
    if sensitive.empty:
        return f"No sensitive {sensitive_type} location data available.", None, pd.DataFrame()
    summary = []
    highlight_rows = []
    for _, row in sensitive.iterrows():
        lat, lon, name = row['lat'], row['lon'], row['name']
        if pd.isna(lat) or pd.isna(lon):
            continue
        near = unresolved[((unresolved['Latitude'] - float(lat))**2 + (unresolved['Longitude'] - float(lon))**2).pow(0.5) < (radius_m/111320)]
        count = len(near)
        if count > 0:
            summary.append(f"{count} active complaint(s) near {name}")
            for _, c in near.iterrows():
                highlight_rows.append({
                    'Sensitive': name,
                    'ComplaintID': c.get('ComplaintID', ''),
                    'Latitude': c['Latitude'],
                    'Longitude': c['Longitude'],
                    'color': 'red',
                    'marker_radius': 10
                })
    if not summary:
        return f"No active pothole complaints found near any {sensitive_type} zone.", None, pd.DataFrame()
    highlight_df = pd.DataFrame(highlight_rows)
    response = f"Active pothole complaints near {sensitive_type} zones: " + "; ".join(summary)
    return response, None, highlight_df

# --- Handler: Intersections with VIA stops, high pothole & injury rates ---
def handle_intersections_via_pothole_injury(top_n=5):
    # Stub: join stops, complaints, and injuries at intersections
    if injuries_df.empty or via_stops_df.empty or complaint_df.empty:
        return "Required data (injuries, VIA stops, complaints) not available.", None, pd.DataFrame()
    # For demo: just return a stub message
    return "This analysis requires intersection and injury data. Please provide a dataset with intersection locations and injury counts.", None, pd.DataFrame()

# --- Handler: Prioritize maintenance for bus damage/delays ---
def handle_prioritize_maintenance_for_buses():
    # Overlay VIA routes, complaint density, and PCI
    if via_routes_df.empty or pavement_latlon_df.empty or complaint_df.empty:
        return "Required data (VIA routes, pavement, complaints) not available.", None, pd.DataFrame()
    # For demo: just return a stub message
    return "This analysis requires VIA route geometry and pavement condition data. Please provide route shapes and PCI scores.", None, pd.DataFrame()

# --- Handler: History of repeated pothole complaints along a road ---
def handle_repeated_complaints_on_road(road):
    if complaint_df.empty or 'MSAG_Name' not in complaint_df.columns:
        return "Complaint data with road names is required.", None, pd.DataFrame()
    road_complaints = complaint_df[complaint_df['MSAG_Name'].str.contains(road, case=False, na=False)]
    if road_complaints.empty:
        return f"No complaints found for road '{road}'.", None, pd.DataFrame()
    trend = road_complaints.groupby(road_complaints['OPENEDDATETIME'].dt.to_period('M')).size()
    response = f"Complaint history for {road}:\n" + '\n'.join([f"{str(idx)}: {val}" for idx, val in trend.items()])
    return response, None, pd.DataFrame()

# --- Handler: Bus stops near high-risk pavement ---
def handle_bus_stops_near_high_risk_pavement(pci_threshold=50, radius_m=100):
    if via_stops_df.empty or pavement_latlon_df.empty:
        return "VIA stops and pavement data required.", None, pd.DataFrame()
    high_risk = pavement_latlon_df[pavement_latlon_df['PCI'] < pci_threshold]
    if high_risk.empty:
        return "No high-risk pavement segments found.", None, pd.DataFrame()
    results = []
    for _, stop in via_stops_df.iterrows():
        near = high_risk[((high_risk['Latitude'] - stop['stop_lat'])**2 + (high_risk['Longitude'] - stop['stop_lon'])**2).pow(0.5) < (radius_m/111320)]
        for _, seg in near.iterrows():
            results.append({'Stop': stop['stop_name'], 'Latitude': seg['Latitude'], 'Longitude': seg['Longitude']})
    if not results:
        return "No bus stops found near high-risk pavement.", None, pd.DataFrame()
    highlight_df = pd.DataFrame(results)
    highlight_df['color'] = 'purple'
    highlight_df['marker_radius'] = 10
    return f"Found {len(highlight_df)} bus stops near high-risk pavement.", None, highlight_df

# --- Handler: Will I face potholes on the way to [area]? ---
def handle_potholes_on_route(destination, origin="San Antonio, TX", buffer_m=50):
    lat1, lon1 = geocode_address(origin)
    lat2, lon2 = geocode_address(destination)
    if None in (lat1, lon1, lat2, lon2):
        return f"Could not geocode the route from '{origin}' to '{destination}'.", None, pd.DataFrame()
    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    try:
        resp = requests.get(osrm_url, timeout=5)
        resp.raise_for_status()
        route = resp.json()["routes"][0]["geometry"]["coordinates"]
        route_points = [gpd.points_from_xy([pt[0]], [pt[1]])[0] for pt in route]
        route_line = gpd.GeoSeries([gpd.GeoSeries(route_points).union_all().convex_hull], crs="EPSG:4326")
        route_proj = route_line.to_crs(epsg=3857)
        route_buffer = route_proj.buffer(buffer_m)
        gdf = get_pavement_gdf()
        if gdf.empty:
            return "No pavement location data available.", None, pd.DataFrame()
        gdf_proj = gdf.to_crs(epsg=3857)
        on_route = gdf_proj[gdf_proj.geometry.within(route_buffer.iloc[0])]
        count = len(on_route)
        if count == 0:
            return f"No potholes found along the route to '{destination}'.", None, pd.DataFrame()
        highlight_df = on_route.to_crs(epsg=4326)[["Latitude", "Longitude", "MSAG_Name"]].copy()
        highlight_df["color"] = "purple"
        highlight_df["marker_radius"] = 10
        return f"There are {count} pothole(s) along the route to '{destination}'.", None, highlight_df
    except Exception:
        return "Could not retrieve route information. Please try again later.", None, pd.DataFrame()

# --- Handler: Are there potholes near [address]? ---
def handle_potholes_near_address(address, radius_m=500):
    lat, lon = geocode_address(address)
    if lat is None or lon is None:
        return f"Could not geocode the address '{address}'. Please check the address and try again.", None, pd.DataFrame()
    gdf = get_pavement_gdf()
    if gdf.empty:
        return "No pavement location data available.", None, pd.DataFrame()
    gdf_proj = gdf.to_crs(epsg=3857)
    point = gpd.GeoSeries([gpd.points_from_xy([lon], [lat])[0]], crs="EPSG:4326").to_crs(epsg=3857)
    buffer = point.buffer(radius_m)
    nearby = gdf_proj[gdf_proj.geometry.within(buffer.iloc[0])]
    count = len(nearby)
    if count == 0:
        return f"No potholes found within {radius_m} meters of '{address}'.", None, pd.DataFrame()
    highlight_df = nearby.to_crs(epsg=4326)[["Latitude", "Longitude", "MSAG_Name"]].copy()
    highlight_df["color"] = "red"
    highlight_df["marker_radius"] = 10
    return f"Found {count} pothole(s) within {radius_m} meters of '{address}'.", None, highlight_df

# --- Analysis Functions (from Visualization.ipynb) ---

@lru_cache(maxsize=1) # Cache the loaded data
def load_pothole_cases_data(path):
    try:
        df = pd.read_csv(path)
        df['OpenDate'] = pd.to_datetime(df['OpenDate'])
        # st.success(f"Successfully loaded {os.path.basename(path)}")
        return df
    except Exception as e:
        print(f"File not found or error loading {os.path.basename(path)}: {e}. Some chatbot features may be limited.")
        return pd.DataFrame()

@lru_cache(maxsize=1) # Cache the loaded data
def load_pavement_data(path):
    try:
        df = pd.read_csv(path)
        # Extract latitude and longitude from 'GoogleMapView' column
        def extract_lat_lon(url):
            if pd.isna(url) or url == 'Not Available':
                return None, None
            match = re.search(r'place/(-?\d+\.?\d*)[NS]\s*(-?\d+\.?\d*)([EW])', url)
            if match:
                lat = float(match.group(1))
                lon_numeric = float(match.group(2))
                lon_direction = match.group(3)
                
                lon = lon_numeric
                if lon_direction == 'W': # Adjust longitude sign if it's West
                    lon = -abs(lon)
                return lat, lon
            return None, None

        df[['Latitude', 'Longitude']] = df['GoogleMapView'].apply(
            lambda x: pd.Series(extract_lat_lon(x))
        )
        df = df.dropna(subset=['MSAG_Name', 'Latitude', 'Longitude'])
        # st.success(f"Successfully loaded and cleaned {os.path.basename(path)}")
        return df
    except Exception as e:
        print(f"File not found or error loading {os.path.basename(path)}: {e}. Some chatbot features may be limited.")
        return pd.DataFrame()

@lru_cache(maxsize=1) # Cache the loaded data
def load_complaint_data(path):
    try:
        df = pd.read_csv(path, low_memory=False)
        df['OPENEDDATETIME'] = pd.to_datetime(df['OPENEDDATETIME'], errors='coerce')
        df['InstallDate'] = pd.to_datetime(df['InstallDate'], errors='coerce')
        # st.success(f"Successfully loaded and cleaned {os.path.basename(path)}")
        return df
    except Exception as e:
        print(f"File not found or error loading {os.path.basename(path)}: {e}. Some chatbot features may be limited.")
        return pd.DataFrame()

def get_pavement_condition_prediction(street_name):
    if pavement_latlon_df.empty:
        return "I don't have pavement condition data to answer that question. Please ensure the 'COSA_Pavement.csv' file is loaded correctly."

    target_street_data = pavement_latlon_df[pavement_latlon_df['MSAG_Name'].str.contains(street_name, case=False, na=False)].copy()

    if not target_street_data.empty:
        avg_pci = target_street_data['PCI'].mean()
        if avg_pci < 50:
            prediction = "High likelihood of facing potholes due to generally poor pavement conditions."
        elif avg_pci < 70:
            prediction = "Moderate likelihood of facing potholes due to fair pavement conditions."
        else:
            prediction = "Low likelihood of facing potholes due to generally good pavement conditions."
        return f"For {street_name}, the average Pavement Condition Index (PCI) is {avg_pci:.2f}. Prediction: {prediction}"
    else:
        return f"No pavement data found for the street: {street_name}. Please check the street name or expand the search area."

def get_monthly_pothole_count():
    if pothole_cases_df.empty:
        return "I don't have monthly pothole case data to answer that question. Please ensure the '311_Pothole_Cases_18_24.csv' file is loaded correctly."

    pothole_cases_df['YearMonth'] = pothole_cases_df['OpenDate'].dt.to_period('M')
    monthly_potholes = pothole_cases_df.groupby('YearMonth')['cases'].sum().sort_index()

    if not monthly_potholes.empty:
        latest_month_period = monthly_potholes.index.max()
        potholes_this_month = monthly_potholes.loc[latest_month_period]
        latest_month_str = latest_month_period.strftime('%B %Y')
        return f"In {latest_month_str}, a total of {potholes_this_month} potholes were reported."
    else:
        return "No monthly pothole cases data available to show trends."

def get_worst_pothole_streets():
    if pavement_latlon_df.empty:
        return "I don't have pavement data to identify streets with the worst potholes. Please ensure the 'COSA_Pavement.csv' file is loaded correctly.", None, pd.DataFrame()

    street_pci_avg = pavement_latlon_df.groupby('MSAG_Name')['PCI'].mean()

    if not street_pci_avg.empty:
        street_deterioration_score = 100 - street_pci_avg
        top_worst_streets_data = street_deterioration_score.sort_values(ascending=False).head(10)

        response = "Here are the Top 10 streets with the worst road conditions (most prone to potholes):\n"
        for rank, (street_name, score) in enumerate(top_worst_streets_data.items()):
            response += f"{rank + 1}. {street_name} (Deterioration Score: {score:.2f})\n"

        # Create a bar chart for visualization
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(x=top_worst_streets_data.values, y=top_worst_streets_data.index, ax=ax, palette="viridis", hue=top_worst_streets_data.index, legend=False)
        ax.set_title('Top 10 Streets with Worst Road Conditions')
        ax.set_xlabel('Pavement Deterioration Score (100 - PCI)')
        ax.set_ylabel('Street Name')
        plt.tight_layout()

        # Prepare highlight_data_df for map
        highlight_data_df = pavement_latlon_df[pavement_latlon_df['MSAG_Name'].isin(top_worst_streets_data.index)].copy()
        highlight_data_df = highlight_data_df.drop_duplicates(subset=['MSAG_Name'])
        highlight_data_df = highlight_data_df[['MSAG_Name', 'Latitude', 'Longitude']]
        highlight_data_df['color'] = 'darkblue' # Assign darkblue color for worst streets

        return response, fig, highlight_data_df
    else:
        return "No street-level road condition data available to identify worst streets.", None, pd.DataFrame()

def get_top_complaint_locations():
    if complaint_df.empty:
        return "I don't have complaint data to identify top locations. Please ensure the 'COSA_pavement_311.csv' file is loaded correctly.", None, pd.DataFrame()

    df_cosa_pavement_311_complaints = complaint_df.copy()
    df_cosa_pavement_311_complaints.dropna(subset=['MSAG_Name'], inplace=True)

    if not df_cosa_pavement_311_complaints.empty:
        top_10_complaint_locations = df_cosa_pavement_311_complaints['MSAG_Name'].value_counts().head(10)

        response = "Here are the Top 10 most frequently reported complaint locations (streets, all types of complaints):\n"
        for rank, (street_name, count) in enumerate(top_10_complaint_locations.items()):
            response += f"{rank + 1}. {street_name}: {count} total reports\n"

        # Create a bar chart for visualization
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(x=top_10_complaint_locations.values, y=top_10_complaint_locations.index, ax=ax, palette="viridis", hue=top_10_complaint_locations.index, legend=False)
        ax.set_title('Top 10 Most Frequently Reported Complaint Locations')
        ax.set_xlabel('Number of Complaints')
        ax.set_ylabel('Street Name')
        plt.tight_layout()

        # Prepare highlight_data_df for map: get lat/lon for top 10 complaint streets
        # Merge with pavement_latlon_df to get coordinates
        highlight_data_df = pd.DataFrame({'MSAG_Name': top_10_complaint_locations.index})
        highlight_data_df = pd.merge(highlight_data_df, pavement_latlon_df[['MSAG_Name', 'Latitude', 'Longitude']],
                                     on='MSAG_Name', how='left')
        highlight_data_df = highlight_data_df.drop_duplicates(subset=['MSAG_Name'])
        highlight_data_df = highlight_data_df.dropna(subset=['Latitude', 'Longitude'])
        highlight_data_df['color'] = 'darkblue' # Assign darkblue color for top complaint locations

        return response, fig, highlight_data_df
    else:
        return "No valid street names found in the complaint data after cleaning.", None, pd.DataFrame()

def get_unresolved_complaints_by_year():
    if complaint_df.empty:
        return "I don't have complaint data to determine unresolved complaints. Please ensure the 'COSA_pavement_311.csv' file is loaded correctly.", None, pd.DataFrame()

    df_complaints_yearly = complaint_df.copy()
    df_complaints_yearly['OPENEDDATETIME'] = pd.to_datetime(df_complaints_yearly['OPENEDDATETIME'], errors='coerce')
    df_complaints_yearly.dropna(subset=['OPENEDDATETIME'], inplace=True)

    if not df_complaints_yearly.empty:
        df_complaints_yearly['OpenedYear'] = df_complaints_yearly['OPENEDDATETIME'].dt.year
        df_complaints_yearly['IsUnresolved'] = df_complaints_yearly['CLOSEDDATETIME'].isna()

        yearly_status = df_complaints_yearly.groupby('OpenedYear').agg(
            TotalComplaints=('OPENEDDATETIME', 'count'),
            UnresolvedComplaints=('IsUnresolved', 'sum')
        ).reset_index()
        yearly_status['UnresolvedComplaints'] = yearly_status['UnresolvedComplaints'].astype(int)

        if not yearly_status.empty:
            response = "Complaint Status by Year:\n"
            for index, row in yearly_status.iterrows():
                if row['TotalComplaints'] > 0:
                    percent_unresolved = (row['UnresolvedComplaints'] / row['TotalComplaints']) * 100
                    response += f"Year {int(row['OpenedYear'])}: Total = {int(row['TotalComplaints'])}, Unresolved = {int(row['UnresolvedComplaints'])} ({percent_unresolved:.2f}%)\n"
                else:
                    response += f"Year {int(row['OpenedYear'])}: No complaints reported.\n"
            return response, None, pd.DataFrame()
        else:
            return "No complaints found to summarize by year.", None, pd.DataFrame()
    else:
        return "No valid complaint data with opened dates found after initial cleaning.", None, pd.DataFrame()

def get_seasonal_pothole_impact():
    if complaint_df.empty:
        return "I don't have complaint data to analyze seasonal impact on potholes. Please ensure the 'COSA_pavement_311.csv' file is loaded correctly.", None, pd.DataFrame()

    pothole_complaints_seasonal = complaint_df.copy()
    pothole_complaints_seasonal['Month'] = pothole_complaints_seasonal['OPENEDDATETIME'].dt.month
    pothole_complaints_seasonal = pothole_complaints_seasonal.dropna(subset=['Month'])

    if not pothole_complaints_seasonal.empty:
        monthly_complaints_potholes = pothole_complaints_seasonal.groupby('Month').size().reset_index(name='Total_Complaints')
        month_names = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                       7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
        monthly_complaints_potholes['Month_Name'] = monthly_complaints_potholes['Month'].map(month_names)

        response = "Seasonal Trend of Road-Related Complaints:\n"
        for index, row in monthly_complaints_potholes.iterrows():
            response += f"{row['Month_Name']}: {row['Total_Complaints']} complaints\n"
        response += "\nTypically, increased precipitation and freeze-thaw cycles (large temperature differences) in winter/early spring contribute to more potholes."
        
        # Create a line plot for seasonal trends
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.lineplot(x='Month_Name', y='Total_Complaints', data=monthly_complaints_potholes, marker='o', ax=ax)
        ax.set_title('Seasonal Trend of Road-Related Complaints')
        ax.set_xlabel('Month')
        ax.set_ylabel('Total Complaints')
        plt.tight_layout()

        return response, fig, pd.DataFrame() # No specific highlight data for this plot
    else:
        return "No road-related complaints found for seasonal analysis.", None, pd.DataFrame()

def get_pothole_formation_prediction():
    if pavement_latlon_df.empty or complaint_df.empty:
        return "I need both pavement and complaint data to predict pothole formation. Please ensure 'COSA_Pavement.csv' and 'COSA_pavement_311.csv' are loaded correctly.", None, pd.DataFrame()

    # 1. Calculate Average PCI and Road Deterioration Score per MSAG_Name
    pci_by_msag = pavement_latlon_df.groupby('MSAG_Name')['PCI'].mean().reset_index()
    pci_by_msag['Road_Deterioration_Score'] = 100 - pci_by_msag['PCI']

    # 2. Calculate Recent Complaint Count per MSAG_Name
    current_year = datetime.now().year
    recent_complaints_period = complaint_df[
        (complaint_df['OPENEDDATETIME'].dt.year >= current_year - 2) &
        (complaint_df['OPENEDDATETIME'].dt.year < current_year) # Exclude current incomplete year
    ].copy()
    recent_complaint_counts = recent_complaints_period['MSAG_Name'].value_counts().reset_index()
    recent_complaint_counts.columns = ['MSAG_Name', 'Recent_Complaint_Count']

    # 3. Calculate Maintenance Age per MSAG_Name
    latest_install_date = complaint_df.groupby('MSAG_Name')['InstallDate'].max().reset_index()
    latest_data_date = complaint_df['OPENEDDATETIME'].max()
    if pd.isna(latest_data_date):
        latest_data_date = datetime.now()
    latest_install_date['Maintenance_Age_Years'] = (latest_data_date - latest_install_date['InstallDate']).dt.days / 365.25
    latest_install_date['Maintenance_Age_Years'] = latest_install_date['Maintenance_Age_Years'].fillna(latest_install_date['Maintenance_Age_Years'].max() * 2)

    # 4. Merge all relevant dataframes
    pothole_risk_df = pd.merge(pci_by_msag, recent_complaint_counts, on='MSAG_Name', how='outer')
    pothole_risk_df = pd.merge(pothole_risk_df, latest_install_date[['MSAG_Name', 'Maintenance_Age_Years']], on='MSAG_Name', how='outer')

    # Fill NaN values
    pothole_risk_df['Road_Deterioration_Score'] = pothole_risk_df['Road_Deterioration_Score'].fillna(pothole_risk_df['Road_Deterioration_Score'].mean())
    pothole_risk_df['Recent_Complaint_Count'] = pothole_risk_df['Recent_Complaint_Count'].fillna(0)
    pothole_risk_df['Maintenance_Age_Years'] = pothole_risk_df['Maintenance_Age_Years'].fillna(pothole_risk_df['Maintenance_Age_Years'].max())

    # 5. Create a composite Pothole Formation Risk Score (normalize and sum)
    for col in ['Road_Deterioration_Score', 'Recent_Complaint_Count', 'Maintenance_Age_Years']:
        min_val = pothole_risk_df[col].min()
        max_val = pothole_risk_df[col].max()
        if (max_val - min_val) != 0:
            pothole_risk_df[f'{col}_Scaled'] = (pothole_risk_df[col] - min_val) / (max_val - min_val)
        else:
            pothole_risk_df[f'{col}_Scaled'] = 0.5 # Assign a neutral value if all are the same

    pothole_risk_df['Pothole_Formation_Risk_Score'] = \
        pothole_risk_df['Road_Deterioration_Score_Scaled'] * 0.5 + \
        pothole_risk_df['Recent_Complaint_Count_Scaled'] * 0.3 + \
        pothole_risk_df['Maintenance_Age_Years_Scaled'] * 0.2 

    pothole_risk_df.sort_values(by='Pothole_Formation_Risk_Score', ascending=False, inplace=True)

    top_risk_areas = pothole_risk_df.head(10)
    
    response = "Predicted Top 10 Areas for New Pothole Formation in the next 2 years (Higher Score = Higher Risk):\n"
    for index, row in top_risk_areas.iterrows():
        response += f"{index + 1}. {row['MSAG_Name']}: Risk Score = {row['Pothole_Formation_Risk_Score']:.2f} (Deterioration: {row['Road_Deterioration_Score']:.2f}, Recent Complaints: {int(row['Recent_Complaint_Count'])}, Maint. Age: {row['Maintenance_Age_Years']:.1f} yrs)\n"
    
    # Create a bar chart for predicted pothole formation risk
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x='Pothole_Formation_Risk_Score', y='MSAG_Name', data=top_risk_areas, ax=ax, palette="coolwarm", hue='MSAG_Name', legend=False)
    ax.set_title('Top 10 Areas for Pothole Formation Prediction')
    ax.set_xlabel('Pothole Formation Risk Score')
    ax.set_ylabel('Street Name')
    plt.tight_layout()

    # Prepare highlight_data_df for map
    highlight_data_df = pd.merge(top_risk_areas, pavement_latlon_df[['MSAG_Name', 'Latitude', 'Longitude']],
                                 on='MSAG_Name', how='left')
    highlight_data_df = highlight_data_df.drop_duplicates(subset=['MSAG_Name'])
    highlight_data_df = highlight_data_df.dropna(subset=['Latitude', 'Longitude'])

    # Ensure numeric columns are standard Python types for JSON serialization
    for col in ['Latitude', 'Longitude', 'Pothole_Formation_Risk_Score', 'Road_Deterioration_Score', 'Recent_Complaint_Count', 'Maintenance_Age_Years']:
        if col in highlight_data_df.columns:
            if highlight_data_df[col].dtype == 'float64':
                highlight_data_df[col] = highlight_data_df[col].astype(float)
            elif highlight_data_df[col].dtype == 'int64':
                highlight_data_df[col] = highlight_data_df[col].astype(int)

    highlight_data_df['color'] = 'darkblue' # Assign darkblue color for predicted risk
    highlight_data_df['marker_radius'] = 15 # Assign radius 15 for predicted risk

    return response, fig, highlight_data_df

# --- Handler: Area-specific pothole formation prediction ---
def handle_pothole_formation_prediction_area(area):
    if pavement_latlon_df.empty or complaint_df.empty:
        return "I need both pavement and complaint data to predict pothole formation. Please ensure 'COSA_Pavement.csv' and 'COSA_pavement_311.csv' are loaded correctly.", None, pd.DataFrame()
    # 1. Calculate Average PCI and Road Deterioration Score per MSAG_Name
    pci_by_msag = pavement_latlon_df.groupby('MSAG_Name')['PCI'].mean().reset_index()
    pci_by_msag['Road_Deterioration_Score'] = 100 - pci_by_msag['PCI']
    # 2. Calculate Recent Complaint Count per MSAG_Name
    current_year = datetime.now().year
    recent_complaints_period = complaint_df[
        (complaint_df['OPENEDDATETIME'].dt.year >= current_year - 2) &
        (complaint_df['OPENEDDATETIME'].dt.year < current_year)
    ].copy()
    recent_complaint_counts = recent_complaints_period['MSAG_Name'].value_counts().reset_index()
    recent_complaint_counts.columns = ['MSAG_Name', 'Recent_Complaint_Count']
    # 3. Calculate Maintenance Age per MSAG_Name
    latest_install_date = complaint_df.groupby('MSAG_Name')['InstallDate'].max().reset_index()
    latest_data_date = complaint_df['OPENEDDATETIME'].max()
    if pd.isna(latest_data_date):
        latest_data_date = datetime.now()
    latest_install_date['Maintenance_Age_Years'] = (latest_data_date - latest_install_date['InstallDate']).dt.days / 365.25
    latest_install_date['Maintenance_Age_Years'] = latest_install_date['Maintenance_Age_Years'].fillna(latest_install_date['Maintenance_Age_Years'].max() * 2)
    # 4. Merge all relevant dataframes
    pothole_risk_df = pd.merge(pci_by_msag, recent_complaint_counts, on='MSAG_Name', how='outer')
    pothole_risk_df = pd.merge(pothole_risk_df, latest_install_date[['MSAG_Name', 'Maintenance_Age_Years']], on='MSAG_Name', how='outer')
    # Fill NaN values
    pothole_risk_df['Road_Deterioration_Score'] = pothole_risk_df['Road_Deterioration_Score'].fillna(pothole_risk_df['Road_Deterioration_Score'].mean())
    pothole_risk_df['Recent_Complaint_Count'] = pothole_risk_df['Recent_Complaint_Count'].fillna(0)
    pothole_risk_df['Maintenance_Age_Years'] = pothole_risk_df['Maintenance_Age_Years'].fillna(pothole_risk_df['Maintenance_Age_Years'].max())
    # 5. Create a composite Pothole Formation Risk Score (normalize and sum)
    for col in ['Road_Deterioration_Score', 'Recent_Complaint_Count', 'Maintenance_Age_Years']:
        min_val = pothole_risk_df[col].min()
        max_val = pothole_risk_df[col].max()
        if (max_val - min_val) != 0:
            pothole_risk_df[f'{col}_Scaled'] = (pothole_risk_df[col] - min_val) / (max_val - min_val)
        else:
            pothole_risk_df[f'{col}_Scaled'] = 0.5
    pothole_risk_df['Pothole_Formation_Risk_Score'] = (
        pothole_risk_df['Road_Deterioration_Score_Scaled'] * 0.5 +
        pothole_risk_df['Recent_Complaint_Count_Scaled'] * 0.3 +
        pothole_risk_df['Maintenance_Age_Years_Scaled'] * 0.2
    )
    # Find the area (case-insensitive, partial match)
    area_row = pothole_risk_df[pothole_risk_df['MSAG_Name'].str.contains(area, case=False, na=False)]
    if area_row.empty:
        return f"No risk data found for the area '{area}'. Please check the area name.", None, pd.DataFrame()
    row = area_row.iloc[0]
    city_avg = pothole_risk_df['Pothole_Formation_Risk_Score'].mean()
    risk = row['Pothole_Formation_Risk_Score']
    risk_level = "High" if risk > 0.66 else ("Moderate" if risk > 0.33 else "Low")
    compare = "above" if risk > city_avg else ("below" if risk < city_avg else "equal to")
    response = (
        f"The predicted pothole formation risk for {row['MSAG_Name']} is {risk:.2f} ({risk_level}).\n"
        f"- Deterioration: {row['Road_Deterioration_Score']:.2f}\n"
        f"- Recent Complaints: {int(row['Recent_Complaint_Count'])}\n"
        f"- Maintenance Age: {row['Maintenance_Age_Years']:.1f} years\n"
        f"This is {compare} the city average risk."
    )
    # Optionally, highlight this area on the map
    highlight_df = pavement_latlon_df[pavement_latlon_df['MSAG_Name'] == row['MSAG_Name']][['MSAG_Name', 'Latitude', 'Longitude']].copy()
    highlight_df['color'] = 'blue'
    highlight_df['marker_radius'] = 12
    return response, None, highlight_df

# --- Handler: How does weather affect formations? ---
def handle_weather_effect():
    response = (
        "Weather plays a major role in pothole formation. Rain and snow allow water to seep into pavement cracks. "
        "When temperatures drop, the water freezes and expands, causing the pavement to break apart. "
        "Repeated freeze-thaw cycles and heavy rainfall accelerate pothole development."
    )
    return response, None, pd.DataFrame()

# --- Handler: Why are there so many potholes? ---
def handle_why_so_many_potholes():
    response = (
        "Potholes are caused by a combination of traffic wear, water infiltration, and temperature changes. "
        "Water seeps into cracks, freezes and expands, breaking the pavement. Heavy traffic then worsens the damage. "
        "Poor road maintenance and weather extremes can increase pothole formation."
    )
    return response, None, pd.DataFrame()

# --- Handler: How long does it take on average for potholes to get fixed in San Antonio? ---
def handle_avg_fix_time():
    if pothole_cases_df.empty or 'OpenDate' not in pothole_cases_df.columns or 'CloseDate' not in pothole_cases_df.columns:
        return "No fix time data available.", None, pd.DataFrame()
    df = pothole_cases_df.dropna(subset=['OpenDate', 'CloseDate']).copy()
    df['fix_time'] = (pd.to_datetime(df['CloseDate']) - pd.to_datetime(df['OpenDate'])).dt.days
    avg_days = df['fix_time'].mean()
    if np.isnan(avg_days):
        return "Insufficient data to calculate average fix time.", None, pd.DataFrame()
    return f"On average, potholes in San Antonio are fixed in {avg_days:.1f} days.", None, pd.DataFrame()

# --- Handler: Which areas have the highest amount of potholes? ---
def handle_areas_with_most_potholes(top_n=5):
    if pothole_cases_df.empty or 'MSAG_Name' not in pothole_cases_df.columns:
        return "No area data available.", None, pd.DataFrame()
    area_counts = pothole_cases_df['MSAG_Name'].value_counts().head(top_n)
    response = "Areas with the highest number of potholes:\n"
    for i, (area, count) in enumerate(area_counts.items(), 1):
        response += f"{i}. {area}: {count} potholes\n"
    highlight_df = pavement_latlon_df[pavement_latlon_df['MSAG_Name'].isin(area_counts.index)][['MSAG_Name', 'Latitude', 'Longitude']].copy()
    highlight_df['color'] = 'red'
    highlight_df['marker_radius'] = 12
    return response, None, highlight_df

# --- Handler: How many potholes have been found this month? ---
def handle_potholes_this_month():
    if pothole_cases_df.empty or 'OpenDate' not in pothole_cases_df.columns:
        return "No pothole data available.", None, pd.DataFrame()
    now = pd.Timestamp.now()
    this_month = pothole_cases_df[pothole_cases_df['OpenDate'].dt.month == now.month]
    count = len(this_month)
    return f"There have been {count} potholes reported so far this month.", None, pd.DataFrame()

# --- Handler: Should I avoid [area] because of the potholes? ---
def handle_should_avoid_area(area, threshold=10):
    msg, _, highlight_df = handle_potholes_in_area(area)
    match = re.search(r"(\d+)", msg)
    count = int(match.group(1)) if match else 0
    if count > threshold:
        advice = f"There are {count} potholes in '{area}'. It is advisable to avoid this area if possible."
    elif count > 0:
        advice = f"There are {count} potholes in '{area}', but it may still be passable. Exercise caution."
    else:
        advice = f"No significant pothole issues detected in '{area}'. It should be safe to travel."
    return advice, None, highlight_df

# --- Handler: How many potholes are in the [area]? ---
def handle_potholes_in_area(area):
    lat, lon = geocode_address(area)
    if lat is None or lon is None:
        return f"Could not geocode the area '{area}'. Please check the area and try again.", None, pd.DataFrame()
    gdf = get_pavement_gdf()
    if gdf.empty:
        return "No pavement location data available.", None, pd.DataFrame()
    gdf_proj = gdf.to_crs(epsg=3857)
    point = gpd.GeoSeries([gpd.points_from_xy([lon], [lat])[0]], crs="EPSG:4326").to_crs(epsg=3857)
    buffer = point.buffer(1000)
    in_area = gdf_proj[gdf_proj.geometry.within(buffer.iloc[0])]
    count = len(in_area)
    if count == 0:
        return f"No potholes found in '{area}'.", None, pd.DataFrame()
    highlight_df = in_area.to_crs(epsg=4326)[["Latitude", "Longitude", "MSAG_Name"]].copy()
    highlight_df["color"] = "orange"
    highlight_df["marker_radius"] = 10
    return f"There are {count} pothole(s) in '{area}'.", None, highlight_df

# --- Handler: Any pothole complaints near school zones? ---
def handle_any_complaints_near_sensitive_areas(radius_m=300, sensitive_type='school'):
    # Map user type to possible keywords in the name
    type_keywords = {
        'school': ['school'],
        'hospital': ['hospital', 'medical', 'clinic'],
        'senior': ['senior', 'elder', 'center', 'elderberry', 'elderwood', 'elderpath']
    }
    keywords = type_keywords.get(sensitive_type, [sensitive_type])
    if complaint_df.empty or 'Latitude' not in complaint_df.columns or 'Longitude' not in complaint_df.columns:
        return "Complaint data with location is required for this analysis.", None, pd.DataFrame()
    all_complaints = complaint_df[complaint_df['Latitude'].notna() & complaint_df['Longitude'].notna()]
    print(f"DEBUG: Number of total complaints: {len(all_complaints)}")
    pattern = '|'.join(keywords)
    sensitive = sensitive_locations_df[sensitive_locations_df['name'].str.contains(pattern, case=False, na=False)].copy()
    print(f"DEBUG: Number of sensitive locations ({sensitive_type}): {len(sensitive)}")
    if sensitive.empty:
        return f"No sensitive {sensitive_type} location data available.", None, pd.DataFrame()
    sensitive_unique = sensitive.drop_duplicates(subset=['name', 'lat', 'lon'])
    summary = []
    highlight_rows = []
    for _, row in sensitive_unique.iterrows():
        lat, lon, name = row['lat'], row['lon'], row['name']
        if pd.isna(lat) or pd.isna(lon):
            continue
        near = all_complaints[((all_complaints['Latitude'] - float(lat))**2 + (all_complaints['Longitude'] - float(lon))**2).pow(0.5) < (radius_m/111320)]
        count = len(near)
        if count > 0:
            summary.append(f"{count} complaint(s) near {name} ({lat:.5f}, {lon:.5f})")
            marker_radius = min(25, 8 + count // 2)
            if count >= 30:
                marker_color = 'darkred'
            elif count >= 20:
                marker_color = 'red'
            elif count >= 10:
                marker_color = 'orange'
            else:
                marker_color = 'yellow'
            for _, c in near.iterrows():
                highlight_rows.append({
                    'Sensitive': name,
                    'ComplaintID': c.get('ComplaintID', ''),
                    'Latitude': c['Latitude'],
                    'Longitude': c['Longitude'],
                    'color': marker_color,
                    'marker_radius': marker_radius,
                    'ComplaintCount': count
                })
    if not summary:
        return f"No pothole complaints found near any {sensitive_type} zone.", None, pd.DataFrame()
    highlight_df = pd.DataFrame(highlight_rows)
    response = f"Pothole complaints near {sensitive_type} zones: " + "; ".join(summary)
    return response, None, highlight_df

# --- RAG Query Integration ---
from rag_tool import query_table

# Simple parser for street and year from user question
def parse_rag_question(question):
    import re
    print(f"[RAG DEBUG] Parsing question: {question}")
    street = None
    year = None
    # Improved regex: match 'on <street> in <year>' or 'for <street> in <year>'
    m = re.search(r"(?:on|for) ([\w\s]+?) in (\d{4})", question, re.IGNORECASE)
    if m:
        street = m.group(1).strip()
        year = int(m.group(2))
        print(f"[RAG DEBUG] Matched improved pattern | street: '{street}', year: {year}")
    else:
        # Fallback to previous patterns
        patterns = [
            r'(?:on|reported on|for) ([\w\s]+?) in (\d{4})\??',
            r'(?:on|for) ([\w\s]+?) (?:were )?reported in (\d{4})\??',
            r'([\w\s]+?) potholes (?:in|for) (\d{4})\??',
            r'potholes (?:on|for) ([\w\s]+?) (?:in|for) (\d{4})\??',
            r'([\w\s]+?) in (\d{4})\??',
            r'([\w\s]+?) (\d{4})\??',
        ]
        for pat in patterns:
            m = re.search(pat, question, re.IGNORECASE)
            if m:
                street = m.group(1).strip()
                year = int(m.group(2))
                print(f"[RAG DEBUG] Matched fallback pattern: {pat} | street: '{street}', year: {year}")
                break
    if not street or not year:
        print("[RAG DEBUG] No RAG pattern matched.")
    return street, year

# --- Update get_groq_response to use RAG as fallback ---
def get_groq_response(prompt):
    prompt_lower = prompt.lower()
    plot_object = None
    highlight_data_df = pd.DataFrame() # Initialize empty DataFrame for map highlighting

    print(f"[DEBUG] Received prompt: {prompt}")

    # --- Area-specific pothole formation prediction ---
    match = re.search(r"how likely (will|could) potholes form (on|in|along|at) ([^?]+)", prompt_lower)
    if match:
        print("[DEBUG] Matched area-specific pothole formation prediction pattern.")
        area = match.group(3).strip()
        return handle_pothole_formation_prediction_area(area)
    # --- General city-wide prediction ---
    if re.search(r"how likely (will|could) potholes form( in san antonio)?", prompt_lower):
        print("[DEBUG] Matched city-wide pothole formation prediction pattern.")
        return get_pothole_formation_prediction()
    # --- Data-driven: How many potholes were reported on [street] in [year]? ---
    match = re.search(r"how many potholes (were )?reported on ([^?]+) in (\d{4})", prompt_lower)
    if match:
        print("[DEBUG] Matched data-driven street/year pattern.")
        street = match.group(2).strip()
        year = int(match.group(3))
        results = query_table(street=street, year=year)
        if results:
            df = pd.DataFrame(results, columns=["latitude", "longitude", "street_name", "year", "council_district"])
            df = df.rename(columns={
                'latitude': 'Latitude',
                'longitude': 'Longitude',
                'street_name': 'MSAG_Name'
            })
            total = len(df)
            breakdown = df['MSAG_Name'].value_counts().to_dict()
            breakdown_str = "; ".join([f"{k}: {v}" for k, v in breakdown.items()])
            response = f"Found {total} pothole records for streets containing '{street}' in {year}.\nBreakdown: {breakdown_str}"
            print(f"[DEBUG] Data-driven response: {response}")
            return response, None, df
        else:
            print(f"[DEBUG] No records found for street='{street}', year={year}")
            return f"No pothole records found for streets containing '{street}' in {year}.", None, pd.DataFrame()
    # --- Optimized intent detection for all questions ---
    # 0. Most potholes / worst pothole locations / top pothole locations
    if re.search(r"(where (are|is) (the )?(most|worst) potholes|top (\d+ )?(worst|most) pothole|worst pothole locations|top pothole locations|most pothole complaints|most reported potholes|highest pothole count)", prompt_lower):
        # Try to extract a number for top N, default to 10
        top_n_match = re.search(r"top (\d+)", prompt_lower)
        top_n = int(top_n_match.group(1)) if top_n_match else 10
        return handle_areas_with_most_potholes(top_n=top_n)
    # 1. Are there potholes near [address]?
    match = re.search(r"potholes? near ([^?]+)", prompt_lower)
    if match:
        address = match.group(1).strip()
        return handle_potholes_near_address(address)
    # 2. Will I face potholes on the way to [area]?
    match = re.search(r"potholes? (on|along|on the way to|on my way to|on route to|on the way) ([^?]+)", prompt_lower)
    if match:
        area = match.group(2).strip()
        return handle_potholes_on_route(area)
    # 3. How many potholes are in the [area]?
    match = re.search(r"how many potholes (are )?(in|at|within) ([^?]+)", prompt_lower)
    if match:
        area = match.group(3).strip()
        return handle_potholes_in_area(area)
    # 4. Should I avoid [area] because of the potholes?
    match = re.search(r"should i avoid ([^?]+) because of (the )?potholes", prompt_lower)
    if match:
        area = match.group(1).strip()
        return handle_should_avoid_area(area)
    # 5. How many potholes have been found this month?
    if re.search(r"(how many|number of) potholes (have been )?(found|reported)? ?(this|in the current) month", prompt_lower):
        return handle_potholes_this_month()
    # 6. Which areas have the highest amount of potholes?
    if re.search(r"which areas? (have|has) (the )?(highest|most) (amount|number) of potholes", prompt_lower):
        return handle_areas_with_most_potholes()
    # 7. Display streets with the worst potholes
    if re.search(r"(display|show) streets? (with|having) (the )?worst potholes", prompt_lower):
        return get_worst_pothole_streets()
    # 8. How long does it take on average for potholes to get fixed in san antonio\??", prompt_lower):
    if re.search(r"how long does it take (on average )?for potholes to get fixed( in san antonio)?", prompt_lower):
        return handle_avg_fix_time()
    # 9. How likely will potholes form on this route/street/area?
    if re.search(r"how likely (will|could) potholes form (on|in|along|at) (this|the|a)? ?(route|street|area)?", prompt_lower):
        return get_pothole_formation_prediction()
    # 10. Why are there so many potholes?
    if re.search(r"why (are|is) (there )?so many potholes", prompt_lower):
        return handle_why_so_many_potholes()
    # 11. How does weather affect formations?
    if re.search(r"how does weather affect (pothole )?formation(s)?", prompt_lower):
        return handle_weather_effect()

    # --- Safety & Prevention Questions ---
    match = re.search(r'active pothole complaints.*(school|senior|hospital)', prompt_lower)
    if match:
        sensitive_type = match.group(1)
        # Normalize to match our type_keywords
        if 'school' in sensitive_type:
            sensitive_type = 'school'
        elif 'hospital' in sensitive_type or 'medical' in sensitive_type or 'clinic' in sensitive_type:
            sensitive_type = 'hospital'
        elif 'senior' in sensitive_type or 'elder' in sensitive_type or 'center' in sensitive_type:
            sensitive_type = 'senior'
        return handle_active_complaints_near_sensitive_areas(sensitive_type=sensitive_type)
    if re.search(r'intersections? with via stops.*pothole.*injur', prompt_lower):
        return handle_intersections_via_pothole_injury()
    if re.search(r'preventative maintenance.*bus|damage|delay', prompt_lower):
        return handle_prioritize_maintenance_for_buses()
    match = re.search(r'history of repeated pothole complaints.*along (.+)', prompt_lower)
    if match:
        road = match.group(1).strip(' ?')
        return handle_repeated_complaints_on_road(road)
    # Also match: 'Is there a history of repeated pothole complaints along the [road]?' (with [road] in brackets or as a phrase)
    match = re.search(r'is there a history of repeated pothole complaints along (?:the )?\[?([\w\s\-\.]+)\]?', prompt_lower)
    if match:
        road = match.group(1).strip()
        return handle_repeated_complaints_on_road(road)
    if re.search(r'bus stops.*high[- ]?risk pavement', prompt_lower):
        return handle_bus_stops_near_high_risk_pavement()
    match = re.search(r'any pothole complaints.*(school|senior|hospital)', prompt_lower)
    if match:
        sensitive_type = match.group(1)
        if 'school' in sensitive_type:
            sensitive_type = 'school'
        elif 'hospital' in sensitive_type or 'medical' in sensitive_type or 'clinic' in sensitive_type:
            sensitive_type = 'hospital'
        elif 'senior' in sensitive_type or 'elder' in sensitive_type or 'center' in sensitive_type:
            sensitive_type = 'senior'
        return handle_any_complaints_near_sensitive_areas(sensitive_type=sensitive_type)

    # --- New: VIA route analytics ---
    if re.search(r'(via|transit|bus) route( analytics| risk| affected| pothole)', prompt_lower):
        return handle_via_route_analytics()
    # --- New: ETA/delay prediction ---
    if re.search(r'(eta|delay|arrival time|transit delay|bus delay)', prompt_lower):
        return handle_eta_delay_prediction()
    # --- New: Budget/cost estimation ---
    if re.search(r'(cost|budget|estimate).*pothole', prompt_lower):
        return handle_budget_cost_estimation()
    # --- New: Dashboard/documentation/cleaning Q&A ---
    if re.search(r'(dashboard|documentation|data cleaning|cleaning process)', prompt_lower):
        topic = None
        if 'dashboard' in prompt_lower:
            topic = 'dashboard'
        elif 'documentation' in prompt_lower:
            topic = 'documentation'
        elif 'cleaning' in prompt_lower:
            topic = 'cleaning'
        return handle_dashboard_documentation(topic)
    # --- New: Research/idea generation ---
    if re.search(r'(research ideas|research questions|project ideas|analysis ideas)', prompt_lower):
        return handle_research_ideas()
    # --- New: Security/compliance Q&A ---
    if re.search(r'(security|compliance|pii|privacy|data protection)', prompt_lower):
        return handle_security_compliance()

    # --- RAG fallback: try to parse and answer with query_table ---
    street, year = parse_rag_question(prompt)
    if street and year:
        print(f"[RAG DEBUG] Parsed street: '{street}', year: {year}")
        results = query_table(street=street, year=year)
        print(f"[RAG DEBUG] Results count: {len(results)}")
        if results:
            df = pd.DataFrame(results, columns=["latitude", "longitude", "street_name", "year", "council_district"])
            df = df.rename(columns={
                'latitude': 'Latitude',
                'longitude': 'Longitude',
                'street_name': 'MSAG_Name'
            })
            total = len(df)
            breakdown = df['MSAG_Name'].value_counts().to_dict()
            breakdown_str = "; ".join([f"{k}: {v}" for k, v in breakdown.items()])
            response = f"Found {total} pothole records for streets containing '{street}' in {year}.\nBreakdown: {breakdown_str}"
            print(f"[RAG DEBUG] Response: {response}")
            return response, None, df
        else:
            print(f"[RAG DEBUG] No records found for street='{street}', year={year}")
            return f"No pothole records found for streets containing '{street}' in {year}.", None, pd.DataFrame()
    else:
        print("[RAG DEBUG] Falling back to generic/LLM answer.")

    # --- Existing logic for other questions ---
    # Check for new, more specific analytical questions
    if "pavement condition for" in prompt_lower or "potholes on" in prompt_lower:
        match = re.search(r'(pavement condition for|potholes on)\s+(.+)', prompt_lower)
        if match:
            street_name = match.group(2).strip()
            response_text = get_pavement_condition_prediction(street_name)
            return response_text, plot_object, highlight_data_df
    if "how many potholes this month" in prompt_lower or "monthly pothole count" in prompt_lower:
        response_text = get_monthly_pothole_count()
        return response_text, plot_object, highlight_data_df
    if "worst potholes" in prompt_lower or "streets with bad roads" in prompt_lower:
        response_text, plot_object, highlight_data_df = get_worst_pothole_streets()
        return response_text, plot_object, highlight_data_df
    if "top complaint locations" in prompt_lower or "most reported streets" in prompt_lower:
        response_text, plot_object, highlight_data_df = get_top_complaint_locations()
        return response_text, plot_object, highlight_data_df
    if "unresolved complaints" in prompt_lower or "open complaints by year" in prompt_lower:
        response_text, plot_object, highlight_data_df = get_unresolved_complaints_by_year()
        return response_text, plot_object, highlight_data_df
    if "seasonal impact on potholes" in prompt_lower or "potholes by season" in prompt_lower:
        response_text, plot_object, highlight_data_df = get_seasonal_pothole_impact()
        return response_text, plot_object, highlight_data_df
    if "predict new potholes" in prompt_lower or "pothole formation prediction" in prompt_lower or "where will new potholes form" in prompt_lower:
        response_text, plot_object, highlight_data_df = get_pothole_formation_prediction()
        return response_text, plot_object, highlight_data_df

    # Keyword-based logic
    keyword_responses = {
        "how many potholes": f"There are {len(pothole_cases_df.index) if not pothole_cases_df.empty else 'no'} potholes recorded in the dataset.",
        "number of potholes": f"The dataset contains {len(pothole_cases_df.index) if not pothole_cases_df.empty else 'no'} potholes.",
        "pavement condition": "Pavement condition ratings were joined with pothole data to analyze correlation.",
        "correlation": "The correlation matrix visualizes relationships among Vibration, Speed, and Acceleration.",
        "heatmap": "The heatmap shows which features are strongly related, such as Vibration vs Speed.",
        "scatter plot": "The scatter plot illustrates the distribution of potholes based on latitude and longitude.",
        "vibration data": "Vibration data, collected by sensors, helps in assessing road roughness and potential pothole formation.",
        "acceleration relate": "Acceleration data can indicate sudden jolts or bumps, which are signs of poor road conditions or potholes.",
        "speed data": "Speed data helps understand how vehicle speed interacts with road conditions, affecting the impact of potholes.",
        "latitude and longitude": "Latitude and longitude provide the precise geographical location of potholes and road segments for mapping.",
        "map or folium": "The Folium map displays potholes and road conditions, allowing for interactive geographical analysis.",
        "time series": "The time series chart visualizes the trend of pothole incidents over time, identifying patterns.",
        "monthly trends": "Monthly trends show fluctuations in pothole reports throughout the year, highlighting peak seasons.",
        "yearly trends": "Yearly trends provide an overview of pothole incidents across different years, indicating long-term changes.",
        "datasets merged": "Various datasets, including 311 service requests, pavement conditions, and sensor data, were merged for comprehensive analysis.",
        "dataset or data columns": "The datasets include columns such as Service Request Type, Latitude, Longitude, Open Date, Close Date, MSAG Name, PCI, etc.",
        "missing values": "Missing values in datasets were handled through imputation or removal, depending on the extent and impact of the missing data."
    }

    # Fallback to Groq API for general questions
    response_text = None
    for keyword, resp in keyword_responses.items():
        if keyword in prompt_lower:
            response_text = resp
            break

    if response_text is None:
        try:
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            }
            data = {
                "model": "llama3-8b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4096,
            }
            groq_response = requests.post(GROQ_API_URL, headers=headers, json=data)
            groq_response.raise_for_status() # Raise an exception for HTTP errors
            response_data = groq_response.json()
            response_text = response_data["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            print(f"Error communicating with Groq API: {e}")
            response_text = "I am currently unable to connect to the Groq AI. Please try again later."
        except KeyError:
            response_text = "I received an unexpected response from the Groq AI. Please try rephrasing your question."

    # Convert numeric types in highlight_data_df to native Python types for JSON serialization
    if not highlight_data_df.empty:
        highlight_data_df = _convert_dataframe_numerics_to_native_types(highlight_data_df)
    
    return response_text, plot_object, highlight_data_df

# Function to plot markers on the map
def plot_from_df(df, folium_map):
    """
    Function to plot markers on the map
    Args:
        df (DataFrame): Data containing coordinates
        folium_map (Map): Folium map object
    Returns:
        Map: Updated map with markers
    """
    for i, row in df.iterrows():
        folium.Marker(
            location=[row.Latitude, row.Longitude],
            tooltip=f"Location {i}",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(folium_map)
    return folium_map

def add_pothole_markers(df, folium_map, feature_group, color_column='color', marker_radius=8):
    for _, row in df.iterrows():
        if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
            marker_color = row[color_column] if color_column in row else 'blue' # Default to blue if no color column
            # Use the best available name for tooltip
            if 'MSAG_Name' in row:
                tooltip_name = row['MSAG_Name']
            elif 'Sensitive' in row:
                tooltip_name = row['Sensitive']
            elif 'name' in row:
                tooltip_name = row['name']
            else:
                tooltip_name = 'Location'
            folium.CircleMarker(
                location=[row.Latitude, row.Longitude],
                radius=int(marker_radius),  # Ensure radius is a standard Python int
                color=marker_color,
                fill=True,
                fill_color=marker_color,
                fill_opacity=0.7,
                tooltip=f"{tooltip_name}: {row.get('ComplaintCount', 'N/A')} Complaints",
            ).add_to(feature_group)
    return feature_group # Return the feature group

# --- Load additional datasets for chatbot analysis ---
# Define paths relative to the integrated.py file
# PATCH: use '../Data' instead of 'Data'
data_folder_path = '../Data'

pothole_cases_path = os.path.join(data_folder_path, '311_Pothole_Cases_18_24.csv')
pavement_path = os.path.join(data_folder_path, 'COSA_Pavement.csv')
complaint_full_path = os.path.join(data_folder_path, 'COSA_pavement_311.csv')

try:
    pothole_cases_df = pd.read_csv(pothole_cases_path)
    pavement_latlon_df = pd.read_csv(pavement_path)
    complaint_df = pd.read_csv(complaint_full_path)
except Exception as e:
    print(f"Error loading data files: {e}")
    pothole_cases_df = pd.DataFrame()
    pavement_latlon_df = pd.DataFrame()
    complaint_df = pd.DataFrame()

# After loading DataFrames, ensure correct dtypes and column names
if 'OpenDate' in pothole_cases_df.columns:
    pothole_cases_df['OpenDate'] = pd.to_datetime(pothole_cases_df['OpenDate'], errors='coerce')
if 'OPENEDDATETIME' in complaint_df.columns:
    complaint_df['OPENEDDATETIME'] = pd.to_datetime(complaint_df['OPENEDDATETIME'], errors='coerce')
if 'InstallDate' in complaint_df.columns:
    complaint_df['InstallDate'] = pd.to_datetime(complaint_df['InstallDate'], errors='coerce')
# Ensure Latitude/Longitude columns exist in pavement_latlon_df
if 'Lat' in pavement_latlon_df.columns and 'Lon' in pavement_latlon_df.columns:
    pavement_latlon_df = pavement_latlon_df.rename(columns={'Lat': 'Latitude', 'Lon': 'Longitude'})
# Extract Latitude/Longitude from GoogleMapView if needed
if 'GoogleMapView' in pavement_latlon_df.columns:
    def extract_lat_lon(url):
        if pd.isna(url) or url == 'Not Available':
            return None, None
        match = re.search(r'place/([0-9.]+)N ([0-9.]+)W', url)
        if match:
            lat = float(match.group(1))
            lon = -float(match.group(2))  # West is negative
            return lat, lon
        return None, None
    pavement_latlon_df[['Latitude', 'Longitude']] = pavement_latlon_df['GoogleMapView'].apply(lambda x: pd.Series(extract_lat_lon(x)))
print("pothole_cases_df columns:", pothole_cases_df.columns)
print("pavement_latlon_df columns:", pavement_latlon_df.columns)
print("complaint_df columns:", complaint_df.columns)

# --- Handler: VIA route analytics (most affected routes, route risk, etc.) ---
def handle_via_route_analytics():
    return (
        "VIA route analytics are under development. In the future, this will show which VIA routes are most affected by potholes, risk scores, and more. Please specify a route or ask about route risk.",
        None,
        pd.DataFrame(),
    )

# --- Handler: ETA/delay prediction (stub) ---
def handle_eta_delay_prediction(route=None):
    return (
        f"ETA and delay prediction for VIA routes is not yet implemented. In the future, this will estimate delays based on pothole and road condition data. Please specify a route for more details.",
        None,
        pd.DataFrame(),
    )

# --- Handler: Budget/cost estimation (stub) ---
def handle_budget_cost_estimation(years=5):
    return (
        f"Estimated cost to repair potholes over {years} years is under development. This will use historical repair costs and predicted pothole formation rates.",
        None,
        pd.DataFrame(),
    )

# --- Handler: Dashboard/documentation/cleaning Q&A (static info) ---
def handle_dashboard_documentation(topic=None):
    doc_map = {
        "dashboard": "The dashboard visualizes pothole locations, risk scores, and VIA route intersections using Streamlit or Power BI.",
        "documentation": "Project documentation covers data sources, cleaning steps, modeling, and deployment. See the project README for details.",
        "cleaning": "Data cleaning involved standardizing date formats, coordinates, and removing duplicates. See the cleaning notebook for more.",
    }
    if topic and topic.lower() in doc_map:
        return (doc_map[topic.lower()], None, pd.DataFrame())
    return ("Supported topics: dashboard, documentation, cleaning. Please specify one.", None, pd.DataFrame())

# --- Handler: Research/idea generation (static list) ---
def handle_research_ideas():
    ideas = [
        "1. Predict pothole formation hotspots using weather and traffic data.",
        "2. Analyze repair time disparities across districts.",
        "3. Estimate VIA route delays due to potholes.",
        "4. Correlate pavement condition with complaint frequency.",
        "5. Model budget needs for proactive repairs."
    ]
    return ("Here are 5 research ideas:\n" + "\n".join(ideas), None, pd.DataFrame())

# --- Handler: Security/compliance Q&A (static info) ---
def handle_security_compliance():
    return (
        "Security features include encrypted storage, SSH key authentication, and custom firewalls. PII is minimized and not stored in analytics outputs. See the security policy documentation for more.",
        None,
        pd.DataFrame(),
    )

    print("pothole_cases_df empty:", pothole_cases_df.empty)
    print("pavement_latlon_df empty:", pavement_latlon_df.empty)
    print("complaint_df empty:", complaint_df.empty)
