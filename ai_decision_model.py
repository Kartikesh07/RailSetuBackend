import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import random
import joblib
import re # Import the regular expressions library

from data_models import *

class RailwayDecisionAI:
    def __init__(self, section_info: SectionInfo):
        self.section = section_info
        self.model = RandomForestClassifier(n_estimators=150, random_state=42, n_jobs=-1, class_weight='balanced')
        self.is_trained = False
        self.feature_columns = [
            'train_priority', 'train_type_encoded', 'current_speed', 'delay_minutes',
            'distance_to_destination', 'trains_ahead', 'single_line_conflict',
            'platform_availability', 'time_of_day', 'train_frequency',
            'time_to_next_bottleneck', 'downstream_congestion', 'conflicting_train_eta'
        ]
        self.decision_map = {
            0: "Proceed normally", 1: "Reduce speed", 2: "Stop at next station",
            3: "Give priority", 4: "Hold/Reroute"
        }

    def predict_optimal_decisions(self, schedules: List[TrainSchedule], positions: List[TrainPosition]) -> Dict[str, Dict]:
        if not self.is_trained: raise RuntimeError("Model is not trained. Please train or load a model first.")
        features_df = self.extract_features(schedules, positions)
        if features_df.empty: return {}
        
        X = features_df[self.feature_columns].values
        
        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X)
        
        # --- STEP 1: Generate initial results from the model ---
        initial_results = {}
        for i, train_number in enumerate(features_df['train_number']):
            pred = predictions[i]
            initial_results[train_number] = {
                'decision': self.decision_map[pred],
                'confidence': float(max(probabilities[i])),
                'reasoning': self._generate_reasoning(features_df.iloc[i], pred, features_df)
            }
            
        # --- STEP 2: NEW - Post-processing for decision consistency ---
        final_results = initial_results.copy()
        overrides = {} # To store which trains need their decisions overridden

        for train_number, result in initial_results.items():
            # Use regex to find "Action: Train [NUMBER] should be held..."
            match = re.search(r"Action: Train (\S+) should be held", result['reasoning'])
            if match:
                train_to_hold = match.group(1)
                # If the targeted train exists in our results, schedule an override
                if train_to_hold in final_results:
                    overrides[train_to_hold] = {
                        'decision': self.decision_map[4], # "Hold/Reroute"
                        'reasoning': f"Holding at station to allow high-priority train {train_number} to overtake as per AI coordination.",
                        'confidence': 0.99 # Override with high confidence
                    }
        
        # Apply the overrides to the final results
        for train_number, override_data in overrides.items():
            final_results[train_number] = override_data
            
        return final_results

    def extract_features(self, schedules: List[TrainSchedule], positions: List[TrainPosition]) -> pd.DataFrame:
        # ... (no changes in this method, keeping it for completeness)
        features, pos_dict, schedule_dict = [], {p.train_number: p for p in positions}, {s.train_number: s for s in schedules}
        for position in positions:
            if position.train_number not in schedule_dict or position.status in [TrainStatus.COMPLETED, TrainStatus.SCHEDULED]: continue
            schedule = schedule_dict[position.train_number]
            features.append({
                # MODEL FEATURES
                'train_number': schedule.train_number, 'train_priority': schedule.priority.value,
                'train_type_encoded': self._encode_train_type(schedule.train_type), 'current_speed': position.speed,
                'delay_minutes': position.delay_minutes, 'distance_to_destination': self._calculate_remaining_distance(schedule, position),
                'trains_ahead': self._count_trains_ahead(schedule, position, positions), 'single_line_conflict': self._check_single_line_conflict(position),
                'platform_availability': self._check_platform_availability(position), 'time_of_day': datetime.now().hour,
                'train_frequency': self._calculate_train_frequency(schedules, datetime.now()),
                'time_to_next_bottleneck': self._calculate_time_to_next_bottleneck(schedule, position),
                'downstream_congestion': self._calculate_downstream_congestion(schedule, position, positions),
                'conflicting_train_eta': self._find_conflicting_train_eta(schedule, position, positions, schedules),
                # CONTEXTUAL FEATURES (for reasoning, not for model)
                'origin': schedule.origin,
                'current_km': position.current_km
            })
        return pd.DataFrame(features)

    # ... (train_model, _get_priority_weight, simulations, save/load remain unchanged)

    def train_model(self, X_train, y_train):
        print(f"Training AI model on {len(X_train)} curated samples...")
        self.model.fit(X_train, y_train)
        self.is_trained = True
        print("Model training completed!")

    def _get_priority_weight(self, priority: Priority) -> float:
        if priority == Priority.CRITICAL: return 4.0
        if priority == Priority.HIGH: return 2.5
        if priority == Priority.MEDIUM: return 1.5
        return 1.0

    def _generate_optimal_decision_by_simulation(self, feature_row: pd.Series, schedules, positions) -> int:
        if feature_row['train_priority'] >= 3 and feature_row['delay_minutes'] < 10: return 3
        outcomes = {}
        for decision in [d for d in self.decision_map.keys() if d != 3]:
            train_schedule = next(s for s in schedules if s.train_number == feature_row['train_number'])
            outcomes[decision] = self._simulate_future_delays(schedules, positions, train_schedule, decision)
        return min(outcomes, key=outcomes.get)

    def _simulate_future_delays(self, schedules, positions, train_to_modify, decision) -> float:
        sim_duration_min, time_step_min, headway_km = 30, 5, 6.0
        sim_positions = {p.train_number: TrainPosition(**p.__dict__) for p in positions}
        schedule_dict = {s.train_number: s for s in schedules}
        target_pos = sim_positions[train_to_modify.train_number]
        if decision == 1: target_pos.speed *= 0.6
        elif decision == 2 or decision == 4: target_pos.speed = 0
        total_weighted_delay = 0
        for _ in range(0, sim_duration_min, time_step_min):
            sorted_pos = sorted(list(sim_positions.values()), key=lambda p: p.current_km)
            for i, pos in enumerate(sorted_pos):
                schedule = schedule_dict[pos.train_number]
                direction = 1 if schedule.origin == "SUR" else -1
                current_speed = pos.speed
                if i > 0:
                    prev_pos = sorted_pos[i - 1]
                    if schedule.origin == schedule_dict[prev_pos.train_number].origin and abs(pos.current_km - prev_pos.current_km) < headway_km:
                        current_speed = min(current_speed, prev_pos.speed * 0.8, 20)
                pos.current_km += current_speed * (time_step_min / 60.0)
                delay_increase = (1 - (current_speed / 80)) * (time_step_min / 5) if current_speed < 80 else 0
                pos.delay_minutes += delay_increase
                total_weighted_delay += delay_increase * self._get_priority_weight(schedule.priority)
        return total_weighted_delay

    def save_model(self, path: str = "railway_ai_model.joblib"):
        if not self.is_trained: raise RuntimeError("Cannot save an untrained model.")
        joblib.dump(self.model, path)
        print(f"Model saved to {path}")

    def load_model(self, path: str = "railway_ai_model.joblib"):
        try:
            self.model, self.is_trained = joblib.load(path), True
            print(f"Model loaded from {path}")
        except FileNotFoundError:
            self.is_trained = False
            print(f"Warning: Model file not found at {path}.")
            
    def _generate_reasoning(self, fr: pd.Series, d: int, all_features_df: pd.DataFrame) -> str:
        # ... (This reasoning function remains the same as the previous version)
        def _get_direction(origin_code: str) -> int:
            return 1 if origin_code == "SUR" else -1
        my_direction = _get_direction(fr['origin'])
        my_km = fr['current_km']
        if d == 0: return f"Path clear with low downstream congestion ({fr['downstream_congestion']:.1f}). Proceeding to maintain schedule."
        if d == 1:
            trains_ahead_df = all_features_df[(all_features_df['train_number'] != fr['train_number']) & (all_features_df['origin'] == fr['origin']) & (((all_features_df['current_km'] - my_km) * my_direction) > 0) & (((all_features_df['current_km'] - my_km) * my_direction) < 25)].copy()
            if not trains_ahead_df.empty:
                trains_ahead_df['distance'] = abs(trains_ahead_df['current_km'] - my_km)
                closest_train = trains_ahead_df.loc[trains_ahead_df['distance'].idxmin()]
                return f"Reduce speed: Approaching slower train {closest_train['train_number']} which is {closest_train['distance']:.1f}km ahead."
            return f"Reduce speed due to high downstream congestion ({fr['downstream_congestion']:.1f}) requiring caution."
        if d == 2:
            if fr['conflicting_train_eta'] < 60:
                opposing_trains_df = all_features_df[all_features_df['origin'] != fr['origin']].copy()
                if not opposing_trains_df.empty:
                    opposing_trains_df['eta_diff'] = abs(opposing_trains_df['conflicting_train_eta'] - fr['conflicting_train_eta'])
                    conflict_train = opposing_trains_df.loc[opposing_trains_df['eta_diff'].idxmin()]
                    return f"CRITICAL: Stop at next station to resolve head-on conflict with train {conflict_train['train_number']} at an upcoming single-line section."
            return f"Stop at next station to regulate flow before bottleneck (in {fr['time_to_next_bottleneck']:.0f} min) which has high traffic."
        if d == 3:
            trains_to_overtake_df = all_features_df[(all_features_df['train_number'] != fr['train_number']) & (all_features_df['origin'] == fr['origin']) & (all_features_df['train_priority'] < fr['train_priority']) & (((all_features_df['current_km'] - my_km) * my_direction) > 0) & (((all_features_df['current_km'] - my_km) * my_direction) < 40)].copy()
            if not trains_to_overtake_df.empty:
                trains_to_overtake_df['distance'] = abs(trains_to_overtake_df['current_km'] - my_km)
                train_to_hold = trains_to_overtake_df.loc[trains_to_overtake_df['distance'].idxmin()]
                return (f"Give Priority: High-priority train on schedule. Action: Train {train_to_hold['train_number']} should be held at its next stop to allow for an overtake.")
            return f"Give Priority: High-priority train (Level {fr['train_priority']:.0f}) proceeding on a clear path."
        if d == 4: return f"Hold/Reroute: Heavy delay ({fr['delay_minutes']:.0f} min) and high section traffic. Holding to stabilize network and prevent cascading delays."
        return "Decision based on optimizing overall section throughput."

    # ... (other helper functions remain unchanged)
    def _calculate_time_to_next_bottleneck(self, s, p):
        if p.speed == 0: return 999.0
        dist, d = float('inf'), 1 if s.origin == "SUR" else -1
        for sk, ek in self.section.single_line_segments:
            ep = sk if d == 1 else ek
            de = (ep - p.current_km) * d
            if 0 < de < dist: dist = de
        return 999.0 if dist == float('inf') else (dist / p.speed) * 60
    def _calculate_downstream_congestion(self, s, p, ap, lk=50):
        c,d=0,1 if s.origin=="SUR" else -1
        for op in ap:
            if op.train_number==p.train_number:continue
            if 0<(op.current_km-p.current_km)*d<=lk: c+=1
        return c/(lk/10.0)
    def _find_conflicting_train_eta(self, s, p, ap, asc):
        d, sd = 1 if s.origin == "SUR" else -1, {sc.train_number: sc for sc in asc}
        for sk, ek in self.section.single_line_segments:
            mde = ((sk if d == 1 else ek) - p.current_km) * d
            if mde < 0: continue
            me = (mde/p.speed)*60 if p.speed>0 else 999.0
            if me > 60: continue
            for op in ap:
                os=sd.get(op.train_number)
                if not os or os.origin==s.origin: continue
                od=-1*d
                ode=((sk if od==1 else ek)-op.current_km)*od
                if ode>0:
                    oe=(ode/op.speed)*60 if op.speed>0 else 999.0
                    if abs(me-oe)<10: return oe
        return 999.0
    def _count_trains_ahead(self, s, p, ap): return sum(1 for op in ap if op.train_number!=p.train_number and (op.current_km-p.current_km)*(1 if s.origin=="SUR" else -1)>0)
    def _encode_train_type(self, tt): return {TrainType.FREIGHT: 1, TrainType.PASSENGER: 2, TrainType.EXPRESS: 3, TrainType.SUPERFAST: 4}[tt]
    def _calculate_remaining_distance(self, s, p): return self.section.total_distance-p.current_km if s.origin=="SUR" else p.current_km
    def _check_single_line_conflict(self, p): return 1 if any(s<=p.current_km<=e for s,e in self.section.single_line_segments) else 0
    def _check_platform_availability(self, p):
        if p.current_station:
            st = next((s for s in self.section.stations if s.code == p.current_station), None)
            if st: return st.platforms/6.0
        return 0.5
    def _calculate_train_frequency(self, s, t): return sum(1 for sc in s if 0<=(sc.scheduled_departure-t).total_seconds()/3600<=2)
    def calculate_throughput_metrics(self, s, p):
        at=[pos for pos in p if pos.status in [TrainStatus.RUNNING, TrainStatus.DELAYED, TrainStatus.STOPPED]]
        if not at: return {'active_trains': 0, 'average_delay_minutes': 0, 'average_speed_kmh': 0, 'bottleneck_utilization': 0, 'total_scheduled_trains': len(s)}
        return {'active_trains':len(at), 'average_delay_minutes':round(np.mean([t.delay_minutes for t in at]),2), 'average_speed_kmh':round(np.mean([t.speed for t in at if t.speed>0]) if any(t.speed>0 for t in at) else 0,2), 'bottleneck_utilization':round(sum(1 for t in at if self._check_single_line_conflict(t))/len(self.section.single_line_segments) if self.section.single_line_segments else 0,2), 'total_scheduled_trains':len(s)}