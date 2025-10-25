import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const App = () => {
  const [currentView, setCurrentView] = useState('dashboard');
  const [hotels, setHotels] = useState([]);
  const [selectedHotel, setSelectedHotel] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);
  const [demandForecasts, setDemandForecasts] = useState([]);
  const [allocations, setAllocations] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchHotels();
  }, []);

  const fetchHotels = async () => {
    try {
      const response = await axios.get(`${API}/hotels`);
      setHotels(response.data);
      if (response.data.length > 0) {
        setSelectedHotel(response.data[0]);
      }
    } catch (error) {
      console.error('Error fetching hotels:', error);
    }
  };

  const fetchDashboardData = async (hotelId) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/analytics/${hotelId}/dashboard`);
      setDashboardData(response.data);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDemandForecasts = async (hotelId) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/forecast/${hotelId}`);
      setDemandForecasts(response.data);
    } catch (error) {
      console.error('Error fetching demand forecasts:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAllocations = async (hotelId) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/allocations/${hotelId}`);
      setAllocations(response.data);
    } catch (error) {
      console.error('Error fetching allocations:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRecommendations = async (hotelId) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/rates/${hotelId}/recommendations`);
      setRecommendations(response.data);
    } catch (error) {
      console.error('Error fetching recommendations:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchBookings = async (hotelId) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/bookings?hotel_id=${hotelId}`);
      setBookings(response.data);
    } catch (error) {
      console.error('Error fetching bookings:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateDemandForecast = async (hotelId) => {
    try {
      setLoading(true);
      await axios.post(`${API}/forecast/${hotelId}`);
      fetchDemandForecasts(hotelId);
    } catch (error) {
      console.error('Error generating demand forecast:', error);
    } finally {
      setLoading(false);
    }
  };

  const optimizeInventory = async (hotelId) => {
    try {
      setLoading(true);
      await axios.post(`${API}/allocations/${hotelId}/optimize`);
      fetchAllocations(hotelId);
    } catch (error) {
      console.error('Error optimizing inventory:', error);
    } finally {
      setLoading(false);
    }
  };

  const optimizeRates = async (hotelId) => {
    try {
      setLoading(true);
      await axios.post(`${API}/rates/${hotelId}/optimize`);
      fetchRecommendations(hotelId);
    } catch (error) {
      console.error('Error optimizing rates:', error);
    } finally {
      setLoading(false);
    }
  };

  const createSampleHotel = async () => {
    try {
      const sampleHotel = {
        name: "Grand Plaza Hotel",
        location: "New York, NY",
        total_rooms: 200,
        room_types: {
          standard: 100,
          deluxe: 60,
          suite: 30,
          presidential: 10
        }
      };
      await axios.post(`${API}/hotels`, sampleHotel);
      fetchHotels();
    } catch (error) {
      console.error('Error creating sample hotel:', error);
    }
  };

  const createSampleBooking = async (hotelId) => {
    try {
      const sampleBooking = {
        hotel_id: hotelId,
        room_id: "room-123",
        guest_name: "John Doe",
        guest_email: "john.doe@example.com",
        check_in_date: new Date().toISOString(),
        check_out_date: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
        room_type: "standard",
        channel: "direct",
        rate: 150.00
      };
      await axios.post(`${API}/bookings`, sampleBooking);
      fetchBookings(hotelId);
    } catch (error) {
      console.error('Error creating sample booking:', error);
    }
  };

  useEffect(() => {
    if (selectedHotel) {
      if (currentView === 'dashboard') {
        fetchDashboardData(selectedHotel.id);
      } else if (currentView === 'forecast') {
        fetchDemandForecasts(selectedHotel.id);
      } else if (currentView === 'inventory') {
        fetchAllocations(selectedHotel.id);
      } else if (currentView === 'pricing') {
        fetchRecommendations(selectedHotel.id);
      } else if (currentView === 'bookings') {
        fetchBookings(selectedHotel.id);
      }
    }
  }, [currentView, selectedHotel]);

  const renderDashboard = () => (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">Revenue Dashboard</h2>
        {dashboardData && (
          <div className="metrics-grid">
            <div className="metric-card">
              <h3 className="metric-title">Total Revenue</h3>
              <p className="metric-value">${dashboardData.metrics.total_revenue}</p>
            </div>
            <div className="metric-card">
              <h3 className="metric-title">Occupancy Rate</h3>
              <p className="metric-value">{dashboardData.metrics.occupancy_rate}%</p>
            </div>
            <div className="metric-card">
              <h3 className="metric-title">ADR</h3>
              <p className="metric-value">${dashboardData.metrics.adr}</p>
            </div>
            <div className="metric-card">
              <h3 className="metric-title">RevPAR</h3>
              <p className="metric-value">${dashboardData.metrics.revpar}</p>
            </div>
          </div>
        )}
      </div>
      
      {dashboardData && (
        <div className="performance-section">
          <div className="performance-grid">
            <div className="performance-card">
              <h3 className="performance-title">Channel Performance</h3>
              <div className="performance-list">
                {Object.entries(dashboardData.channel_performance).map(([channel, data]) => (
                  <div key={channel} className="performance-item">
                    <span className="channel-name">{channel}</span>
                    <div className="channel-stats">
                      <span className="bookings">{data.bookings} bookings</span>
                      <span className="revenue">${data.revenue}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="performance-card">
              <h3 className="performance-title">Room Type Performance</h3>
              <div className="performance-list">
                {Object.entries(dashboardData.room_type_performance).map(([roomType, data]) => (
                  <div key={roomType} className="performance-item">
                    <span className="room-type-name">{roomType}</span>
                    <div className="room-stats">
                      <span className="bookings">{data.bookings} bookings</span>
                      <span className="revenue">${data.revenue}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const renderForecast = () => (
    <div className="forecast-section">
      <div className="section-header">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">Demand Forecasting</h2>
        <button 
          onClick={() => generateDemandForecast(selectedHotel.id)}
          className="action-button"
          disabled={loading}
        >
          {loading ? 'Generating...' : 'Generate Forecast'}
        </button>
      </div>
      
      <div className="forecast-grid">
        {demandForecasts.map((forecast) => (
          <div key={forecast.id} className="forecast-card">
            <div className="forecast-header">
              <h3 className="forecast-room-type">{forecast.room_type}</h3>
              <span className="forecast-date">{new Date(forecast.date).toLocaleDateString()}</span>
            </div>
            <div className="forecast-metrics">
              <div className="forecast-metric">
                <span className="metric-label">Predicted Demand</span>
                <span className="metric-value">{forecast.predicted_demand}</span>
              </div>
              <div className="forecast-metric">
                <span className="metric-label">Predicted ADR</span>
                <span className="metric-value">${forecast.predicted_adr}</span>
              </div>
              <div className="forecast-metric">
                <span className="metric-label">Confidence</span>
                <span className="metric-value">{(forecast.confidence_score * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderInventory = () => (
    <div className="inventory-section">
      <div className="section-header">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">Inventory Management</h2>
        <button 
          onClick={() => optimizeInventory(selectedHotel.id)}
          className="action-button"
          disabled={loading}
        >
          {loading ? 'Optimizing...' : 'Optimize Allocation'}
        </button>
      </div>
      
      <div className="allocation-grid">
        {allocations.map((allocation) => (
          <div key={allocation.id} className="allocation-card">
            <div className="allocation-header">
              <h3 className="allocation-room-type">{allocation.room_type}</h3>
              <span className="allocation-date">{new Date(allocation.date).toLocaleDateString()}</span>
            </div>
            <div className="allocation-details">
              <div className="allocation-detail">
                <span className="detail-label">Channel</span>
                <span className="detail-value">{allocation.channel}</span>
              </div>
              <div className="allocation-detail">
                <span className="detail-label">Allocated Rooms</span>
                <span className="detail-value">{allocation.allocated_rooms}</span>
              </div>
              <div className="allocation-detail">
                <span className="detail-label">Rate</span>
                <span className="detail-value">${allocation.rate}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderPricing = () => (
    <div className="pricing-section">
      <div className="section-header">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">Rate Optimization</h2>
        <button 
          onClick={() => optimizeRates(selectedHotel.id)}
          className="action-button"
          disabled={loading}
        >
          {loading ? 'Optimizing...' : 'Optimize Rates'}
        </button>
      </div>
      
      <div className="recommendations-grid">
        {recommendations.map((rec) => (
          <div key={rec.id} className="recommendation-card">
            <div className="recommendation-header">
              <h3 className="recommendation-room-type">{rec.room_type}</h3>
              <span className="recommendation-date">{new Date(rec.date).toLocaleDateString()}</span>
            </div>
            <div className="recommendation-details">
              <div className="rate-comparison">
                <div className="rate-item">
                  <span className="rate-label">Current Rate</span>
                  <span className="rate-value">${rec.current_rate}</span>
                </div>
                <div className="rate-item">
                  <span className="rate-label">Recommended Rate</span>
                  <span className="rate-value recommended">${rec.recommended_rate}</span>
                </div>
              </div>
              <div className="recommendation-impact">
                <div className="impact-item">
                  <span className="impact-label">Expected Revenue Lift</span>
                  <span className={`impact-value ${rec.expected_revenue_lift >= 0 ? 'positive' : 'negative'}`}>
                    ${rec.expected_revenue_lift}
                  </span>
                </div>
                <div className="recommendation-reason">
                  <span className="reason-label">Reason</span>
                  <span className="reason-text">{rec.reason}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderBookings = () => (
    <div className="bookings-section">
      <div className="section-header">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">Booking Management</h2>
        <button 
          onClick={() => createSampleBooking(selectedHotel.id)}
          className="action-button"
        >
          Add Sample Booking
        </button>
      </div>
      
      <div className="bookings-table">
        <div className="table-header">
          <span>Guest Name</span>
          <span>Room Type</span>
          <span>Check-in</span>
          <span>Check-out</span>
          <span>Channel</span>
          <span>Rate</span>
          <span>Status</span>
        </div>
        {bookings.map((booking) => (
          <div key={booking.id} className="table-row">
            <span>{booking.guest_name}</span>
            <span>{booking.room_type}</span>
            <span>{new Date(booking.check_in_date).toLocaleDateString()}</span>
            <span>{new Date(booking.check_out_date).toLocaleDateString()}</span>
            <span>{booking.channel}</span>
            <span>${booking.rate}</span>
            <span className={`status ${booking.status}`}>{booking.status}</span>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="app">
      <div className="sidebar">
        <div className="sidebar-header">
          <h1 className="app-title">Hotel Revenue Management</h1>
          <div className="hotel-selector">
            <select 
              value={selectedHotel?.id || ''} 
              onChange={(e) => setSelectedHotel(hotels.find(h => h.id === e.target.value))}
              className="hotel-select"
            >
              {hotels.map(hotel => (
                <option key={hotel.id} value={hotel.id}>{hotel.name}</option>
              ))}
            </select>
          </div>
        </div>
        
        <nav className="sidebar-nav">
          <button 
            onClick={() => setCurrentView('dashboard')}
            className={`nav-item ${currentView === 'dashboard' ? 'active' : ''}`}
          >
            Dashboard
          </button>
          <button 
            onClick={() => setCurrentView('forecast')}
            className={`nav-item ${currentView === 'forecast' ? 'active' : ''}`}
          >
            Demand Forecasting
          </button>
          <button 
            onClick={() => setCurrentView('inventory')}
            className={`nav-item ${currentView === 'inventory' ? 'active' : ''}`}
          >
            Inventory Management
          </button>
          <button 
            onClick={() => setCurrentView('pricing')}
            className={`nav-item ${currentView === 'pricing' ? 'active' : ''}`}
          >
            Rate Optimization
          </button>
          <button 
            onClick={() => setCurrentView('bookings')}
            className={`nav-item ${currentView === 'bookings' ? 'active' : ''}`}
          >
            Bookings
          </button>
        </nav>
        
        <div className="sidebar-footer">
          <button onClick={createSampleHotel} className="sample-button">
            Create Sample Hotel
          </button>
        </div>
      </div>
      
      <div className="main-content">
        {loading && <div className="loading-overlay">Loading...</div>}
        
        {!selectedHotel ? (
          <div className="empty-state">
            <h2>No Hotels Found</h2>
            <p>Create a sample hotel to get started</p>
            <button onClick={createSampleHotel} className="create-hotel-button">
              Create Sample Hotel
            </button>
          </div>
        ) : (
          <div className="content">
            {currentView === 'dashboard' && renderDashboard()}
            {currentView === 'forecast' && renderForecast()}
            {currentView === 'inventory' && renderInventory()}
            {currentView === 'pricing' && renderPricing()}
            {currentView === 'bookings' && renderBookings()}
          </div>
        )}
      </div>
    </div>
  );
};

export default App;