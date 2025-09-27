if (typeof window.RailwayDashboard === 'undefined') {
	class RailwayDashboard {
	    constructor() {
	        this.data = null;
	        this.chart = null;
	        this.stations = [];
	        this.trainPositions = [];
	        this.init();
	    }
	
	    async init() {
	        this.showLoading();
	        await this.loadData();
	        this.updateMetrics();
	        this.renderTimeDistanceGraph();
	        this.renderDecisions();
	        this.renderTrains();
	        this.hideLoading();
	        
	        // Auto-refresh every 30 seconds
	        this._refreshInterval = setInterval(() => this.refreshData(), 30000);
	    }
	
	    async loadData() {
	        try {
	            const response = await fetch('../section_report.json');
	            this.data = await response.json();
	            
	            if (this.data && this.data.stations) {
	                this.stations = this.data.stations;
	            } else {
	                this.initializeDefaultStations();
	            }
	            
	            // Generate train positions for the simple track view
	            this.generateTrainPositions();
	            
	        } catch (error) {
	            console.error('Error loading data:', error);
	            this.generateFallbackData();
	        }
	    }
	
	    generateFallbackData() {
	        this.data = {
	            metrics: {
	                active_trains: 12,
	                average_delay_minutes: 25.5,
	                average_speed_kmh: 68.2,
	                bottleneck_utilization: 0.45,
	                total_scheduled_trains: 20
	            },
	            decisions: {
	                "11001": {
	                    decision: "Give priority",
	                    confidence: 0.95,
	                    reasoning: "High priority express train"
	                },
	                "11002": {
	                    decision: "Reduce speed", 
	                    confidence: 0.88,
	                    reasoning: "Traffic congestion ahead"
	                }
	            },
	            critical_count: 3,
	            trains: this.generateMockTrains()
	        };
	        this.initializeDefaultStations();
	        this.generateTrainPositions();
	    }
	
	    generateTrainPositions() {
	        this.trainPositions = [];
	        const decisions = (this.data && this.data.decisions) ? this.data.decisions : {};
	        const trains = (this.data && this.data.trains) ? this.data.trains : this.generateMockTrains();
	        
	        trains.slice(0, 8).forEach((train) => {
	            let status = train.status || 'running';
	            
	            // Override status based on AI decision
	            const decision = decisions[train.train_number];
	            if (decision) {
	                if (decision.decision === 'Stop at next station') status = 'stopped';
	                else if (decision.decision === 'Hold/Reroute') status = 'delayed';
	            }
	            
	            this.trainPositions.push({
	                number: train.train_number,
	                position: (typeof train.current_km === 'number') ? train.current_km : Math.random() * 455.3,
	                status: status,
	                speed: train.speed || (40 + Math.random() * 60),
	                delay: train.delay_minutes || (Math.random() < 0.3 ? Math.random() * 60 : 0)
	            });
	        });
	    }
	
	    initializeDefaultStations() {
	        this.stations = [
	            { code: "SUR", name: "Solapur", km: 0 },
	            { code: "HOTGI", name: "Hotgi", km: 25.3 },
	            { code: "INDI", name: "Indi", km: 45.8 },
	            { code: "BIJAPUR", name: "Bijapur", km: 78.2 },
	            { code: "GADAG", name: "Gadag", km: 168.9 },
	            { code: "HUBLI", name: "Hubli", km: 285.4 },
	            { code: "DHARWAD", name: "Dharwad", km: 305.8 },
	            { code: "BGM", name: "Belagavi", km: 375.4 },
	            { code: "WDI", name: "Wadi", km: 455.3 }
	        ];
	    }
	
	    renderTimeDistanceGraph() {
	        const ctx = document.getElementById('time-distance-graph');
	        if (!ctx) return;
	
	        // Destroy existing chart
	        if (this.chart) {
	            this.chart.destroy();
	        }
	
	        const timeRangeEl = document.getElementById('time-range');
	        const timeRange = parseInt(timeRangeEl?.value || 12);
	        const now = new Date();
	        const endTime = new Date(now.getTime() + timeRange * 60 * 60 * 1000);
	
	        // Prepare datasets for each train
	        const datasets = [];
	        const trains = (this.data && this.data.trains) ? this.data.trains : this.generateMockTrains();
	
	        trains.slice(0, 6).forEach((train) => { // Limit to 6 trains for clarity
	            const trainData = this.generateTrainPath(train, now, endTime);
	            const color = this.getTrainColor(train);
	            
	            datasets.push({
	                label: `${train.train_number} (${train.train_type})`,
	                data: trainData,
	                borderColor: train.status === 'delayed' ? '#f39c12' : color,
	                backgroundColor: train.status === 'delayed' ? '#f39c12' : color,
	                borderWidth: train.status === 'delayed' ? 3 : 2,
	                borderDash: train.status === 'delayed' ? [10, 5] : [],
	                fill: false,
	                tension: 0.1,
	                pointRadius: 2,
	                pointHoverRadius: 5
	            });
	        });
	
	        this.chart = new Chart(ctx, {
	            type: 'line',
	            data: { datasets },
	            options: {
	                responsive: true,
	                maintainAspectRatio: false,
	                plugins: {
	                    title: {
	                        display: true,
	                        text: 'Train Movement - Time vs Distance',
	                        font: { size: 16, weight: 'bold' }
	                    },
	                    legend: {
	                        display: true,
	                        position: 'bottom',
	                        labels: {
	                            usePointStyle: true,
	                            padding: 20,
	                            font: { size: 12 }
	                        }
	                    },
	                    tooltip: {
	                        callbacks: {
	                            title: (items) => {
	                                const time = new Date(items[0].parsed.x);
	                                return time.toLocaleTimeString();
	                            },
	                            label: (item) => {
	                                const station = this.getNearestStation(item.parsed.y);
	                                return `${item.dataset.label}: ${item.parsed.y.toFixed(1)}km (near ${station})`;
	                            }
	                        }
	                    }
	                },
	                scales: {
	                    x: {
	                        type: 'time',
	                        time: {
	                            unit: 'hour',
	                            displayFormats: {
	                                hour: 'HH:mm'
	                            },
	                            tooltipFormat: 'HH:mm'
	                        },
	                        title: {
	                            display: true,
	                            text: 'Time',
	                            font: { weight: 'bold' }
	                        },
	                        min: now,
	                        max: endTime
	                    },
	                    y: {
	                        title: {
	                            display: true,
	                            text: 'Distance (km)',
	                            font: { weight: 'bold' }
	                        },
	                        min: 0,
	                        max: 455.3,
	                        ticks: {
	                            stepSize: 50,
	                            callback: (value) => {
	                                const station = this.stations.find(s => Math.abs(s.km - value) < 25);
	                                return station ? `${value}km (${station.code})` : `${value}km`;
	                            }
	                        }
	                    }
	                },
	                interaction: {
	                    intersect: false,
	                    mode: 'index'
	                }
	            }
	        });
	    }
	
	    generateTrainPath(train, startTime, endTime) {
	        const path = [];
	        const currentTime = new Date();
	        
	        // Calculate train's journey parameters
	        const totalDistance = 455.3;
	        const baseSpeed = train.speed || 60;
	        
	        // Start position
	        let startDistance = (typeof train.current_km === 'number') ? train.current_km : Math.random() * totalDistance;
	        
	        // Direction: 1 for SUR->WDI, -1 for WDI->SUR
	        const direction = train.destination === 'WDI' ? 1 : -1;
	        
	        // Generate path points every 15 minutes for smoother lines
	        const intervalMinutes = 15;
	        const intervalMs = intervalMinutes * 60 * 1000;
	        
	        for (let time = new Date(startTime); time <= endTime; time = new Date(time.getTime() + intervalMs)) {
	            const hoursFromNow = (time - currentTime) / (1000 * 60 * 60);
	            
	            // Calculate distance with some realistic variations
	            let distance = startDistance + (direction * baseSpeed * hoursFromNow);
	            
	            // Apply delay effects
	            if (train.status === 'delayed') {
	                distance -= (train.delay_minutes || 30) / 60 * baseSpeed * 0.3;
	            }
	            
	            // Keep within section bounds
	            distance = Math.max(0, Math.min(totalDistance, distance));
	            
	            path.push({ 
	                x: time.getTime(), // Use timestamp for Chart.js time scale
	                y: distance 
	            });
	            
	            // Stop if train reaches destination
	            if ((direction === 1 && distance >= totalDistance - 5) || 
	                (direction === -1 && distance <= 5)) {
	                break;
	            }
	        }
	        
	        return path;
	    }
	
	    getTrainColor(train) {
	        const colors = {
	            'express': '#e74c3c',
	            'superfast': '#e74c3c',
	            'passenger': '#3498db',
	            'freight': '#95a5a6'
	        };
	        return colors[train.train_type] || '#3498db';
	    }
	
	    getNearestStation(km) {
	        if (!this.stations || this.stations.length === 0) return '';
	        let nearest = this.stations[0];
	        let minDistance = Math.abs(nearest.km - km);
	        
	        for (const station of this.stations) {
	            const distance = Math.abs(station.km - km);
	            if (distance < minDistance) {
	                minDistance = distance;
	                nearest = station;
	            }
	        }
	        
	        return nearest.code;
	    }
	
	    generateMockTrains() {
	        // Generate mock train data for demonstration
	        const mockTrains = [];
	        const trainTypes = ['express', 'passenger', 'freight', 'superfast'];
	        
	        for (let i = 0; i < 8; i++) {
	            const trainType = trainTypes[i % trainTypes.length];
	            const isDelayed = Math.random() < 0.3;
	            
	            mockTrains.push({
	                train_number: `1100${i}`,
	                train_name: `${trainType} ${1100 + i}`,
	                train_type: trainType,
	                priority: Math.floor(Math.random() * 4) + 1,
	                origin: i % 2 === 0 ? 'SUR' : 'WDI',
	                destination: i % 2 === 0 ? 'WDI' : 'SUR',
	                current_km: Math.random() * 455.3,
	                speed: 40 + Math.random() * 60,
	                status: isDelayed ? 'delayed' : 'running',
	                delay_minutes: isDelayed ? Math.random() * 60 : 0
	            });
	        }
	        
	        return mockTrains;
	    }
	
	    updateMetrics() {
	        const metrics = (this.data && this.data.metrics) ? this.data.metrics : {
	            active_trains: 0,
	            average_delay_minutes: 0,
	            average_speed_kmh: 0,
	            bottleneck_utilization: 0
	        };
	        
	        const el = (id) => document.getElementById(id);
	        if (el('active-trains')) el('active-trains').textContent = metrics.active_trains;
	        if (el('avg-delay')) el('avg-delay').textContent = metrics.average_delay_minutes.toFixed(1);
	        if (el('avg-speed')) el('avg-speed').textContent = metrics.average_speed_kmh.toFixed(0);
	        if (el('bottleneck-util')) el('bottleneck-util').textContent = (metrics.bottleneck_utilization * 100).toFixed(0) + '%';
	        if (el('critical-count')) el('critical-count').textContent = `${(this.data && this.data.critical_count) || 0} Critical`;
	    }
	
	    renderDecisions() {
	        const container = document.getElementById('decisions-container');
	        const decisions = (this.data && this.data.decisions) ? this.data.decisions : {};
	        if (!container) return;
	        
	        let decisionsHTML = '';
	        
	        Object.entries(decisions).forEach(([trainNumber, decision]) => {
	            const cardClass = this.getDecisionCardClass(decision.decision);
	            
	            decisionsHTML += `
	                <div class="decision-card ${cardClass}">
	                    <div class="decision-header">
	                        <span class="train-info">Train ${trainNumber}</span>
	                        <span class="confidence-badge">${(decision.confidence * 100).toFixed(0)}%</span>
	                    </div>
	                    <div class="decision-action">${decision.decision}</div>
	                    <div class="decision-reasoning">${decision.reasoning}</div>
	                </div>
	            `;
	        });
	        
	        container.innerHTML = decisionsHTML;
	    }
	
	    getDecisionCardClass(decision) {
	        if (!decision) return 'normal';
	        if (decision.includes('Hold') || decision.includes('Stop')) return 'critical';
	        if (decision.toLowerCase().includes('priority')) return 'priority';
	        return 'normal';
	    }
	
	    renderTrains() {
	        const container = document.getElementById('trains-container');
	        const decisions = (this.data && this.data.decisions) ? this.data.decisions : {};
	        if (!container) return;
	        
	        if (!this.trainPositions || this.trainPositions.length === 0) {
	            container.innerHTML = '<p>No train data available</p>';
	            return;
	        }
	        
	        let trainsHTML = '';
	        
	        this.trainPositions.forEach(train => {
	            const decision = decisions[train.number];
	            if (!decision) return;
	            
	            trainsHTML += `
	                <div class="train-card ${train.status}">
	                    <div class="train-header">
	                        <span class="train-number">${train.number}</span>
	                        <span class="train-status ${train.status}">${train.status}</span>
	                    </div>
	                    <div class="train-details">
	                        <div class="detail-item">
	                            <div class="detail-label">Position</div>
	                            <div class="detail-value">${train.position.toFixed(1)} km</div>
	                        </div>
	                        <div class="detail-item">
	                            <div class="detail-label">Speed</div>
	                            <div class="detail-value">${train.speed.toFixed(0)} km/h</div>
	                        </div>
	                        <div class="detail-item">
	                            <div class="detail-label">Delay</div>
	                            <div class="detail-value">${train.delay.toFixed(0)} min</div>
	                        </div>
	                        <div class="detail-item">
	                            <div class="detail-label">AI Action</div>
	                            <div class="detail-value">${decision.decision}</div>
	                        </div>
	                    </div>
	                </div>
	            `;
	        });
	        
	        container.innerHTML = trainsHTML;
	    }
	
	    showLoading() {
	        const overlay = document.getElementById('loading-overlay');
	        if (overlay) overlay.classList.add('active');
	    }
	
	    hideLoading() {
	        const overlay = document.getElementById('loading-overlay');
	        if (overlay) overlay.classList.remove('active');
	    }
	
	    async refreshData() {
	        this.showLoading();
	        await this.loadData();
	        this.updateMetrics();
	        this.renderTimeDistanceGraph();
	        this.renderDecisions();
	        this.renderTrains();
	        this.hideLoading();
	        
	        // Add refresh animation
	        const refreshBtn = document.querySelector('.btn-refresh i');
	        if (refreshBtn) {
	            refreshBtn.style.animation = 'spin 1s linear';
	            setTimeout(() => {
	                refreshBtn.style.animation = '';
	            }, 1000);
	        }
	    }
	
	    filterTrains(status) {
	        const trains = document.querySelectorAll('.train-card');
	        trains.forEach(train => {
	            if (status === 'all' || train.classList.contains(status)) {
	                train.style.display = 'block';
	            } else {
	                train.style.display = 'none';
	            }
	        });
	    }
	}
	
	// expose class
	window.RailwayDashboard = RailwayDashboard;
}

// Initialize dashboard when page loads (single consolidated listener)
let dashboard = null;
document.addEventListener('DOMContentLoaded', () => {
    if (!dashboard) {
        dashboard = new window.RailwayDashboard();
    }
    
    // Global functions for HTML events
    window.refreshData = function() {
        if (dashboard) dashboard.refreshData();
    };
    
    const statusFilter = document.getElementById('status-filter');
    if (statusFilter) {
        statusFilter.addEventListener('change', (e) => {
            if (dashboard) dashboard.filterTrains(e.target.value);
        });
    }
    
    const timeRange = document.getElementById('time-range');
    if (timeRange) {
        timeRange.addEventListener('change', () => {
            if (dashboard) dashboard.renderTimeDistanceGraph();
        });
    }
});
// Filter functionality
document.addEventListener('DOMContentLoaded', () => {
    const statusFilter = document.getElementById('status-filter');
    if (statusFilter) {
        statusFilter.addEventListener('change', (e) => {
            if (dashboard) {
                dashboard.filterTrains(e.target.value);
            }
        });
    }
});

// Add event listener for time range change
document.addEventListener('DOMContentLoaded', () => {
    const timeRange = document.getElementById('time-range');
    if (timeRange) {
        timeRange.addEventListener('change', () => {
            if (dashboard) {
                dashboard.renderTimeDistanceGraph();
            }
        });
    }
});
