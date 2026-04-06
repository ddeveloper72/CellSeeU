package com.cellseeu.scanner;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.location.Location;
import android.telephony.CellIdentityLte;
import android.telephony.CellIdentityNr;
import android.telephony.CellIdentityGsm;
import android.telephony.CellIdentityWcdma;
import android.telephony.CellInfo;
import android.telephony.CellInfoLte;
import android.telephony.CellInfoNr;
import android.telephony.CellInfoGsm;
import android.telephony.CellInfoWcdma;
import android.telephony.CellSignalStrength;
import android.telephony.TelephonyManager;
import android.util.Log;

import androidx.core.app.ActivityCompat;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.List;

/**
 * Scans for cell towers using Android TelephonyManager API
 * 
 * Detects all nearby cell towers including:
 * - LTE (4G)
 * - 5G NR (New Radio)
 * - WCDMA (3G)
 * - GSM (2G)
 */
public class CellTowerScanner {
    
    private static final String TAG = "CellTowerScanner";
    
    private final Context context;
    private final TelephonyManager telephonyManager;
    
    public CellTowerScanner(Context context) {
        this.context = context;
        this.telephonyManager = (TelephonyManager) context.getSystemService(Context.TELEPHONY_SERVICE);
    }
    
    /**
     * Scan for all nearby cell towers
     * 
     * @param deviceLocation Current GPS location of device (can be null)
     * @return JSON object containing tower data
     */
    public JSONObject scanTowers(Location deviceLocation) {
        JSONObject result = new JSONObject();
        
        try {
            // Add device location if available
            if (deviceLocation != null) {
                JSONObject locationJson = new JSONObject();
                locationJson.put("latitude", deviceLocation.getLatitude());
                locationJson.put("longitude", deviceLocation.getLongitude());
                locationJson.put("accuracy", deviceLocation.getAccuracy());
                locationJson.put("altitude", deviceLocation.getAltitude());
                result.put("device_location", locationJson);
                Log.i(TAG, String.format("Device location: %.6f, %.6f (±%.0fm)", 
                    deviceLocation.getLatitude(), 
                    deviceLocation.getLongitude(), 
                    deviceLocation.getAccuracy()));
            } else {
                Log.w(TAG, "⚠️ No device location available - tower coordinates cannot be estimated");
            }
            
            // Get all cell info
            List<CellInfo> cellInfoList = getAllCellInfo();
            
            if (cellInfoList == null || cellInfoList.isEmpty()) {
                Log.w(TAG, "No cell towers detected");
                result.put("towers", new JSONArray());
                result.put("error", "No cell towers detected - check permissions");
                return result;
            }
            
            Log.i(TAG, "getAllCellInfo() returned " + cellInfoList.size() + " cell tower(s)");
            
            if (cellInfoList.size() == 1) {
                Log.w(TAG, "Only 1 tower detected. This is normal - many Android devices/carriers only expose the serving cell, not neighboring towers.");
            }
            
            JSONArray towersArray = new JSONArray();
            
            for (CellInfo cellInfo : cellInfoList) {
                JSONObject towerJson = parseCellInfo(cellInfo);
                if (towerJson != null) {
                    towersArray.put(towerJson);
                    Log.d(TAG, "Parsed tower: " + towerJson.optString("network_type") + 
                          " signal=" + towerJson.optInt("signal_strength") + 
                          " registered=" + towerJson.optBoolean("registered"));
                } else {
                    Log.w(TAG, "Failed to parse tower: " + cellInfo.getClass().getSimpleName());
                }
            }
            
            result.put("towers", towersArray);
            result.put("count", towersArray.length());
            result.put("timestamp", System.currentTimeMillis());
            
            Log.i(TAG, "Detected " + towersArray.length() + " cell towers");
            
        } catch (JSONException e) {
            Log.e(TAG, "Error creating JSON result", e);
        }
        
        return result;
    }
    
    /**
     * Get all cell info from TelephonyManager
     */
    private List<CellInfo> getAllCellInfo() {
        // Check location permission
        if (ActivityCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) {
            Log.e(TAG, "Location permission not granted");
            return null;
        }
        
        // Check phone state permission (required for neighboring cells on Android 10+)
        if (ActivityCompat.checkSelfPermission(context, Manifest.permission.READ_PHONE_STATE)
                != PackageManager.PERMISSION_GRANTED) {
            Log.e(TAG, "Phone state permission not granted - may only return connected tower");
        }
        
        List<CellInfo> cellInfoList = telephonyManager.getAllCellInfo();
        
        if (cellInfoList != null) {
            Log.i(TAG, "getAllCellInfo() returned " + cellInfoList.size() + " tower(s) from TelephonyManager");
            Log.i(TAG, "Note: Android may limit neighboring cell info based on API level and carrier");
        }
        
        return cellInfoList;
    }
    
/**
     * Parse CellInfo into JSON format
     */
    private JSONObject parseCellInfo(CellInfo cellInfo) {
        try {
            if (cellInfo instanceof CellInfoLte) {
                return parseLteTower((CellInfoLte) cellInfo);
            } else if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q
                    && cellInfo instanceof CellInfoNr) {
                return parse5GNrTower((CellInfoNr) cellInfo);
            } else if (cellInfo instanceof CellInfoWcdma) {
                return parseWcdmaTower((CellInfoWcdma) cellInfo);
            } else if (cellInfo instanceof CellInfoGsm) {
                return parseGsmTower((CellInfoGsm) cellInfo);
            }
        } catch (Exception e) {
            Log.e(TAG, "Error parsing cell info", e);
        }
        
        return null;
    }
    
    /**
     * Parse LTE (4G) tower information
     */
    private JSONObject parseLteTower(CellInfoLte cellInfo) throws JSONException {
        JSONObject tower = new JSONObject();
        
        CellIdentityLte identity = cellInfo.getCellIdentity();
        int signalStrength = cellInfo.getCellSignalStrength().getDbm();
        
        // Get cell identity (unique identifier for the tower)
        int ci = identity.getCi();  // Cell Identity
        if (ci == Integer.MAX_VALUE) ci = 0;  // Invalid value
        
        tower.put("cell_id", ci);
        tower.put("tower_type", "TERRESTRIAL");
        tower.put("network_type", "LTE");
        
        // Get MCC and MNC (Mobile Country Code and Mobile Network Code)
        String mccString = identity.getMccString();
        String mncString = identity.getMncString();
        
        if (mccString != null && mncString != null) {
            tower.put("mcc", Integer.parseInt(mccString));
            tower.put("mnc", Integer.parseInt(mncString));
        }
        
        // Signal strength in dBm
        tower.put("signal_strength", signalStrength);
        
        // Check if this is the registered (connected) tower
        tower.put("registered", cellInfo.isRegistered());
        
        // Additional LTE-specific fields
        tower.put("tac", identity.getTac());  // Tracking Area Code
        tower.put("pci", identity.getPci());  // Physical Cell ID
        tower.put("earfcn", identity.getEarfcn());  // E-UTRA Absolute Radio Frequency Channel Number
        
        // Bandwidth (if available on newer Android versions)
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.P) {
            int bandwidth = identity.getBandwidth();
            if (bandwidth != Integer.MAX_VALUE) {
                tower.put("bandwidth_khz", bandwidth);
            }
        }
        
        return tower;
    }
    
    /**
     * Parse 5G NR tower information
     */
    private JSONObject parse5GNrTower(CellInfoNr cellInfo) throws JSONException {
        if (android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.Q) {
            return null;
        }
        
        JSONObject tower = new JSONObject();
        
        CellIdentityNr identity = (CellIdentityNr) cellInfo.getCellIdentity();
        int signalStrength = cellInfo.getCellSignalStrength().getDbm();
        
        // Get NCI (NR Cell Identity)
        long nci = identity.getNci();
        if (nci == Long.MAX_VALUE) nci = 0;
        
        tower.put("cell_id", nci);
        tower.put("tower_type", "TERRESTRIAL");  // Assume terrestrial unless detected otherwise
        tower.put("network_type", "5G_NR");
        
        // Get MCC and MNC
        String mccString = identity.getMccString();
        String mncString = identity.getMncString();
        
        if (mccString != null && mncString != null) {
            tower.put("mcc", Integer.parseInt(mccString));
            tower.put("mnc", Integer.parseInt(mncString));
        }
        
        tower.put("signal_strength", signalStrength);
        tower.put("registered", cellInfo.isRegistered());
        
        // 5G-specific fields
        tower.put("tac", identity.getTac());
        tower.put("pci", identity.getPci());
        tower.put("nrarfcn", identity.getNrarfcn());  // NR Absolute Radio Frequency Channel Number
        
        return tower;
    }
    
    /**
     * Parse WCDMA (3G) tower information
     */
    private JSONObject parseWcdmaTower(CellInfoWcdma cellInfo) throws JSONException {
        JSONObject tower = new JSONObject();
        
        CellIdentityWcdma identity = cellInfo.getCellIdentity();
        int signalStrength = cellInfo.getCellSignalStrength().getDbm();
        
        int cid = identity.getCid();
        if (cid == Integer.MAX_VALUE) cid = 0;
        
        tower.put("cell_id", cid);
        tower.put("tower_type", "TERRESTRIAL");
        tower.put("network_type", "WCDMA");
        
        String mccString = identity.getMccString();
        String mncString = identity.getMncString();
        
        if (mccString != null && mncString != null) {
            tower.put("mcc", Integer.parseInt(mccString));
            tower.put("mnc", Integer.parseInt(mncString));
        }
        
        tower.put("signal_strength", signalStrength);
        tower.put("registered", cellInfo.isRegistered());
        tower.put("lac", identity.getLac());  // Location Area Code
        tower.put("psc", identity.getPsc());  // Primary Scrambling Code
        
        return tower;
    }
    
    /**
     * Parse GSM (2G) tower information
     */
    private JSONObject parseGsmTower(CellInfoGsm cellInfo) throws JSONException {
        JSONObject tower = new JSONObject();
        
        CellIdentityGsm identity = cellInfo.getCellIdentity();
        int signalStrength = cellInfo.getCellSignalStrength().getDbm();
        
        int cid = identity.getCid();
        if (cid == Integer.MAX_VALUE) cid = 0;
        
        tower.put("cell_id", cid);
        tower.put("tower_type", "TERRESTRIAL");
        tower.put("network_type", "GSM");
        
        String mccString = identity.getMccString();
        String mncString = identity.getMncString();
        
        if (mccString != null && mncString != null) {
            tower.put("mcc", Integer.parseInt(mccString));
            tower.put("mnc", Integer.parseInt(mncString));
        }
        
        tower.put("signal_strength", signalStrength);
        tower.put("registered", cellInfo.isRegistered());
        tower.put("lac", identity.getLac());
        tower.put("arfcn", identity.getArfcn());  // Absolute Radio Frequency Channel Number
        
        return tower;
    }
}
