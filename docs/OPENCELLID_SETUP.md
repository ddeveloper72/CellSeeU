# OpenCelliD API Configuration

## What is OpenCelliD?

OpenCelliD is a free, crowdsourced database of cell tower locations worldwide. It contains GPS coordinates for millions of cell towers based on their Cell ID, MCC (Mobile Country Code), and MNC (Mobile Network Code).

## How to Get Real Tower Locations

### Option 1: Use OpenCelliD API (Recommended for Production)

1. **Register for free API key:**
   - Visit: https://opencellid.org/
   - Click "Sign Up" → Create account
   - Go to API section → Generate API token
   - Copy your token (looks like: `pk.xxxxxxxxxxxxx`)

2. **Add token to your app:**
   - Open: `src/services/tower_location.py`
   - Find line: `OPENCELLID_TOKEN = None`
   - Replace with: `OPENCELLID_TOKEN = "pk.your_token_here"`

3. **Restart Flask:**
   ```bash
   flask run --host=0.0.0.0 --port=5000
   ```

4. **Scan on your phone:**
   - The app will now lookup REAL tower coordinates!
   - If found in database: `location_source: 'opencellid'`
   - If not found: Falls back to signal-based estimation

### Option 2: Use Signal-Based Estimation (Current Fallback)

Without an API key, the app estimates tower positions based on:
- **Signal strength** → Distance from device
- **Cell ID** → Consistent random direction

**Pros:** Works immediately, no API key needed
**Cons:** Not accurate, towers appear in random locations

## How It Works

```python
# 1. Try OpenCelliD lookup first
result = lookup_tower_location(mcc=272, mnc=1, lac=53101, cell_id=43593731)
# → Returns: (53.2912, -6.6234, 1000)  # Real GPS coordinates!

# 2. If not found, fall back to estimation
if not result:
    estimate_from_signal(device_lat, device_lon, signal_dbm=-85, cell_id)
    # → Returns estimated position ~300-800m from device
```

## Coverage

OpenCelliD has excellent coverage in Ireland:
- **Vodafone Ireland** (MCC=272, MNC=1): ~2,500 towers
- **Three Ireland** (MCC=272, MNC=2): ~1,800 towers  
- **Eir Mobile** (MCC=272, MNC=3): ~1,200 towers

Most major towers in Dublin, Cork, Galway, Limerick are in the database.

## Alternative APIs

If OpenCelliD doesn't have your tower:

1. **Google Geolocation API**
   - Most accurate, uses Google's database
   - Requires API key + billing account
   - Free tier: 40,000 requests/month
   - See: https://developers.google.com/maps/documentation/geolocation

2. **Unwired Labs LocationAPI**
   - Commercial, paid plans only
   - Very accurate for major carriers
   - See: https://unwiredlabs.com/

3. **Mozilla Location Service (MLS)**
   - Was free, now deprecated (shut down 2024)
   - Historical data might be available elsewhere

## Privacy Note

When using OpenCelliD:
- Your tower lookups are logged by OpenCelliD
- Consider this when using in production
- For educational/diagnostic use, this is fine
- Read their privacy policy: https://opencellid.org/privacy
