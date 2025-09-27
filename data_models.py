from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import enum

# ENHANCEMENT: Add an enum for our problem-centric scenarios
class ScenarioType(enum.Enum):
    MAJOR_DISRUPTION = "major_disruption"
    BOTTLENECK_CONFLICT = "bottleneck_conflict"
    HIGH_DENSITY = "high_density"

class TrainStatus(enum.Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    DELAYED = "delayed"
    STOPPED = "stopped"
    COMPLETED = "completed"

class TrainType(enum.Enum):
    PASSENGER = "passenger"
    EXPRESS = "express"
    FREIGHT = "freight"
    SUPERFAST = "superfast"

class Priority(enum.Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Station:
    code: str
    name: str
    km_from_start: float
    platforms: int

@dataclass
class TrainSchedule:
    train_number: str
    train_name: str
    train_type: TrainType
    priority: Priority
    origin: str
    destination: str
    scheduled_departure: datetime
    scheduled_arrival: datetime
    stops: List[Dict[str, any]]

@dataclass
class TrainPosition:
    train_number: str
    current_station: Optional[str]
    current_km: float
    speed: float
    status: TrainStatus
    delay_minutes: int
    last_updated: datetime
    # ENHANCEMENT: Add origin for easier cascading delay logic
    origin: str = "SUR"

@dataclass
class SectionInfo:
    section_name: str
    start_station: str
    end_station: str
    total_distance: float
    max_speed: float
    stations: List[Station]
    single_line_segments: List[tuple]