import random
from datetime import datetime, timedelta
from typing import List, Tuple
from data_models import *
from collections import defaultdict

class SolapurWadiDataGenerator:
    def __init__(self):
        self.section = self._create_section_info()
        self.current_time = datetime.now()
        self.train_types = [
            (TrainType.PASSENGER, Priority.LOW, 50, 8), (TrainType.EXPRESS, Priority.MEDIUM, 80, 4),
            (TrainType.SUPERFAST, Priority.HIGH, 100, 2), (TrainType.FREIGHT, Priority.LOW, 60, 0),
        ]

    def _create_section_info(self) -> SectionInfo:
        stations_data = [("SUR", "Solapur", 0.0, 4), ("HOTGI", "Hotgi", 25.3, 2), ("INDI", "Indi", 45.8, 2), ("BIJAPUR", "Bijapur", 78.2, 3), ("ALMATTI", "Almatti", 95.5, 1), ("BAGALKOT", "Bagalkot", 125.7, 2), ("BADAMI", "Badami", 142.3, 2), ("GADAG", "Gadag", 168.9, 3), ("WDI", "Wadi", 455.3, 3)]
        stations = [Station(code, name, km, p) for code, name, km, p in stations_data]
        single_line_segments = [(25.3, 45.8), (142.3, 168.9)]
        return SectionInfo("Solapur-Wadi", "SUR", "WDI", 455.3, 110.0, stations, single_line_segments)

    def generate_scenario(self, scenario_type: ScenarioType, num_trains: int = 25) -> Tuple[List[TrainSchedule], List[TrainPosition]]:
        print(f"🔥 Generating SCENARIO: {scenario_type.value.upper()}")
        if scenario_type == ScenarioType.MAJOR_DISRUPTION:
            return self._generate_disruption_scenario(num_trains)
        elif scenario_type == ScenarioType.BOTTLENECK_CONFLICT:
            return self._generate_bottleneck_conflict_scenario(num_trains)
        elif scenario_type == ScenarioType.HIGH_DENSITY:
            return self._generate_high_density_scenario(num_trains)

    def _generate_base_schedule(self, i, origin, destination, departure_time):
        train_type, priority, avg_speed, _ = random.choice(self.train_types)
        train_number = f"F{50000 + i}" if train_type == TrainType.FREIGHT else f"{13000 + i}"
        travel_time_hours = self.section.total_distance / avg_speed * random.uniform(0.9, 1.2)
        arrival_time = departure_time + timedelta(hours=travel_time_hours)
        return TrainSchedule(train_number, f"{train_type.value.title()} {train_number}", train_type, priority, origin, destination, departure_time, arrival_time, [])

    def _generate_disruption_scenario(self, num_trains):
        schedules = []
        disrupted_train_dep_time = self.current_time - timedelta(hours=random.uniform(1.5, 2.5))
        disrupted_train = self._generate_base_schedule(99, "SUR", "WDI", disrupted_train_dep_time)
        disrupted_train.priority = Priority.HIGH
        schedules.append(disrupted_train)
        for i in range(num_trains - 1):
            departure_offset = timedelta(hours=random.uniform(-3, 1))
            schedules.append(self._generate_base_schedule(i, *random.choice([("SUR", "WDI"), ("WDI", "SUR")]), self.current_time + departure_offset))
        positions = self._create_positions(schedules, disrupted_train_number=disrupted_train.train_number)
        return schedules, positions

    def _generate_bottleneck_conflict_scenario(self, num_trains):
        schedules = []
        bottleneck = random.choice(self.section.single_line_segments)
        conflict_time = self.current_time + timedelta(minutes=random.uniform(20, 45))
        bottleneck_mid_km = (bottleneck[0] + bottleneck[1]) / 2
        _, _, speed1, _ = random.choice(self.train_types)
        dep_time1 = conflict_time - timedelta(hours=bottleneck_mid_km / speed1)
        schedules.append(self._generate_base_schedule(99, "SUR", "WDI", dep_time1))
        _, _, speed2, _ = random.choice(self.train_types)
        dep_time2 = conflict_time - timedelta(hours=(self.section.total_distance - bottleneck_mid_km) / speed2)
        schedules.append(self._generate_base_schedule(98, "WDI", "SUR", dep_time2))
        for i in range(num_trains - 2):
            departure_offset = timedelta(hours=random.uniform(-3, 1))
            schedules.append(self._generate_base_schedule(i, *random.choice([("SUR", "WDI"), ("WDI", "SUR")]), self.current_time + departure_offset))
        positions = self._create_positions(schedules)
        return schedules, positions

    def _generate_high_density_scenario(self, num_trains):
        schedules = []
        for i in range(num_trains):
            departure_offset = timedelta(minutes=random.uniform(-120, 30))
            schedules.append(self._generate_base_schedule(i, *random.choice([("SUR", "WDI"), ("WDI", "SUR")]), self.current_time + departure_offset))
        positions = self._create_positions(schedules)
        return schedules, positions
    
    def _create_positions(self, schedules, disrupted_train_number=None):
        positions = []
        
        for schedule in schedules:
            if self.current_time < schedule.scheduled_departure:
                positions.append(TrainPosition(schedule.train_number, schedule.origin, 0, 0, TrainStatus.SCHEDULED, 0, self.current_time, schedule.origin))
                continue
            if self.current_time > schedule.scheduled_arrival + timedelta(hours=1):
                continue

            journey_duration_hrs = (schedule.scheduled_arrival - schedule.scheduled_departure).total_seconds() / 3600
            time_elapsed_hrs = (self.current_time - schedule.scheduled_departure).total_seconds() / 3600
            ideal_progress = min(1.0, time_elapsed_hrs / journey_duration_hrs) if journey_duration_hrs > 0 else 0

            delay = int(random.uniform(5, 30) * ideal_progress)
            progress = max(0, ideal_progress - (delay / (journey_duration_hrs * 60)) * 0.5) if journey_duration_hrs > 0 else 0
            
            current_km = progress * self.section.total_distance if schedule.origin == "SUR" else self.section.total_distance * (1 - progress)
            speed = (self.section.total_distance / journey_duration_hrs) * random.uniform(0.6, 1.1) if journey_duration_hrs > 0 else 0
            status = TrainStatus.DELAYED if delay > 25 else TrainStatus.RUNNING
            
            if disrupted_train_number and schedule.train_number == disrupted_train_number:
                current_km = random.uniform(100, 300)
                speed, status, delay = 0, TrainStatus.STOPPED, delay + 60

            current_station = next((s.code for s in self.section.stations if abs(s.km_from_start - current_km) < 1), None)
            if speed < 5: status = TrainStatus.STOPPED
            if status == TrainStatus.STOPPED: speed = 0

            # --- FIX IS HERE: Using keyword arguments to ensure correct assignment ---
            positions.append(TrainPosition(
                train_number=schedule.train_number,
                current_station=current_station,
                current_km=round(current_km, 2),
                speed=round(speed, 2),
                status=status,
                delay_minutes=delay,
                last_updated=self.current_time,
                origin=schedule.origin
            ))
        
        pos_dict = {p.train_number: p for p in positions}
        schedules_by_origin = defaultdict(list)
        for s in schedules: schedules_by_origin[s.origin].append(s)

        for origin in schedules_by_origin:
            sorted_schedules = sorted(schedules_by_origin[origin], key=lambda s: s.scheduled_departure)
            for i in range(1, len(sorted_schedules)):
                prev_s, curr_s = sorted_schedules[i-1], sorted_schedules[i]
                
                if prev_s.train_number in pos_dict and curr_s.train_number in pos_dict:
                    prev_p = pos_dict[prev_s.train_number]
                    curr_p = pos_dict[curr_s.train_number]

                    if prev_p.delay_minutes > 20 and curr_p.status != TrainStatus.SCHEDULED:
                        knock_on_delay = (prev_p.delay_minutes - 15) * random.uniform(0.2, 0.5)
                        new_delay = curr_p.delay_minutes + knock_on_delay
                        curr_p.delay_minutes = int(min(90, new_delay))
                        if curr_p.delay_minutes > 25: curr_p.status = TrainStatus.DELAYED

        station_occupancy = defaultdict(int)
        station_map = {s.code: s for s in self.section.stations}
        positions.sort(key=lambda p: abs(p.current_km - (self.section.total_distance if p.origin == "SUR" else 0)), reverse=True)
        for p in positions:
            if p.current_station and p.status in [TrainStatus.RUNNING, TrainStatus.DELAYED]:
                station_code = p.current_station
                platforms = station_map[station_code].platforms
                if station_occupancy[station_code] >= platforms:
                    p.status = TrainStatus.STOPPED
                    p.speed = 0
                    p.delay_minutes += 5
                    p.current_km -= (1 * (1 if p.origin == "SUR" else -1))
                    p.current_station = None
                else:
                    station_occupancy[station_code] += 1
        
        return positions