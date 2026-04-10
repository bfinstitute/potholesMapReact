# Data Expansion Plan for ZIP 78207 Analysis

## Executive Summary
This document outlines:
1. **Unused datasets** already in the codebase that can answer many test questions
2. **Public APIs/data sources** we can integrate for missing data
3. **Database use cases** beyond caching for better system performance

---

## Part 1: Unused Datasets (Already Have, Need to Integrate)

### ✅ Health & Beauty Market Potential (`Health_and_Beauty_Market_Potential_78207_San_Antonio_Behavior.csv`)

**Location:** `/backend/Data/ZIPCODE 78207/clean/Health_and_Beauty_Market_Potential_78207/`

**What It Contains:**
- Exercise patterns (1-3 hrs/wk: 26.1%, 4-6 hrs/wk: 20.4%, 7+ hrs/wk: 18.6%)
- Gym memberships (Planet Fitness: 5.6%, LA Fitness: 1.7%, YMCA: 1.5%)
- Home exercise locations (41.6% exercise at home 2+ times/week)
- Health monitoring equipment ownership:
  - Blood Pressure Monitors: 22.5%
  - Blood Glucose Monitors: 14.3%
  - Pulse Oximeters: 12.4%
  - Heart Rate Monitors: 6.2%
- Diet control patterns:
  - Blood Sugar: 20.4%
  - Cholesterol: 19.3%
  - Weight Loss: 19.4%
  - Weight Maintenance: 9.4%
  - Salt Restriction: 5.6%
- Food purchasing habits (labeled foods):
  - Sugar-Free: 17.3%
  - Low-Sodium: 15.9%
  - Natural/Organic: 16.0%
  - Low-Fat: 13.1%
  - Fat-Free: 11.7%

**Answers These Test Questions:**
- ✅ "What percentage of residents engage in regular physical activity?"
- ✅ "Are residents actively monitoring their health?"
- ✅ "What are the dominant dietary patterns?"
- ✅ "Are residents making health-conscious food choices?"
- ✅ "How prevalent are special diets (diabetic, low-sodium)?"
- ✅ "What behaviors observed suggest elevated stress or burnout?"
- ✅ "Do behavioral trends align with reported medical data?"

**Integration Needed:** Add to `saaf_data.py` as `get_health_behavior_summary()`

---

### ✅ Medical Expenditures (`Medical_Expenditures_78207_San_Antonio.csv`)

**Location:** `/backend/Data/ZIPCODE 78207/clean/Medical_Expenditures_78207/`

**What It Contains:**
- Health insurance coverage spending: $35.16M total
  - Medicare payments: $8.88M
  - Blue Cross/Blue Shield: $9.75M
  - Fee for Service: $6.88M
  - HMO: $4.34M
- Medical care spending: $17.55M total
  - Prescription Drugs: $2.68M
  - Dental Services: $3.07M
  - Hospital Services: $2.04M
  - Physician Services: $2.01M
  - Nonprescription Drugs: $1.40M
- Preventive care:
  - Eyeglasses/Contacts: $758K
  - Vitamins/Supplements: $958K
  - Lab Tests/X-rays: $582K

**Answers These Test Questions:**
- ✅ "How does healthcare utilization compare to national benchmarks?"
- ✅ "What percentage of residents visit healthcare providers annually?"
- ✅ "Are preventive care and regular checkups being utilized?"
- ✅ "What barriers (cost) affect healthcare access?"
- ✅ "Is medication usage higher than expected?"

**Integration Needed:** Add to `saaf_data.py` as `get_medical_spending_summary()`

---

## Part 2: Public APIs & Data Sources to Integrate

### 🔗 1. **CDC PLACES API** (Already Referenced, Need Full Integration)
**URL:** https://data.cdc.gov/resource/swc5-untb.json
**Endpoint:** `https://data.cdc.gov/resource/swc5-untb.json?zipcode=78207`

**What It Provides:**
- 36 chronic disease and health outcome measures
- ZIP code level granularity
- Mental health indicators (depression, mental distress)
- Behavioral risk factors (smoking, drinking, exercise)
- Preventive measures (mammography, colonoscopy, flu shots)
- Health status (general health, disability)

**Sample Query:**
```python
import requests
url = "https://data.cdc.gov/resource/swc5-untb.json"
params = {"zipcode": "78207", "$limit": 100}
response = requests.get(url, params=params)
data = response.json()
```

**Integration:** Create `api_loaders/cdc_places.py` with auto-refresh every 30 days

---

### 🔗 2. **U.S. Census Bureau API**
**URL:** https://api.census.gov/data.html
**Key:** https://api.census.gov/data/key_signup.html (Free)

**What It Provides:**
- American Community Survey (ACS) 5-Year Estimates
- ZIP Code Tabulation Area (ZCTA) data
- Demographics, income, education, employment
- Housing characteristics
- Commuting patterns

**Sample Query:**
```python
# ACS 5-Year Data for ZIP 78207
url = "https://api.census.gov/data/2022/acs/acs5"
params = {
    "get": "NAME,B01003_001E,B19013_001E,B23025_005E",  # Pop, Income, Unemployed
    "for": "zip code tabulation area:78207",
    "key": "YOUR_API_KEY"
}
```

**Integration:** Create `api_loaders/census_api.py`

---

### 🔗 3. **San Antonio Open Data Portal API**
**URL:** https://data.sanantonio.gov/
**Key Features:** Free, no API key needed

**Available Datasets:**
- **311 Service Requests:** https://data.sanantonio.gov/dataset/service-calls
- **Building Permits:** https://data.sanantonio.gov/dataset/building-permits
- **Code Violations:** https://data.sanantonio.gov/dataset/code-violations
- **Fire Incidents:** https://data.sanantonio.gov/dataset/fire-incidents
- **Police Calls:** https://data.sanantonio.gov/dataset/police-calls
- **Health Inspections:** https://data.sanantonio.gov/dataset/restaurant-inspections

**Sample Query:**
```python
# Get recent 311 requests for ZIP 78207
url = "https://data.sanantonio.gov/api/3/action/datastore_search"
params = {
    "resource_id": "service-calls-resource-id",
    "filters": '{"ZIPCODE":"78207"}',
    "limit": 1000
}
```

**Integration:** Create `api_loaders/sa_open_data.py`

---

### 🔗 4. **CMS Medicare Provider Data**
**URL:** https://data.cms.gov/provider-data/
**API:** https://data.cms.gov/provider-data/api-docs

**What It Provides:**
- Medicare provider locations (hospitals, clinics, nursing homes)
- Quality ratings
- Service offerings
- Patient satisfaction scores

**Sample Query:**
```python
# Find healthcare providers near ZIP 78207
url = "https://data.cms.gov/data-api/v1/dataset/xubh-q36u/data"
params = {
    "filter[zip_code]": "78207",
    "size": 100
}
```

**Integration:** Create `api_loaders/cms_providers.py`

---

### 🔗 5. **BLS (Bureau of Labor Statistics) API**
**URL:** https://www.bls.gov/developers/
**Key:** https://data.bls.gov/registrationEngine/ (Free, 500 queries/day)

**What It Provides:**
- Employment statistics by area
- Unemployment rates (already have static data, this provides live updates)
- Wage data by occupation
- Consumer Price Index

**Sample Query:**
```python
# Get San Antonio unemployment rate
import requests
headers = {'Content-type': 'application/json'}
data = {
    "seriesid": ['LAUMT484186000000003'],  # San Antonio unemployment
    "startyear": "2023",
    "endyear": "2026",
    "registrationkey": "YOUR_API_KEY"
}
response = requests.post(
    'https://api.bls.gov/publicAPI/v2/timeseries/data/',
    json=data,
    headers=headers
)
```

**Integration:** Create `api_loaders/bls_api.py`

---

### 🔗 6. **USDA Food Access Research Atlas**
**URL:** https://www.ers.usda.gov/data-products/food-access-research-atlas/
**Data:** https://www.ers.usda.gov/data-products/food-access-research-atlas/download-the-data/

**What It Provides:**
- Food desert indicators
- Supermarket access by distance
- Vehicle access statistics
- Low-income/low-access areas

**Integration:** Download CSV, add to `Data/ZIPCODE 78207/clean/food_access.csv`

---

### 🔗 7. **EPA Environmental Justice Screen**
**URL:** https://www.epa.gov/ejscreen
**API:** https://ejscreen.epa.gov/mapper/

**What It Provides:**
- Environmental hazard indicators
- Air quality index
- Proximity to hazardous waste
- Lead paint exposure risk
- Diesel particulate matter

**Integration:** Create `api_loaders/epa_ejscreen.py`

---

### 🔗 8. **Texas Health and Human Services**
**URL:** https://data.texas.gov/browse?tags=health
**No API Key Required**

**What It Provides:**
- Mental health facility locations
- Substance abuse treatment centers
- Community health centers
- SNAP benefit utilization

---

## Part 3: Database Use Cases (Beyond Caching)

### 📊 1. **User Session & Query Analytics**

**Collection:** `user_sessions`
```javascript
{
  session_id: "uuid",
  user_ip_hash: "md5(ip)",
  started_at: ISODate("2026-04-04T12:00:00Z"),
  ended_at: ISODate("2026-04-04T12:15:00Z"),
  queries: [
    {
      question: "What are the top health issues?",
      intent_detected: "community_need",
      data_sources_used: ["health", "demographics"],
      response_time_ms: 234,
      groq_api_called: true,
      timestamp: ISODate("2026-04-04T12:01:00Z")
    }
  ],
  total_queries: 12,
  avg_response_time_ms: 189
}
```

**Benefits:**
- Track most common questions → prioritize data loading
- Identify slow queries → optimize
- Detect patterns in user behavior
- A/B test different response formats

---

### 📊 2. **Data Freshness Tracking**

**Collection:** `data_sources`
```javascript
{
  source_name: "cdc_places",
  source_type: "api",
  last_fetched: ISODate("2026-04-04T06:00:00Z"),
  next_refresh: ISODate("2026-05-04T06:00:00Z"),
  fetch_status: "success",
  record_count: 36,
  api_endpoint: "https://data.cdc.gov/resource/swc5-untb.json",
  error_count: 0,
  last_error: null
}
```

**Benefits:**
- Auto-refresh stale data
- Monitor API health
- Alert on fetch failures
- Track data versioning

---

### 📊 3. **Intent Detection Training Data**

**Collection:** `intent_feedback`
```javascript
{
  question: "What's the unemployment rate?",
  detected_intent: "context_demographics",
  correct_intent: "unemployment_query",  // Admin correction
  user_satisfied: false,
  data_sources_shown: ["demographics"],
  should_have_shown: ["unemployment"],
  corrected_at: ISODate("2026-04-04T12:00:00Z"),
  corrected_by: "admin"
}
```

**Benefits:**
- Improve intent detection accuracy
- Build training dataset for ML model
- Track misclassifications
- Validate SAAF intent patterns

---

### 📊 4. **Groq Response Quality Monitoring**

**Collection:** `groq_responses`
```javascript
{
  question_hash: "md5(question)",
  question: "What are the main health challenges?",
  context_provided: {
    demographics: "Population: 37,672; Median income: $35,421; Poverty rate: 28.3%",
    health: "High blood pressure: 42.3%; Obesity: 38.1%; Diabetes: 15.7%",
    unemployment: "Latest rate: 6.2%",
    "311": "Top requests: Illegal dumping (1,234 cases)"
  },
  groq_response: "Top Health Challenges in ZIP 78207:\n• High blood pressure: 42.3% of residents\n...",
  temperature: 0.3,
  seed: 42,
  model: "llama-3.1-8b-instant",
  response_time_ms: 456,
  tokens_used: 234,
  grounded_correctly: true,  // Did it cite specific numbers?
  hallucinated: false,  // Did it make up data?
  created_at: ISODate("2026-04-04T12:00:00Z")
}
```

**Benefits:**
- Track response consistency (same question → same answer?)
- Detect hallucinations (citing numbers not in context)
- Monitor token usage costs
- A/B test temperature/seed settings

---

### 📊 5. **Data Gap Tracking**

**Collection:** `data_gaps`
```javascript
{
  question_category: "medication_usage",
  questions_asked: 47,
  data_available: false,
  potential_sources: [
    {
      name: "Texas Prescription Monitoring Program",
      url: "https://www.pharmacy.texas.gov/pmp/",
      access: "restricted",
      notes: "Requires HIPAA compliance"
    },
    {
      name: "Aggregated pharmacy data",
      url: "contact local pharmacies",
      access: "possible",
      notes: "Need aggregated/anonymized data"
    }
  ],
  priority: "high",
  business_value: "Can answer 15% of user questions"
}
```

**Benefits:**
- Prioritize data acquisition
- Track ROI of new datasets
- Justify budget for data purchases
- Guide API integration roadmap

---

### 📊 6. **Geospatial Queries Cache**

**Collection:** `geospatial_cache`
```javascript
{
  query_type: "potholes_west_side",
  zip_codes: ["78207", "78228", "78237", "78201", "78210", "78227", "78211", "78204", "78205", "78226"],
  result_count: 1247,
  result_hash: "md5(results)",
  results_s3_url: "s3://cache/potholes_west_20260404.parquet",
  created_at: ISODate("2026-04-04T12:00:00Z"),
  expires_at: ISODate("2026-04-05T12:00:00Z"),
  hit_count: 12
}
```

**Benefits:**
- Speed up expensive spatial queries
- Reduce GeoPackage I/O
- Track popular map queries
- Pre-warm cache for common areas

---

### 📊 7. **API Rate Limit Management**

**Collection:** `api_rate_limits`
```javascript
{
  api_name: "groq",
  rate_limit_per_minute: 30,
  rate_limit_per_day: 14400,
  current_minute_count: 12,
  current_day_count: 1247,
  reset_minute: ISODate("2026-04-04T12:01:00Z"),
  reset_day: ISODate("2026-04-05T00:00:00Z"),
  blocked_requests: 3,
  queue_size: 0
}
```

**Benefits:**
- Prevent 429 rate limit errors
- Queue requests when nearing limit
- Track API usage costs
- Auto-throttle during peak times

---

### 📊 8. **Change Data Capture (CDC)**

**Collection:** `data_change_log`
```javascript
{
  dataset: "health_places",
  change_type: "update",
  old_value: {"High blood pressure": "41.2%"},
  new_value: {"High blood pressure": "42.3%"},
  changed_fields: ["value"],
  source: "cdc_places_api",
  changed_at: ISODate("2026-04-04T06:00:00Z"),
  impact: "affects 23 cached responses"
}
```

**Benefits:**
- Track data evolution over time
- Invalidate affected cache entries
- Alert stakeholders to significant changes
- Audit data quality

---

## Part 4: Implementation Priority

### 🔥 **Phase 1: Quick Wins (This Week)**
1. ✅ Integrate unused CSV files (Health Behavior, Medical Expenditures)
2. ✅ Add to `saaf_data.py` with new loader functions
3. ✅ Update Groq context to include this data
4. ✅ Test with your sample questions

**Expected Impact:** Answer 40% more test questions immediately

---

### 🔥 **Phase 2: Public APIs (Next 2 Weeks)**
1. CDC PLACES API integration
2. Census API integration
3. San Antonio Open Data portal
4. Set up MongoDB for caching and analytics

**Expected Impact:** Answer 70% more test questions, real-time data

---

### 🔥 **Phase 3: Advanced Analytics (Month 2)**
1. User session tracking
2. Query analytics dashboard
3. Data gap analysis
4. Intent detection improvements

**Expected Impact:** Data-driven optimization, better user experience

---

### 🔥 **Phase 4: Production Scale (Month 3)**
1. API rate limit management
2. Geospatial query caching
3. Change data capture
4. Performance monitoring

**Expected Impact:** Production-ready system with 99.9% uptime

---

## Part 5: Estimated Costs

### Free Tier Available:
- ✅ CDC PLACES API: Free, unlimited
- ✅ Census API: Free, 500 requests/day
- ✅ San Antonio Open Data: Free, unlimited
- ✅ BLS API: Free, 500 requests/day (1000 with registration)
- ✅ MongoDB Atlas: Free tier (512MB storage, shared cluster)

### Potential Paid Services:
- **Groq API:** Currently using free tier, may need paid if scaling
- **MongoDB Atlas:** $57/month for 10GB storage (M10 cluster)
- **AWS S3:** $0.023/GB for geospatial cache storage
- **Esri ArcGIS API:** $100/month for premium geocoding (optional)

**Total Monthly Cost (with paid MongoDB):** ~$60-100/month

---

## Part 6: MongoDB vs Alternatives

**When MongoDB Makes Sense:**
- ✅ Flexible schema (queries, sessions, API responses vary)
- ✅ Good at JSON document storage
- ✅ Built-in TTL indexes for auto-expiring cache
- ✅ Geospatial query support
- ✅ Easy aggregation pipelines for analytics

**Alternatives:**
- **PostgreSQL:** Better for structured data, joins, ACID compliance
- **Redis:** Faster for pure caching, but limited analytics
- **SQLite:** Good for embedded use, but limited concurrency
- **DuckDB:** Excellent for analytics, but not for operational data

**Recommendation:** Use **MongoDB** for flexible operational data (sessions, queries, cache) and keep **PostgreSQL/DuckDB** for analytical queries on structured datasets.

---

## Next Steps

1. **Integrate Unused CSVs** (1-2 hours)
2. **Set up MongoDB Atlas Free Tier** (30 minutes)
3. **Add CDC PLACES API Integration** (2-3 hours)
4. **Test with Your Sample Questions** (1 hour)
5. **Measure Improvement** (Track % of questions answered)

Ready to start with Phase 1?
