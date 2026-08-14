import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Marker } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { 
  Flame, 
  Wind, 
  Droplets, 
  AlertTriangle, 
  UserPlus, 
  Send, 
  RefreshCw, 
  Layers, 
  ShieldAlert,
  Sparkles,
  Search,
  CheckCircle,
  AlertCircle
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

// Coordinates centered around Ludhiana, Punjab to focus the map
const MAP_CENTER = [30.5000, 76.2000];
const DEFAULT_ZOOM = 7.5;

function App() {
  const [districts, setDistricts] = useState([]);
  const [hotspotsData, setHotspotsData] = useState({ hotspots: [], clusters: [], noise: [] });
  const [farmers, setFarmers] = useState([]);
  const [advisories, setAdvisories] = useState([]);
  
  const [mapMode, setMapMode] = useState('live'); // 'live' or 'prediction'
  const [selectedDistrict, setSelectedDistrict] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Registration form state
  const [farmerName, setFarmerName] = useState('');
  const [farmerPhone, setFarmerPhone] = useState('');
  const [farmerDistrict, setFarmerDistrict] = useState('');
  const [farmerLang, setFarmerLang] = useState('Hindi');
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [formMsg, setFormMsg] = useState({ text: '', type: '' });

  // Fetch initial data
  const fetchData = async () => {
    try {
      const distRes = await fetch(`${API_BASE}/api/districts`);
      const districtsData = await distRes.json();
      setDistricts(districtsData);

      const hotRes = await fetch(`${API_BASE}/api/hotspots`);
      const hotData = await hotRes.json();
      setHotspotsData(hotData);

      const farmRes = await fetch(`${API_BASE}/api/farmers`);
      const farmData = await farmRes.json();
      setFarmers(farmData);

      const advRes = await fetch(`${API_BASE}/api/advisories`);
      const advData = await advRes.json();
      setAdvisories(advData);

      if (districtsData.length > 0 && !selectedDistrict) {
        // Set default selected district (e.g. Ludhiana or NCR)
        const defaultDist = districtsData.find(d => d.name === 'Sangrur') || districtsData[0];
        setSelectedDistrict(defaultDist);
      }
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = async (simulate = true) => {
    setRefreshing(true);
    try {
      const res = await fetch(`${API_BASE}/api/refresh?simulate=${simulate}`, {
        method: 'POST'
      });
      const data = await res.json();
      await fetchData();
      
      // Select the updated district details if currently selected
      if (selectedDistrict) {
        const updated = districts.find(d => d.id === selectedDistrict.id);
        if (updated) setSelectedDistrict(updated);
      }
      
      setFormMsg({ text: 'System states updated with live predictions.', type: 'success' });
      setTimeout(() => setFormMsg({ text: '', type: '' }), 5000);
    } catch (error) {
      console.error("Error refreshing data:", error);
      setFormMsg({ text: 'Failed to update system state.', type: 'error' });
    } finally {
      setRefreshing(false);
    }
  };

  const handleRegisterFarmer = async (e) => {
    e.preventDefault();
    if (!farmerName || !farmerPhone || !farmerDistrict) {
      setFormMsg({ text: 'Please fill in all fields.', type: 'error' });
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/farmers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: farmerName,
          phone: farmerPhone,
          district_id: parseInt(farmerDistrict),
          language: farmerLang
        })
      });

      const resData = await response.json();
      if (response.ok) {
        setFormMsg({ text: `Farmer ${farmerName} registered successfully!`, type: 'success' });
        setFarmerName('');
        setFarmerPhone('');
        setFarmerDistrict('');
        // Reload farmer lists
        const farmRes = await fetch(`${API_BASE}/api/farmers`);
        const farmData = await farmRes.json();
        setFarmers(farmData);
        
        // Auto trigger advisories to send one to this farmer if district is at risk
        fetch(`${API_BASE}/api/trigger-advisory`, { method: 'POST' }).then(() => {
          fetch(`${API_BASE}/api/advisories`).then(r => r.json()).then(data => setAdvisories(data));
        });
      } else {
        setFormMsg({ text: resData.detail || 'Registration failed.', type: 'error' });
      }
    } catch (error) {
      setFormMsg({ text: 'Error connecting to server.', type: 'error' });
    }
    setTimeout(() => setFormMsg({ text: '', type: '' }), 5000);
  };

  const triggerAdvisoryManually = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/trigger-advisory`, { method: 'POST' });
      const data = await res.json();
      const advRes = await fetch(`${API_BASE}/api/advisories`);
      const advData = await advRes.json();
      setAdvisories(advData);
      setFormMsg({ 
        text: `Advisories dispatched! ${data.advisories_sent || 0} alerts logged.`, 
        type: 'success' 
      });
      setTimeout(() => setFormMsg({ text: '', type: '' }), 5000);
    } catch (error) {
      console.error("Error triggering advisories:", error);
    }
  };

  // Helper for rendering wind rotation icons on map
  const getWindIcon = (windDir) => {
    return L.divIcon({
      html: `<div style="transform: rotate(${windDir}deg); color: #06b6d4; font-size: 16px; font-weight: 800; text-align: center; width: 24px; height: 24px;">↑</div>`,
      className: 'wind-direction-arrow',
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });
  };

  const filteredDistricts = districts.filter(d => 
    d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.state.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Statistics summaries
  const totalFires = hotspotsData.hotspots.length;
  const highRiskCount = districts.filter(d => d.risk_level === 'High').length;
  const avgAQI = districts.length > 0 
    ? Math.round(districts.reduce((acc, d) => acc + (d.aqi || 0), 0) / districts.length) 
    : 0;

  if (loading) {
    return (
      <div style={{
        display: 'flex', 
        flexDirection: 'column',
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh', 
        backgroundColor: '#08090c',
        gap: '16px'
      }}>
        <RefreshCw className="animate-spin" size={48} color="#6366f1" />
        <p style={{ fontFamily: 'Outfit', color: '#9ca3af' }}>Loading Early-Warning System dashboard...</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header glass-panel">
        <div className="header-brand">
          <ShieldAlert size={28} color="#6366f1" style={{ filter: 'drop-shadow(0 0 8px rgba(99, 102, 241, 0.6))' }} />
          <div>
            <h1>KrishiKavach</h1>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Stubble Burning Early-Warning & Farmer Advisory</span>
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div className="badge-live">
            <span className="badge-live-dot"></span>
            Demo Environment Active
          </div>
          
          <button 
            className="map-btn" 
            onClick={() => handleRefresh(true)} 
            disabled={refreshing}
            style={{ border: '1px solid rgba(99, 102, 241, 0.4)' }}
          >
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
            {refreshing ? 'Simulating...' : 'Simulate Season'}
          </button>

          <button 
            className="map-btn" 
            onClick={() => handleRefresh(false)} 
            disabled={refreshing}
          >
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
            Refresh NASA Live
          </button>
        </div>
      </header>

      {/* Left Column: Metrics & Farmer Registration */}
      <aside className="dashboard-sidebar">
        {/* Metric Summary Cards */}
        <div className="glass-panel" style={{ padding: '16px' }}>
          <h3 style={{ fontSize: '0.95rem', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={16} color="var(--color-info)" />
            Aerosol & Burn Metrics
          </h3>
          <div className="metric-grid">
            <div className="metric-card">
              <div className="metric-card-label">Active Fires</div>
              <div className="metric-card-value" style={{ color: 'var(--color-danger)' }}>{totalFires}</div>
            </div>
            <div className="metric-card">
              <div className="metric-card-label">High-Risk Zones</div>
              <div className="metric-card-value" style={{ color: 'var(--color-warning)' }}>{highRiskCount}</div>
            </div>
            <div className="metric-card" style={{ gridColumn: 'span 2' }}>
              <div className="metric-card-label">Regional Average AQI</div>
              <div className="metric-card-value" style={{ 
                color: avgAQI > 300 ? 'var(--color-danger)' : (avgAQI > 150 ? 'var(--color-warning)' : 'var(--color-success)'),
                display: 'flex',
                alignItems: 'baseline',
                gap: '8px'
              }}>
                {avgAQI}
                <span style={{ fontSize: '0.75rem', fontWeight: 'normal', color: 'var(--text-secondary)' }}>
                  {avgAQI > 300 ? '(Severe)' : (avgAQI > 150 ? '(Poor)' : '(Moderate)')}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Farmer Registration Form */}
        <div className="glass-panel" style={{ padding: '16px' }}>
          <h3 style={{ fontSize: '0.95rem', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <UserPlus size={16} color="var(--color-primary)" />
            Farmer Registration Portal
          </h3>
          <form onSubmit={handleRegisterFarmer}>
            <div className="form-group">
              <label>Farmer Name</label>
              <input 
                type="text" 
                className="form-control" 
                placeholder="e.g. Gurpreet Singh"
                value={farmerName}
                onChange={e => setFarmerName(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Phone Number (SMS Alert Target)</label>
              <input 
                type="tel" 
                className="form-control" 
                placeholder="e.g. +91 9876543210"
                value={farmerPhone}
                onChange={e => setFarmerPhone(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Farming District</label>
              <select 
                className="form-control"
                value={farmerDistrict}
                onChange={e => setFarmerDistrict(e.target.value)}
                required
              >
                <option value="">Select District</option>
                {districts.filter(d => d.state !== 'Delhi').map(d => (
                  <option key={d.id} value={d.id}>{d.name} ({d.state})</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Preferred Alert Language</label>
              <div style={{ display: 'flex', gap: '16px', marginTop: '4px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', cursor: 'pointer' }}>
                  <input 
                    type="radio" 
                    name="lang" 
                    value="Hindi" 
                    checked={farmerLang === 'Hindi'}
                    onChange={() => setFarmerLang('Hindi')}
                  />
                  हिन्दी (Hindi)
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', cursor: 'pointer' }}>
                  <input 
                    type="radio" 
                    name="lang" 
                    value="English" 
                    checked={farmerLang === 'English'}
                    onChange={() => setFarmerLang('English')}
                  />
                  English
                </label>
              </div>
            </div>
            {formMsg.text && (
              <div style={{
                padding: '8px 12px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                marginBottom: '10px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                background: formMsg.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: formMsg.type === 'success' ? 'var(--color-success)' : 'var(--color-danger)',
                border: `1px solid ${formMsg.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
              }}>
                {formMsg.type === 'success' ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
                {formMsg.text}
              </div>
            )}
            <button type="submit" className="btn-submit" style={{ width: '100%' }}>
              <UserPlus size={16} />
              Register Farmer
            </button>
          </form>
        </div>

        {/* Farmer SMS Dispatch Log */}
        <div className="glass-panel" style={{ padding: '16px', flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Send size={16} color="var(--color-info)" />
              Advisory Dispatch Log
            </h3>
            <button 
              onClick={triggerAdvisoryManually} 
              style={{
                background: 'transparent',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                color: 'var(--text-primary)',
                fontSize: '0.7rem',
                padding: '4px 8px',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
            >
              Trigger Broadcast
            </button>
          </div>
          
          <div className="alert-log-container">
            {advisories.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '24px' }}>
                No alerts dispatched yet. Registration triggers or manual broadcast will populate alerts.
              </div>
            ) : (
              advisories.map(adv => (
                <div key={adv.id} className={`sms-card ${districts.find(d => d.name === adv.district_name)?.risk_level || 'Low'}`}>
                  <div className="sms-card-header">
                    <span>TO: {adv.farmer_name} ({adv.farmer_phone})</span>
                    <span>{new Date(adv.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                  <div className="sms-card-body">
                    {adv.message}
                  </div>
                  <div className="sms-card-footer">
                    <span>District: {adv.district_name}</span>
                    <span className={`status-badge ${adv.status}`}>{adv.status}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </aside>

      {/* Central Panel: Leaflet Map Overlay */}
      <main className="glass-panel map-panel" style={{ padding: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', zIndex: 1001 }}>
          <h2 style={{ fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={18} color="var(--color-primary)" />
            Interactive Spatial Dashboard
          </h2>
          
          {/* Layer/Mode Toggles */}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button 
              className={`map-btn ${mapMode === 'live' ? 'active' : ''}`}
              onClick={() => setMapMode('live')}
            >
              <Flame size={14} />
              Current Hotspots
            </button>
            <button 
              className={`map-btn ${mapMode === 'prediction' ? 'active' : ''}`}
              onClick={() => setMapMode('prediction')}
            >
              <AlertTriangle size={14} />
              24-48hr Forecast Model
            </button>
          </div>
        </div>

        {/* Leaflet map container */}
        <div className="map-container-wrapper">
          <MapContainer center={MAP_CENTER} zoom={DEFAULT_ZOOM} scrollWheelZoom={true}>
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            />
            
            {/* Live Hotspots Mode */}
            {mapMode === 'live' && hotspotsData.hotspots.map((h, i) => (
              <CircleMarker
                key={`hotspot-${i}`}
                center={[h.latitude, h.longitude]}
                radius={4 + (h.confidence / 30)}
                fillColor="#ef4444"
                color="#f43f5e"
                weight={1}
                opacity={0.8}
                fillOpacity={0.8}
              >
                <Popup>
                  <div style={{ color: '#000', fontSize: '0.8rem' }}>
                    <strong>Active Hotspot</strong><br />
                    Lat: {h.latitude.toFixed(4)}<br />
                    Lon: {h.longitude.toFixed(4)}<br />
                    Confidence: {h.confidence.toFixed(1)}%<br />
                    Detected in: {h.district_name || 'Unassigned'}
                  </div>
                </Popup>
              </CircleMarker>
            ))}

            {/* DBSCAN Clusters (Overlay circles in Live Mode) */}
            {mapMode === 'live' && hotspotsData.clusters.map((c, i) => (
              <CircleMarker
                key={`cluster-${i}`}
                center={c.centroid}
                radius={25 + c.fire_count * 3}
                fillColor="#f59e0b"
                color="#d97706"
                weight={2}
                opacity={0.6}
                fillOpacity={0.15}
                dashArray="5, 10"
              >
                <Popup>
                  <div style={{ color: '#000', fontSize: '0.8rem' }}>
                    <strong style={{ color: 'var(--color-warning)' }}>Active Burning Zone (DBSCAN Cluster)</strong><br />
                    Cluster ID: {c.cluster_id}<br />
                    Hotspots Count: {c.fire_count}<br />
                    Mean Confidence: {c.avg_confidence.toFixed(1)}%<br />
                    Status: High risk of downwind particulate transport.
                  </div>
                </Popup>
              </CircleMarker>
            ))}

            {/* Prediction Mode Overlays */}
            {mapMode === 'prediction' && districts.map((d) => {
              const riskColor = d.risk_level === 'High' 
                ? '#ef4444' 
                : (d.risk_level === 'Medium' ? '#f59e0b' : '#10b981');
              const opacity = d.risk_level === 'High' ? 0.35 : (d.risk_level === 'Medium' ? 0.25 : 0.08);
              
              return (
                <React.Fragment key={`district-pred-${d.id}`}>
                  {/* Large boundary overlay */}
                  <CircleMarker
                    center={[d.latitude, d.longitude]}
                    radius={30}
                    fillColor={riskColor}
                    color={riskColor}
                    weight={2}
                    opacity={0.8}
                    fillOpacity={opacity}
                  >
                    <Popup>
                      <div style={{ color: '#000', fontSize: '0.8rem' }}>
                        <strong>{d.name} ({d.state})</strong><br />
                        Forecast Risk: <strong style={{ color: riskColor }}>{d.risk_level}</strong><br />
                        Confidence: {(d.prediction_confidence * 100).toFixed(0)}%<br />
                        Current AQI: {d.aqi || 'N/A'}<br />
                        Wind Speed: {d.wind_speed?.toFixed(1) || 'N/A'} km/h<br />
                        Wind Dir: {d.wind_dir?.toFixed(0) || 'N/A'}°
                      </div>
                    </Popup>
                  </CircleMarker>

                  {/* Rotating Wind Arrow Marker */}
                  {d.wind_dir !== undefined && (
                    <Marker
                      position={[d.latitude, d.longitude]}
                      icon={getWindIcon(d.wind_dir)}
                    />
                  )}
                </React.Fragment>
              );
            })}
          </MapContainer>
        </div>
      </main>

      {/* Right Column: District Overview & ML Model Insights */}
      <aside className="dashboard-sidebar">
        {/* District list search & select */}
        <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', height: '360px', overflow: 'hidden' }}>
          <h3 style={{ fontSize: '0.95rem', marginBottom: '8px' }}>Regional Risk Standings</h3>
          
          <div style={{ position: 'relative', marginBottom: '10px' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-secondary)' }} />
            <input 
              type="text" 
              className="form-control" 
              placeholder="Search districts..." 
              style={{ paddingLeft: '32px', width: '100%' }}
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>

          <div style={{ flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
            {filteredDistricts.map(d => (
              <div 
                key={d.id} 
                className={`district-item ${selectedDistrict?.id === d.id ? 'active-item' : ''}`}
                onClick={() => setSelectedDistrict(d)}
                style={{
                  borderLeft: `3px solid ${
                    d.risk_level === 'High' ? 'var(--color-danger)' : (d.risk_level === 'Medium' ? 'var(--color-warning)' : 'var(--color-success)')
                  }`,
                  backgroundColor: selectedDistrict?.id === d.id ? 'rgba(255,255,255,0.06)' : ''
                }}
              >
                <div>
                  <div style={{ fontWeight: '600', fontSize: '0.85rem' }}>{d.name}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{d.state}</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div className="aqi-badge Low" style={{
                    background: d.aqi > 300 ? 'rgba(239,68,68,0.15)' : (d.aqi > 150 ? 'rgba(245,158,11,0.15)' : 'rgba(16,185,129,0.15)'),
                    color: d.aqi > 300 ? '#ef4444' : (d.aqi > 150 ? '#f59e0b' : '#10b981')
                  }}>{d.aqi}</div>
                  <div className={`risk-dot ${d.risk_level}`} title={`Risk: ${d.risk_level}`}></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Selected District Details */}
        {selectedDistrict && (
          <div className="glass-panel" style={{ padding: '16px', flex: 1 }}>
            <h3 style={{ fontSize: '0.95rem', marginBottom: '12px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px' }}>
              {selectedDistrict.name} Details
            </h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>State:</span>
                <span>{selectedDistrict.state}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Active Fires locally:</span>
                <span style={{ fontWeight: 'bold', color: selectedDistrict.active_fires > 0 ? 'var(--color-danger)' : 'var(--text-primary)' }}>
                  {selectedDistrict.active_fires}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Current AQI (PM2.5):</span>
                <span style={{ fontWeight: 'bold' }}>{selectedDistrict.aqi} ({selectedDistrict.pm25?.toFixed(0)} µg/m³)</span>
              </div>
              
              <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                <div style={{ flex: 1, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', padding: '6px', borderRadius: '8px', textAlign: 'center' }}>
                  <Wind size={16} color="var(--color-info)" style={{ marginBottom: '4px' }} />
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Wind</div>
                  <div style={{ fontWeight: 'bold', fontSize: '0.75rem' }}>{selectedDistrict.wind_speed?.toFixed(1)} km/h</div>
                </div>
                <div style={{ flex: 1, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', padding: '6px', borderRadius: '8px', textAlign: 'center' }}>
                  <Wind size={16} color="var(--color-info)" style={{ transform: `rotate(${selectedDistrict.wind_dir}deg)`, marginBottom: '4px' }} />
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Direction</div>
                  <div style={{ fontWeight: 'bold', fontSize: '0.75rem' }}>{selectedDistrict.wind_dir?.toFixed(0)}°</div>
                </div>
                <div style={{ flex: 1, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', padding: '6px', borderRadius: '8px', textAlign: 'center' }}>
                  <Droplets size={16} color="var(--color-primary)" style={{ marginBottom: '4px' }} />
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Humidity</div>
                  <div style={{ fontWeight: 'bold', fontSize: '0.75rem' }}>{selectedDistrict.humidity?.toFixed(0)}%</div>
                </div>
              </div>

              <div style={{ 
                marginTop: '8px',
                padding: '12px', 
                borderRadius: '8px', 
                background: selectedDistrict.risk_level === 'High' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(255,255,255,0.02)',
                border: `1px solid ${selectedDistrict.risk_level === 'High' ? 'rgba(239, 68, 68, 0.2)' : 'var(--border-color)'}`
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontWeight: '600' }}>24-48h Early Warning</span>
                  <span className={`aqi-badge ${selectedDistrict.risk_level}`} style={{ padding: '2px 6px', fontSize: '0.65rem' }}>
                    {selectedDistrict.risk_level} Risk
                  </span>
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                  Prediction Confidence: {(selectedDistrict.prediction_confidence * 100).toFixed(0)}%<br />
                  {selectedDistrict.prediction_features && (
                    <span>
                      Upwind fires weighted: {selectedDistrict.prediction_features.upwind_fires || 0}<br />
                      Wind vectors towards NCR: {selectedDistrict.wind_dir >= 300 && selectedDistrict.wind_dir <= 340 ? 'YES' : 'NO'}
                    </span>
                  )}
                </div>
              </div>
              
              {/* Feature Importance Panel (ML Interpretability) */}
              <div style={{ marginTop: '4px' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text-secondary)' }}>
                  ML Interpretability (RF Feature Weights)
                </div>
                <div className="bar-chart">
                  <div className="bar-row">
                    <div className="bar-label-container">
                      <span>Current Local AQI</span>
                      <span>42%</span>
                    </div>
                    <div className="bar-container"><div className="bar-fill" style={{ width: '42%' }}></div></div>
                  </div>
                  <div className="bar-row">
                    <div className="bar-label-container">
                      <span>Local Active Fires</span>
                      <span>34%</span>
                    </div>
                    <div className="bar-container"><div className="bar-fill" style={{ width: '34%' }}></div></div>
                  </div>
                  <div className="bar-row">
                    <div className="bar-label-container">
                      <span>Upwind Fires (Smoke Transport)</span>
                      <span>12%</span>
                    </div>
                    <div className="bar-container"><div className="bar-fill" style={{ width: '12%' }}></div></div>
                  </div>
                  <div className="bar-row">
                    <div className="bar-label-container">
                      <span>Wind Speed & Humidity</span>
                      <span>12%</span>
                    </div>
                    <div className="bar-container"><div className="bar-fill" style={{ width: '12%' }}></div></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}

export default App;
