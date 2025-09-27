from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import random # ENHANCEMENT: Import random to pick scenarios

# ENHANCEMENT: Import AI classes and the new ScenarioType
from ai_decision_model import RailwayDecisionAI
from mock_data_generator import SolapurWadiDataGenerator
from data_models import ScenarioType

app = Flask(__name__)
CORS(app)

# --- Initialize and load the AI model ONCE at startup ---
print("Initializing AI Decision Support System...")
data_generator = SolapurWadiDataGenerator()
ai_model = RailwayDecisionAI(data_generator.section)
ai_model.load_model("railway_ai_model.joblib")
print("System Ready. Waiting for requests...")
# --------------------------------------------------------------------

@app.route('/api/live_report')
def get_live_report():
    """
    New dynamic endpoint that generates a fresh, PROBLEMATIC scenario
    and gets a live prediction from the AI model on every request.
    """
    if not ai_model.is_trained:
        return jsonify(get_mock_data()), 503

    print(f"[{datetime.now()}] Generating new live report...")

    # --- FIX: Use the new problem-centric scenario generator ---
    # 1. Randomly pick a difficult scenario type to keep the demo interesting.
    scenario_to_generate = random.choice(list(ScenarioType))
    
    # 2. Call the single method that returns both schedules and positions.
    schedules, positions = data_generator.generate_scenario(scenario_to_generate)
    # -------------------------------------------------------------

    # 3. Get fresh AI decisions and metrics for the generated problem
    decisions = ai_model.predict_optimal_decisions(schedules, positions)
    metrics = ai_model.calculate_throughput_metrics(schedules, positions)
    
    critical_decisions = {k: v for k, v in decisions.items() if v['decision'] != 'Proceed normally'}

    # 4. Format data for the frontend
    report = {
        'timestamp': datetime.now().isoformat(),
        'section': ai_model.section.section_name,
        'metrics': metrics,
        'decisions': decisions,
        'critical_count': len(critical_decisions),
        'trains': format_train_data(schedules, positions),
        'stations': [
            {'code': s.code, 'name': s.name, 'km': s.km_from_start}
            for s in data_generator.section.stations
        ]
    }
    
    return jsonify(report)

def format_train_data(schedules, positions):
    """Helper to format train data for JSON response."""
    pos_dict = {pos.train_number: pos for pos in positions}
    schedule_data = []
    for schedule in schedules:
        pos = pos_dict.get(schedule.train_number)
        if pos:
            schedule_data.append({
                'train_number': schedule.train_number,
                'train_name': schedule.train_name,
                'train_type': schedule.train_type.value,
                'priority': schedule.priority.value,
                'origin': schedule.origin,
                'destination': schedule.destination,
                'scheduled_departure': schedule.scheduled_departure.isoformat(),
                'scheduled_arrival': schedule.scheduled_arrival.isoformat(),
                'current_km': pos.current_km,
                'current_station': pos.current_station,
                'speed': pos.speed,
                'status': pos.status.value,
                'delay_minutes': pos.delay_minutes,
                'stops': [
                    {
                        'station_code': stop['station_code'],
                        'arrival_time': stop['arrival_time'].isoformat(),
                        'departure_time': stop['departure_time'].isoformat()
                    } for stop in schedule.stops
                ]
            })
    return schedule_data

def get_mock_data():
    """Provides fallback data if the model isn't trained."""
    return { "timestamp": datetime.now().isoformat(), "section": "Solapur-Wadi (Model Not Trained)", "metrics": { "active_trains": 0, "average_delay_minutes": 0, "average_speed_kmh": 0, "bottleneck_utilization": 0, "total_scheduled_trains": 0 }, "decisions": {}, "critical_count": 0, "trains": [], "stations": [] }

if __name__ == '__main__':
    app.run(debug=False) 