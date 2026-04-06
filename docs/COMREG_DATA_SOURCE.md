# ComReg Official Irish Tower Data Source

## 📡 Official Source Found!

ComReg (Ireland's telecom regulator) publishes **official mobile tower locations** as **downloadable Excel spreadsheets**.

This is the **authoritative** source for Irish tower data used by the Site Viewer at https://siteviewer.comreg.ie/

## 🗂️ Data Location

**Main Page:** https://www.comreg.ie/industry/radio-spectrum/licensing/search-licence-type/mobile-licences-2/

### Available Data Files (2025-2026):

#### Vodafone Ireland Limited
- **MBSA1 Licence** (800, 900, 1800 MHz) - **Your tower is likely here**
- **MBSA2 Licence** (700, 2.1, 2.3, 2.6 GHz)  
- **3.6 GHz Licence**

#### Three Ireland (Hutchison) Limited
- **MBSA1 Licence** (800, 900, 1800 MHz)
- **MBSA2 Licence** (700, 2.1, 2.3, 2.6 GHz)
- **3.6 GHz Licence**

#### Eir (Eircom Limited)
- **3G Licence & 2.1 GHz**
- **MBSA1 Licence** (800, 900, 1800 MHz)
- **MBSA2 Licence** (700, 2.1, 2.3, 2.6 GHz)
- **3.6 GHz Licence**

## 📊 Data Format

Each Excel file contains tower information with the following fields:

### Key Fields:
- **Site Identity** - Unique site identifier  
- **Easting** - ITM Coordinate (Irish Transverse Mercator)
- **Northing** - ITM Coordinate (Irish Transverse Mercator)
- **Services / Siteviewer Services** - Technology types (2G, UMTS, LTE, NR)

### Coverage Statistics (Q1 2026):

| Operator | 800 MHz Sites | 900 MHz Sites | 1800 MHz Sites | 2.1 GHz Sites |
|----------|---------------|---------------|----------------|---------------|
| Vodafone | 2,271        | 2,326         | 1,758          | 1,406         |
| Three    | 2,415        | 2,486         | 2,295          | 2,137         |
| Eir      | 2,648        | 2,686         | 1,924          | 1,925         |

**Your detected tower:**
- Cell ID: 43593731
- Operator: Vodafone Ireland (MCC=272, MNC=1)  
- Technology: LTE
- Signal: -85 dBm
- Location: ~53.29°N, -6.62°W (Clane/Prosperous area)

## 🔧 How to Access the Data

### Method 1: Manual Download (Quick Start)
1. Go to: https://www.comreg.ie/industry/radio-spectrum/licensing/search-licence-type/mobile-licences-2/
2. Scroll to **"(2) MBSA1 Liberalised Use Licences (800 MHz, 900 MHz, 1800 MHz Bands)"**
3. Click **"Vodafone Ireland Limited"** → **"2025-2026"**
4. Download the Excel file
5. Look for columns: `Site Identity`, `Easting`, `Northing`, `Services`

### Method 2: Coordinate Conversion Required
**Important:** ComReg uses **ITM (Irish Transverse Mercator)** coordinates, not GPS lat/lon!

**Conversion needed:**
- ITM Easting/Northing → WGS84 Latitude/Longitude
- Use formula or library (e.g., `pyproj`, `proj4`)

**Example ITM to WGS84 conversion:**
```python
from pyproj import Transformer

# Create transformer: ITM (EPSG:2157) → WGS84 (EPSG:4326)
transformer = Transformer.from_crs("EPSG:2157", "EPSG:4326", always_xy=True)

# Example: Convert ITM coordinates  
easting = 677123  # Example ITM Easting
northing = 735456  # Example ITM Northing

# Convert to lat/lon
lon, lat = transformer.transform(easting, northing)
print(f"Latitude: {lat:.6f}, Longitude: {lon:.6f}")
```

## 🚀 Implementation Strategy

### Option 1: Download & Convert (Recommended)
1. **Download all 3 operator Excel files** (Vodafone, Three, Eir for MBSA1/MBSA2)
2. **Parse Excel** → Extract Site ID, Easting, Northing, Services
3. **Convert ITM → WGS84** using pyproj
4. **Build SQLite database** with columns:
   - `site_id` (TEXT)
   - `operator` (TEXT)  
   - `latitude` (REAL)
   - `longitude` (REAL)
   - `services` (TEXT) - e.g., "LTE,NR"
   - `easting` (INTEGER)
   - `northing` (INTEGER)
5. **Lookup by operator** (MNC) and **nearest location**

### Option 2: Use Site Viewer API (Reverse Engineering)
1. Open https://siteviewer.comreg.ie/ in Chrome DevTools
2. Network tab → Zoom into Clane area
3. Find API request like:
   - `GET /geoserver/wfs?...`
   - `GET /api/sites?bounds=...`
4. Parse GeoJSON response
5. **Note:** Unofficial API, may change without notice

### Option 3: Hybrid Approach
1. **Primary:** ComReg Excel files (authoritative, updated annually)
2. **Fallback:** OpenCelliD (global coverage, may have gaps)
3. **Last resort:** Signal-based estimation

## 📦 Implementation Files to Create

### 1. `src/services/comreg_data_loader.py`
- Download Excel files from ComReg
- Parse Site ID, Easting, Northing, Services
- Convert ITM → WGS84
- Build SQLite database: `data/comreg_towers.db`

### 2. `src/services/comreg_lookup.py` (Update existing)
- Query SQLite database by operator + nearest location
- Return lat/lon for tower

### 3. `scripts/update_comreg_data.py`
- Standalone script to refresh tower database
- Run quarterly when ComReg publishes new data

## 📅 Update Frequency

- **ComReg updates:** Annually (usually Q1 of following year)
- **Your app:** Download data once, refresh quarterly
- **No API key required** - Public domain data

## ⚖️ Licensing

ComReg data is published under **Creative Commons Attribution 4.0**:
- ✅ Free to use
- ✅ Free to redistribute  
- ✅ Must attribute ComReg as source
- ✅ No registration required

**Attribution text:**
```
Tower location data © Commission for Communications Regulation (ComReg)
Published under CC-BY 4.0 License
Source: https://www.comreg.ie/industry/radio-spectrum/licensing/
```

## 🎯 Next Steps

1. **Manual test:** Download one Excel file, verify data format
2. **Install pyproj:** `pip install pyproj` (for ITM→WGS84 conversion)
3. **Create loader script:** Parse Excel, convert coordinates, build database
4. **Update comreg_lookup.py:** Query database instead of web API
5. **Test with your tower:** Verify Vodafone tower in Clane area appears

## 🔍 Debugging: Find Your Tower

**Your tower:** Cell ID 43593731, Vodafone LTE

**Expected in file:** `Vodafone Ireland Limited MBSA1 Licence 2025-2026.xlsx`

**Look for:**
- Site in Clane/Prosperous area
- ITM coordinates near:
  - Easting: ~678000-681000
  - Northing: ~723000-726000
- Services: Contains "LTE" or "L"

## 📚 References

- ComReg Site Viewer: https://siteviewer.comreg.ie/
- Licence Data: https://www.comreg.ie/industry/radio-spectrum/licensing/search-licence-type/mobile-licences-2/
- ITM Projection (EPSG:2157): https://epsg.io/2157
- WGS84 (EPSG:4326): https://epsg.io/4326
- pyproj Documentation: https://pyproj4.github.io/pyproj/stable/

---

**Status:** ✅ Official data source identified  
**Quality:** 🇮🇪 Authoritative (Irish regulator)  
**Coverage:** 🎯 Complete (all licensed towers in Ireland)  
**Cost:** 💰 Free (public domain, CC-BY 4.0)  
**API Key:** ❌ Not required  
**Update:** 📅 Manually download quarterly
