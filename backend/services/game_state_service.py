"""Game state management for web gameplay - Full multiplayer implementation."""
import random
import uuid
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from ..models.game_state import (
    GameStateResponse, GamePhase, TireCompound, SponsorTier, MessagePriority, MessageType,
    ContractStatus, DriverStats, ContractDemand, DriverContract, DriverInfo, MarketDriver,
    CarStats, UpgradeOption, DevelopmentNode, DevelopmentTree, SponsorObjective, SponsorInfo,
    TeamInfo, InboxMessage, TrackInfo, QualifyingResult, RaceEntry, RaceEvent, RaceState,
    RaceResult, SeasonCalendarEntry, DriverStanding, ConstructorStanding, PlayerState, TurnInfo,
    PitDecisionStatus
)

# Add src/data to path to import driver/track data
SRC_DATA_PATH = Path(__file__).parent.parent.parent / "src" / "data"
SRC_PATH = Path(__file__).parent.parent.parent / "src"

if str(SRC_DATA_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_DATA_PATH))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Load driver data
F1_DRIVERS = []
F2_DRIVERS = []
TRACKS = []

try:
    from drivers_f1 import F1_DRIVERS as _F1_DRIVERS
    from drivers_f2 import F2_DRIVERS as _F2_DRIVERS
    from tracks import TRACKS as _TRACKS
    F1_DRIVERS = _F1_DRIVERS
    F2_DRIVERS = _F2_DRIVERS
    TRACKS = _TRACKS
    print(f"Loaded {len(F1_DRIVERS)} F1 drivers, {len(F2_DRIVERS)} F2 drivers, {len(TRACKS)} tracks")
except ImportError as e:
    print(f"Warning: Could not import data: {e}")
    # Minimal fallback data - see full fallback in original file if needed

# ==================== CONSTANTS ====================

POINTS_SYSTEM = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}

RACE_PRIZE_MONEY = {
    1: 3.75, 2: 2.75, 3: 2.25, 4: 1.85, 5: 1.5, 6: 1.2, 7: 1.0, 8: 0.85, 9: 0.7, 10: 0.6
}

SEASON_PRIZE_MONEY = {
    1: 80, 2: 70, 3: 62, 4: 55, 5: 48, 6: 42, 7: 38, 8: 35, 9: 32, 10: 30, 11: 28
}

# Upgrade costs per stat level
UPGRADE_COSTS = {
    (50, 54): 2, (55, 59): 3, (60, 64): 5, (65, 69): 7, (70, 74): 10,
    (75, 79): 14, (80, 84): 18, (85, 89): 24, (90, 94): 32, (95, 99): 45
}

# AI Team car ratings
AI_TEAM_CARS = {
    "Red Bull Racing": {"downforce": 90, "aero_efficiency": 92, "chassis": 88, "power_unit": 90, "reliability": 85, "tire_cooling": 88},
    "Mercedes": {"downforce": 85, "aero_efficiency": 88, "chassis": 86, "power_unit": 88, "reliability": 90, "tire_cooling": 85},
    "Ferrari": {"downforce": 88, "aero_efficiency": 85, "chassis": 85, "power_unit": 86, "reliability": 80, "tire_cooling": 82},
    "McLaren": {"downforce": 86, "aero_efficiency": 87, "chassis": 88, "power_unit": 84, "reliability": 85, "tire_cooling": 86},
    "Aston Martin": {"downforce": 80, "aero_efficiency": 78, "chassis": 79, "power_unit": 82, "reliability": 82, "tire_cooling": 78},
    "Alpine": {"downforce": 76, "aero_efficiency": 74, "chassis": 75, "power_unit": 78, "reliability": 78, "tire_cooling": 74},
    "Williams": {"downforce": 72, "aero_efficiency": 73, "chassis": 71, "power_unit": 75, "reliability": 80, "tire_cooling": 72},
    "Sauber": {"downforce": 70, "aero_efficiency": 71, "chassis": 72, "power_unit": 73, "reliability": 76, "tire_cooling": 70},
    "Haas": {"downforce": 68, "aero_efficiency": 69, "chassis": 70, "power_unit": 72, "reliability": 74, "tire_cooling": 68},
    "RB": {"downforce": 74, "aero_efficiency": 75, "chassis": 74, "power_unit": 76, "reliability": 77, "tire_cooling": 75},
}

# Sponsor definitions
SPONSORS = {
    "bronze": [
        {"name": "LocalParts Inc", "payment": 0.3, "bonus": 3, "objective_type": "finish_position", "target": 20},
        {"name": "RegionalFuel Co", "payment": 0.4, "bonus": 4, "objective_type": "finish_position", "target": 18},
        {"name": "StartupTech", "payment": 0.5, "bonus": 5, "objective_type": "finish_position", "target": 16},
    ],
    "silver": [
        {"name": "MidRange Motors", "payment": 0.7, "bonus": 7, "objective_type": "finish_position", "target": 15},
        {"name": "National Bank", "payment": 0.8, "bonus": 8, "objective_type": "finish_position", "target": 12},
        {"name": "TechCorp", "payment": 0.9, "bonus": 10, "objective_type": "points_finish", "target": 10},
    ],
    "gold": [
        {"name": "GlobalEnergy", "payment": 1.2, "bonus": 14, "objective_type": "finish_position", "target": 8},
        {"name": "LuxuryWatches", "payment": 1.4, "bonus": 16, "objective_type": "finish_position", "target": 6},
        {"name": "PremiumAuto", "payment": 1.5, "bonus": 18, "objective_type": "podium", "target": 3},
    ],
    "platinum": [
        {"name": "MegaCorp International", "payment": 2.2, "bonus": 28, "objective_type": "podium", "target": 3},
        {"name": "Elite Brands", "payment": 2.6, "bonus": 32, "objective_type": "win", "target": 1},
        {"name": "WorldWide Tech", "payment": 3.0, "bonus": 40, "objective_type": "finish_position", "target": 5},
    ],
}


class Weather(Enum):
    DRY = "dry"
    LIGHT_RAIN = "light_rain"
    HEAVY_RAIN = "heavy_rain"


class TireState:
    """Tire state with CLI performance curves."""
    BASE_PERFORMANCE = {"soft": 1.0, "medium": 0.75, "hard": 0.55, "intermediate": 0.65, "wet": 0.55}
    DEGRADATION_RATES = {"soft": 3.0, "medium": 1.8, "hard": 1.0, "intermediate": 1.4, "wet": 1.2}

    def __init__(self, compound: str):
        self.compound = compound
        self.wear = 0.0

    @property
    def performance(self) -> float:
        base = self.BASE_PERFORMANCE.get(self.compound, 0.75)
        if self.wear <= 30:
            penalty = (self.wear / 100) * 0.15
        elif self.wear <= 60:
            penalty = 0.045 + ((self.wear - 30) / 100) * 0.4
        elif self.wear <= 80:
            penalty = 0.165 + ((self.wear - 60) / 100) * 0.6
        else:
            penalty = 0.285 + ((self.wear - 80) / 100) * 1.2
        return max(0.05, base - penalty)


def calc_overall(stats: Dict) -> int:
    return round(stats["pace"] * 0.25 + stats["overtaking"] * 0.15 + stats["defending"] * 0.15 +
                 stats["consistency"] * 0.20 + stats["tire_management"] * 0.15 + stats["wet_skill"] * 0.10)


def calc_car_overall(car: Dict) -> int:
    return round(car["downforce"] * 0.18 + car["aero_efficiency"] * 0.18 + car["chassis"] * 0.22 +
                 car["power_unit"] * 0.18 + car["reliability"] * 0.12 + car["tire_cooling"] * 0.12)


def get_upgrade_cost(current_value: int) -> float:
    for (low, high), cost in UPGRADE_COSTS.items():
        if low <= current_value <= high:
            return cost
    return 45  # Max cost for 95+


def calc_potential(age: int, overall: int) -> int:
    if age < 23:
        return min(99, overall + random.randint(8, 15))
    elif age <= 26:
        return min(99, overall + random.randint(4, 10))
    elif age <= 30:
        return min(99, overall + random.randint(1, 5))
    return min(99, overall + random.randint(0, 2))


# ==================== DEVELOPMENT TREE ====================

def create_development_tree() -> List[Dict]:
    """Create the full development tree structure."""
    return [
        # AERODYNAMICS - Base
        {"id": "aero_base", "name": "Aerodynamic Package", "description": "Foundation for aero development",
         "category": "aerodynamics", "branch": "base", "cost": 8, "development_time": 2,
         "effects": {"downforce": 2, "aero_efficiency": 2}, "prerequisites": []},
        # High Downforce Branch
        {"id": "aero_hd_1", "name": "Enhanced Front Wing", "description": "More front-end grip",
         "category": "aerodynamics", "branch": "high_downforce", "cost": 10, "development_time": 3,
         "effects": {"downforce": 4, "aero_efficiency": -1}, "prerequisites": ["aero_base"]},
        {"id": "aero_hd_2", "name": "Aggressive Rear Wing", "description": "Maximum rear grip",
         "category": "aerodynamics", "branch": "high_downforce", "cost": 14, "development_time": 4,
         "effects": {"downforce": 5, "aero_efficiency": -2}, "prerequisites": ["aero_hd_1"]},
        {"id": "aero_hd_3", "name": "Maximum Downforce Package", "description": "Ultimate cornering setup",
         "category": "aerodynamics", "branch": "high_downforce", "cost": 20, "development_time": 5,
         "effects": {"downforce": 6, "chassis": 2, "aero_efficiency": -3}, "prerequisites": ["aero_hd_2"]},
        # Low Drag Branch
        {"id": "aero_ld_1", "name": "Slippery Bodywork", "description": "Reduced drag coefficient",
         "category": "aerodynamics", "branch": "low_drag", "cost": 10, "development_time": 3,
         "effects": {"aero_efficiency": 4, "downforce": -1}, "prerequisites": ["aero_base"]},
        {"id": "aero_ld_2", "name": "DRS Optimization", "description": "More effective DRS zone",
         "category": "aerodynamics", "branch": "low_drag", "cost": 14, "development_time": 4,
         "effects": {"aero_efficiency": 5, "downforce": -2}, "prerequisites": ["aero_ld_1"]},
        {"id": "aero_ld_3", "name": "Monza Special", "description": "Ultimate top speed setup",
         "category": "aerodynamics", "branch": "low_drag", "cost": 20, "development_time": 5,
         "effects": {"aero_efficiency": 6, "power_unit": 2, "downforce": -3}, "prerequisites": ["aero_ld_2"]},
        # Balanced Aero
        {"id": "aero_bal_1", "name": "Versatile Aero Package", "description": "Good all-round aero",
         "category": "aerodynamics", "branch": "balanced", "cost": 12, "development_time": 3,
         "effects": {"downforce": 2, "aero_efficiency": 2}, "prerequisites": ["aero_base"]},
        {"id": "aero_bal_2", "name": "Adaptive Wing Elements", "description": "Track-adaptable wings",
         "category": "aerodynamics", "branch": "balanced", "cost": 16, "development_time": 4,
         "effects": {"downforce": 3, "aero_efficiency": 3}, "prerequisites": ["aero_bal_1"]},

        # POWER UNIT - Base
        {"id": "pu_base", "name": "Power Unit Optimization", "description": "Foundation for PU development",
         "category": "power_unit", "branch": "base", "cost": 10, "development_time": 2,
         "effects": {"power_unit": 2, "reliability": 1}, "prerequisites": []},
        # Raw Power
        {"id": "pu_power_1", "name": "Aggressive Engine Mapping", "description": "More power, less reliability",
         "category": "power_unit", "branch": "raw_power", "cost": 12, "development_time": 3,
         "effects": {"power_unit": 5, "reliability": -2}, "prerequisites": ["pu_base"]},
        {"id": "pu_power_2", "name": "Maximum Power Mode", "description": "Ultimate straight-line speed",
         "category": "power_unit", "branch": "raw_power", "cost": 18, "development_time": 4,
         "effects": {"power_unit": 6, "reliability": -3}, "prerequisites": ["pu_power_1"]},
        # Efficiency
        {"id": "pu_eff_1", "name": "Energy Recovery Upgrade", "description": "Better hybrid efficiency",
         "category": "power_unit", "branch": "efficiency", "cost": 12, "development_time": 3,
         "effects": {"power_unit": 3, "aero_efficiency": 2}, "prerequisites": ["pu_base"]},
        {"id": "pu_eff_2", "name": "Advanced Hybrid System", "description": "State-of-the-art energy recovery",
         "category": "power_unit", "branch": "efficiency", "cost": 16, "development_time": 4,
         "effects": {"power_unit": 4, "aero_efficiency": 2, "reliability": 1}, "prerequisites": ["pu_eff_1"]},
        # Reliability
        {"id": "pu_rel_1", "name": "Bulletproof Components", "description": "Much more reliable engine",
         "category": "power_unit", "branch": "reliability", "cost": 10, "development_time": 3,
         "effects": {"reliability": 5, "power_unit": 1}, "prerequisites": ["pu_base"]},
        {"id": "pu_rel_2", "name": "Race-Hardened Engine", "description": "Ultimate reliability",
         "category": "power_unit", "branch": "reliability", "cost": 14, "development_time": 4,
         "effects": {"reliability": 6, "power_unit": 2}, "prerequisites": ["pu_rel_1"]},

        # CHASSIS - Base
        {"id": "chassis_base", "name": "Chassis Rigidity", "description": "Foundation for chassis work",
         "category": "chassis", "branch": "base", "cost": 8, "development_time": 2,
         "effects": {"chassis": 2, "downforce": 1}, "prerequisites": []},
        # Mechanical Grip
        {"id": "chassis_mech_1", "name": "Suspension Geometry", "description": "Better mechanical grip",
         "category": "chassis", "branch": "mechanical", "cost": 10, "development_time": 3,
         "effects": {"chassis": 4, "tire_cooling": 2}, "prerequisites": ["chassis_base"]},
        {"id": "chassis_mech_2", "name": "Advanced Dampers", "description": "Superior ride quality",
         "category": "chassis", "branch": "mechanical", "cost": 14, "development_time": 4,
         "effects": {"chassis": 5, "tire_cooling": 3}, "prerequisites": ["chassis_mech_1"]},
        # Aero Integration
        {"id": "chassis_aero_1", "name": "Active Aero Integration", "description": "Chassis-aero synergy",
         "category": "chassis", "branch": "aero_integration", "cost": 12, "development_time": 3,
         "effects": {"chassis": 3, "downforce": 2}, "prerequisites": ["chassis_base"]},
        {"id": "chassis_aero_2", "name": "Ground Effect Optimization", "description": "Maximum floor performance",
         "category": "chassis", "branch": "aero_integration", "cost": 16, "development_time": 4,
         "effects": {"chassis": 4, "downforce": 3, "aero_efficiency": 1}, "prerequisites": ["chassis_aero_1"]},

        # TIRE MANAGEMENT - Base
        {"id": "tire_base", "name": "Basic Cooling", "description": "Foundation for tire management",
         "category": "tire_management", "branch": "base", "cost": 6, "development_time": 2,
         "effects": {"tire_cooling": 2}, "prerequisites": []},
        # Aggressive Cooling
        {"id": "tire_aggr_1", "name": "Brake Duct Redesign", "description": "Better brake/tire cooling",
         "category": "tire_management", "branch": "aggressive", "cost": 8, "development_time": 3,
         "effects": {"tire_cooling": 4, "aero_efficiency": -1}, "prerequisites": ["tire_base"]},
        {"id": "tire_aggr_2", "name": "Advanced Thermal Management", "description": "Optimal tire temps",
         "category": "tire_management", "branch": "aggressive", "cost": 12, "development_time": 4,
         "effects": {"tire_cooling": 5, "chassis": 1, "aero_efficiency": -1}, "prerequisites": ["tire_aggr_1"]},
        # Conservative
        {"id": "tire_cons_1", "name": "Endurance Setup", "description": "Tires last longer",
         "category": "tire_management", "branch": "conservative", "cost": 8, "development_time": 3,
         "effects": {"tire_cooling": 3, "reliability": 2}, "prerequisites": ["tire_base"]},
        {"id": "tire_cons_2", "name": "One-Stop Special", "description": "Ultimate tire life",
         "category": "tire_management", "branch": "conservative", "cost": 12, "development_time": 4,
         "effects": {"tire_cooling": 5, "reliability": 2}, "prerequisites": ["tire_cons_1"]},
    ]


# ==================== MAIN GAME STATE CLASS ====================

class MultiplayerGameState:
    """Manages a multiplayer game session with 2 players."""

    def __init__(self, game_id: str):
        self.game_id = game_id
        self.phase = GamePhase.WAITING_FOR_PLAYERS

        # Season info
        self.current_season = 1
        self.current_race = 0
        self.total_races = 24

        # Player management
        self.players: Dict[str, Dict] = {}  # player_id -> player data
        self.player_order: List[str] = []  # Turn order
        self.current_turn_index = 0
        self.players_ready: Dict[str, bool] = {}

        # Teams - indexed by player_id
        self.player_teams: Dict[str, Dict] = {}

        # All drivers
        self._all_drivers: List[Dict] = []
        self._initialize_drivers()

        # AI teams
        self._ai_teams: Dict[str, Dict] = {}
        self._setup_ai_teams()

        # Track data
        self._tracks: List[Dict] = []
        self._load_tracks()

        # Race state
        self.qualifying_results: List[Dict] = []
        self.race_entries: List[Dict] = []
        self.race_events: List[Dict] = []
        self.current_lap = 0
        self.total_laps = 0
        self.race_finished = False
        self.weather = Weather.DRY
        self.last_weather = Weather.DRY  # Track weather changes
        self.safety_car = False
        self.safety_car_laps = 0

        # Tire selections - player_id -> {driver_id: compound}
        self.player_tire_selections: Dict[str, Dict[str, str]] = {}

        # Synchronized pit decision tracking for multiplayer
        # player_id -> list of driver_ids needing pit decision
        self.pit_decisions_needed: Dict[str, List[str]] = {}
        # player_id -> True if they've confirmed their pit decisions (or chose to stay out)
        self.pit_decisions_confirmed: Dict[str, bool] = {}
        # Whether we're currently paused for pit decisions
        self.race_paused_for_pits = False

        # Weekend modifiers
        self._weekend_modifiers: Dict[str, Dict] = {}

        # Standings
        self._driver_standings: List[Dict] = []
        self._constructor_standings: List[Dict] = []

        # Inbox - player_id -> messages
        self.inboxes: Dict[str, List[Dict]] = {}

        # Available sponsors for selection
        self.available_sponsors: Dict[str, List[Dict]] = {}

    def _initialize_drivers(self):
        """Load all drivers from data files."""
        all_data = F1_DRIVERS + F2_DRIVERS
        for i, d in enumerate(all_data):
            stats = d.get("stats", d)
            if isinstance(stats, dict) and "pace" in stats:
                overall = calc_overall(stats)
                # Calculate minimum team prestige based on driver quality
                # Top drivers (85+) want top teams, mid drivers (70-84) want midfield+
                # Lower drivers (below 70) will consider any team
                min_prestige = self._calculate_driver_min_prestige(overall, d["age"])

                driver = {
                    "id": str(i),
                    "name": d["name"],
                    "age": d["age"],
                    "nationality": d["nationality"],
                    "stats": stats.copy(),
                    "overall": overall,
                    "potential": calc_potential(d["age"], overall),
                    "salary": d.get("salary", 1),
                    "market_value": d.get("market_value", 5),
                    "team_name": d.get("team_name"),
                    "original_team": d.get("team_name"),
                    "is_free_agent": d.get("team_name") is None,
                    "season_points": 0, "race_wins": 0, "podiums": 0, "dnfs": 0,
                    "morale": 75, "confidence": 75,
                    "win_streak": 0, "podium_streak": 0, "no_points_streak": 0,
                    "dnf_streak": 0, "beaten_by_teammate_streak": 0,
                    "contract_years": 2 if d.get("team_name") else 0,
                    "is_number_one": False,
                    "player_id": None,
                    "min_team_prestige": min_prestige,  # Minimum team prestige to sign
                    "career_races": random.randint(0, 200) if overall > 75 else random.randint(0, 50),
                }
                self._all_drivers.append(driver)

    def _calculate_driver_min_prestige(self, overall: int, age: int) -> int:
        """Calculate minimum team prestige a driver requires based on their quality."""
        # Base prestige requirement from skill
        if overall >= 90:
            base = 85  # Elite drivers only want top teams
        elif overall >= 85:
            base = 75  # Very good drivers want competitive teams
        elif overall >= 80:
            base = 60  # Good drivers want midfield or better
        elif overall >= 75:
            base = 45  # Decent drivers want decent teams
        elif overall >= 70:
            base = 30  # Average drivers are more flexible
        elif overall >= 65:
            base = 15  # Below average will take most opportunities
        else:
            base = 0  # Rookies/low-rated will take any seat

        # Age modifier - older drivers may be more willing to take a lower seat
        # Younger drivers in their prime want better seats
        if age <= 22:
            base -= 15  # Young talents willing to prove themselves
        elif age <= 25:
            base -= 5  # Still developing
        elif age >= 35:
            base -= 20  # Older drivers more flexible for final years
        elif age >= 32:
            base -= 10  # Veterans may accept less

        return max(0, min(95, base))

    def _setup_ai_teams(self):
        """Set up AI team data."""
        # Budget ranges by team tier
        team_budgets = {
            "Red Bull Racing": (180, 220),
            "Mercedes": (170, 210),
            "Ferrari": (170, 210),
            "McLaren": (140, 180),
            "Aston Martin": (130, 170),
            "Alpine": (100, 140),
            "Williams": (80, 120),
            "Sauber": (75, 115),
            "Haas": (70, 110),
            "RB": (90, 130),
        }
        for team_name, car_stats in AI_TEAM_CARS.items():
            budget_range = team_budgets.get(team_name, (80, 120))
            self._ai_teams[team_name] = {
                "name": team_name,
                "car": car_stats.copy(),
                "budget": random.uniform(*budget_range),
                "season_points": 0,
                "race_wins": 0,
                "podiums": 0,
                "upgrade_budget": 0,  # Money set aside for upgrades
                "reputation": calc_car_overall(car_stats),  # AI reputation = car quality
            }

    def _load_tracks(self):
        """Load track data."""
        for t in TRACKS:
            self._tracks.append({
                "name": t.get("name", "Unknown"),
                "country": t.get("country", "Unknown"),
                "city": t.get("city", "Unknown"),
                "laps": t.get("laps", 50),
                "track_type": t.get("track_type", "CIRCUIT"),
                "tire_degradation": t.get("tire_degradation", 1.0),
                "overtaking_difficulty": t.get("overtaking_difficulty", 5),
                "base_lap_time": t.get("base_lap_time", 90.0),
                "pit_loss_time": t.get("pit_loss_time", 22.0),
            })
        self.total_races = len(self._tracks)

    # ==================== PLAYER MANAGEMENT ====================

    def is_player(self, player_id: str) -> bool:
        """Check if a player is in this game."""
        return player_id in self.players

    def set_player_ready(self, player_id: str, ready: bool = True) -> bool:
        """Set a player's ready status."""
        return self.mark_ready(player_id, ready)

    def add_player(self, player_id: str, username: str) -> bool:
        """Add a player to the game."""
        if len(self.players) >= 2:
            return False
        if player_id in self.players:
            return True  # Already in game

        # Default team name (will be customized)
        default_team_name = f"{username} Racing"
        self.players[player_id] = {
            "player_id": player_id,
            "username": username,
            "team_name": default_team_name,
            "is_ready": False,
            "has_set_team_name": False,
            "has_selected_sponsor": False,
            "has_selected_tires": False,
            "drivers_signed": 0,
        }
        self.player_order.append(player_id)
        self.players_ready[player_id] = False
        self.inboxes[player_id] = []

        # Create player team with backmarker-level car
        self.player_teams[player_id] = {
            "id": player_id,
            "name": default_team_name,
            "budget": 50.0,
            # Backmarker car stats - starting from the back of the grid
            "car": {"downforce": 62, "aero_efficiency": 60, "chassis": 63,
                    "power_unit": 61, "reliability": 68, "tire_cooling": 60},
            "drivers": [],
            "season_points": 0,
            "race_wins": 0,
            "podiums": 0,
            "player_id": player_id,
            "sponsor": None,
            "development_tree": self._create_player_dev_tree(),
            "reputation": 20,  # Starting reputation as a new team
            "seasons_completed": 0,
        }

        # Generate sponsors for this player
        self.available_sponsors[player_id] = self._generate_sponsors()

        # If we have 2 players, start with team name selection
        if len(self.players) == 2:
            self.phase = GamePhase.TEAM_NAME_SELECTION
            self._add_inbox_message_all("Game Started", "Welcome! Choose your team name to begin your F1 journey.", MessageType.TEAM_UPDATE)

        return True

    def set_team_name(self, player_id: str, team_name: str) -> bool:
        """Set the player's team name."""
        if player_id not in self.players:
            return False
        if self.phase != GamePhase.TEAM_NAME_SELECTION:
            return False

        # Validate team name
        team_name = team_name.strip()
        if len(team_name) < 3 or len(team_name) > 30:
            return False

        # Update player and team
        self.players[player_id]["team_name"] = team_name
        self.players[player_id]["has_set_team_name"] = True
        self.player_teams[player_id]["name"] = team_name

        self._add_inbox_message(player_id, "Team Created",
            f"Welcome to F1! {team_name} is now officially registered. "
            f"As a new team, you'll need to prove yourself before top drivers will consider joining.",
            MessageType.TEAM_UPDATE)

        # Check if all players have set their team names
        if all(p["has_set_team_name"] for p in self.players.values()):
            self.phase = GamePhase.SPONSOR_SELECTION

        return True

    def get_team_prestige(self, player_id: str) -> int:
        """Calculate team prestige for driver signing interest."""
        if player_id not in self.player_teams:
            return 0

        team = self.player_teams[player_id]
        car = team["car"]

        # Car quality (40% of prestige)
        car_overall = calc_car_overall(car)
        car_score = (car_overall / 100) * 40

        # Budget (20% of prestige)
        budget_score = min(20, (team["budget"] / 200) * 20)

        # Reputation/Results (30% of prestige)
        reputation = team.get("reputation", 20)
        rep_score = (reputation / 100) * 30

        # Seasons completed (10% of prestige) - experience matters
        seasons = team.get("seasons_completed", 0)
        season_score = min(10, seasons * 2)

        return int(car_score + budget_score + rep_score + season_score)

    def _create_player_dev_tree(self) -> Dict:
        """Create a fresh development tree for a player."""
        return {
            "nodes": create_development_tree(),
            "active_developments": [],
            "completed_developments": [],
            "branch_choices": {},
        }

    def _generate_sponsors(self) -> List[Dict]:
        """Generate 5 random sponsors for selection."""
        sponsors = []
        # 2 bronze, 2 silver, 1 gold
        tiers = ["bronze", "bronze", "silver", "silver", "gold"]
        random.shuffle(tiers)
        for tier in tiers:
            s = random.choice(SPONSORS[tier])
            obj_desc = self._get_objective_description(s["objective_type"], s["target"])
            sponsors.append({
                "id": str(uuid.uuid4())[:8],
                "name": s["name"],
                "tier": tier,
                "payment_per_race": s["payment"],
                "season_bonus": s["bonus"],
                "objective_type": s["objective_type"],
                "objective_target": s["target"],
                "objective_description": obj_desc,
            })
        return sponsors

    def _get_objective_description(self, obj_type: str, target: int) -> str:
        if obj_type == "finish_position":
            return f"Finish P{target} or better each race"
        elif obj_type == "points_finish":
            return "Score points (top 10) each race"
        elif obj_type == "podium":
            return "Achieve a podium (top 3) each race"
        elif obj_type == "win":
            return "Win each race"
        return f"Achieve target: {target}"

    def select_sponsor(self, player_id: str, sponsor_id: str) -> bool:
        """Player selects their sponsor."""
        if player_id not in self.players:
            return False
        if self.players[player_id]["has_selected_sponsor"]:
            return False

        sponsors = self.available_sponsors.get(player_id, [])
        sponsor = next((s for s in sponsors if s["id"] == sponsor_id), None)
        if not sponsor:
            return False

        self.player_teams[player_id]["sponsor"] = sponsor.copy()
        self.player_teams[player_id]["sponsor"]["races_completed"] = 0
        self.player_teams[player_id]["sponsor"]["objectives_met"] = 0
        self.players[player_id]["has_selected_sponsor"] = True

        self._add_inbox_message(player_id, "Sponsor Signed",
            f"Welcome aboard! {sponsor['name']} is excited to partner with you. "
            f"Objective: {sponsor['objective_description']}. "
            f"Payment: ${sponsor['payment_per_race']}M per race.",
            MessageType.TEAM_UPDATE)

        # Check if both players have selected sponsors
        if all(p["has_selected_sponsor"] for p in self.players.values()):
            self.phase = GamePhase.TEAM_SETUP
            self.current_race = 0
            self._shuffle_turn_order()
        return True

    # ==================== DRIVER SIGNING ====================

    def get_available_drivers(self, player_id: str, include_uninterested: bool = True) -> List[Dict]:
        """Get drivers available for signing with interest information."""
        signed_ids = set()
        for team in self.player_teams.values():
            for d in team["drivers"]:
                signed_ids.add(d["id"])

        team_prestige = self.get_team_prestige(player_id)

        available = []
        for d in self._all_drivers:
            if d["id"] not in signed_ids:
                driver_copy = d.copy()
                min_prestige = d.get("min_team_prestige", 0)

                # Check if driver would be interested
                if team_prestige >= min_prestige:
                    driver_copy["interested"] = True
                    driver_copy["interest_reason"] = "Interested in joining your team"
                else:
                    driver_copy["interested"] = False
                    prestige_gap = min_prestige - team_prestige
                    if prestige_gap > 40:
                        driver_copy["interest_reason"] = "Would never consider joining a backmarker team"
                    elif prestige_gap > 25:
                        driver_copy["interest_reason"] = "Looking for a more competitive seat"
                    elif prestige_gap > 10:
                        driver_copy["interest_reason"] = "Wants a team with better prospects"
                    else:
                        driver_copy["interest_reason"] = "Considering other offers first"

                if include_uninterested or driver_copy["interested"]:
                    available.append(driver_copy)

        available.sort(key=lambda x: (x["interested"], x["market_value"]), reverse=True)
        return available

    def get_interested_drivers(self, player_id: str) -> List[Dict]:
        """Get only drivers who would join this team."""
        return self.get_available_drivers(player_id, include_uninterested=False)

    def get_min_driver_cost(self, player_id: str, exclude_id: str = None) -> float:
        """Get minimum cost of available drivers."""
        signed_ids = set()
        for team in self.player_teams.values():
            for d in team["drivers"]:
                signed_ids.add(d["id"])

        min_cost = float('inf')
        for d in self._all_drivers:
            if d["id"] not in signed_ids and d["id"] != exclude_id:
                if d["market_value"] < min_cost:
                    min_cost = d["market_value"]
        return min_cost if min_cost != float('inf') else 0

    def sign_driver(self, player_id: str, driver_id: str, salary: float, years: int, is_number_one: bool) -> bool:
        """Sign a driver to a player's team."""
        if player_id not in self.player_teams:
            return False

        team = self.player_teams[player_id]
        if len(team["drivers"]) >= 2:
            return False

        # Check if it's this player's turn (in multiplayer)
        if len(self.players) == 2 and not self._is_player_turn(player_id):
            return False

        driver = next((d for d in self._all_drivers if d["id"] == driver_id), None)
        if not driver:
            return False

        # Check if driver is interested in joining this team
        team_prestige = self.get_team_prestige(player_id)
        min_prestige = driver.get("min_team_prestige", 0)
        if team_prestige < min_prestige:
            return False  # Driver not interested

        # Check affordability
        if driver["market_value"] > team["budget"]:
            return False

        # If signing first driver, must have enough left for a second
        if len(team["drivers"]) == 0:
            min_cost = self.get_min_driver_cost(player_id, exclude_id=driver_id)
            if team["budget"] - driver["market_value"] < min_cost:
                return False

        # Sign the driver
        team["budget"] -= driver["market_value"]
        driver["team_name"] = team["name"]
        driver["player_id"] = player_id
        driver["contract_years"] = years
        driver["is_number_one"] = is_number_one
        driver["is_free_agent"] = False
        team["drivers"].append(driver)
        self.players[player_id]["drivers_signed"] = len(team["drivers"])

        self._add_inbox_message(player_id, "Driver Signed",
            f"{driver['name']} has joined your team! Contract: {years} years at ${salary}M/year.",
            MessageType.TEAM_UPDATE)

        # Advance turn
        self._advance_turn()

        # Check if all players have 2 drivers
        if all(len(self.player_teams[pid]["drivers"]) >= 2 for pid in self.players):
            self.phase = GamePhase.MAIN_MENU
            self.current_race = 1
            self._initialize_standings()
            self._add_inbox_message_all("Season Ready", "All teams are set! The season is ready to begin.", MessageType.TEAM_UPDATE)

        return True

    def release_driver(self, player_id: str, driver_id: str) -> bool:
        """Release a driver from a team."""
        if player_id not in self.player_teams:
            return False

        team = self.player_teams[player_id]
        driver = next((d for d in team["drivers"] if d["id"] == driver_id), None)
        if not driver:
            return False

        team["drivers"].remove(driver)
        driver["team_name"] = None
        driver["player_id"] = None
        driver["is_free_agent"] = True
        self.players[player_id]["drivers_signed"] = len(team["drivers"])

        self._add_inbox_message(player_id, "Driver Released",
            f"{driver['name']} has been released from your team.",
            MessageType.TEAM_UPDATE)

        return True

    # ==================== CAR UPGRADES ====================

    def get_upgrade_options(self, player_id: str) -> List[Dict]:
        """Get available car upgrade options."""
        if player_id not in self.player_teams:
            return []

        team = self.player_teams[player_id]
        car = team["car"]
        budget = team["budget"]

        options = []
        stat_names = {
            "downforce": "Downforce",
            "aero_efficiency": "Aero Efficiency",
            "chassis": "Chassis",
            "power_unit": "Power Unit",
            "reliability": "Reliability",
            "tire_cooling": "Tire Cooling"
        }

        for stat, display in stat_names.items():
            current = car[stat]
            if current >= 100:
                continue
            cost = get_upgrade_cost(current)
            options.append({
                "stat_name": stat,
                "display_name": display,
                "current_value": current,
                "upgrade_cost": cost,
                "new_value": current + 1,
                "can_afford": budget >= cost
            })
        return options

    def upgrade_car(self, player_id: str, stat_name: str, points: int = 1) -> bool:
        """Upgrade a car stat."""
        if player_id not in self.player_teams:
            return False

        team = self.player_teams[player_id]
        car = team["car"]

        if stat_name not in car:
            return False
        if car[stat_name] >= 100:
            return False

        total_cost = 0
        for _ in range(points):
            if car[stat_name] >= 100:
                break
            cost = get_upgrade_cost(car[stat_name])
            if team["budget"] < cost:
                break
            total_cost += cost
            team["budget"] -= cost
            car[stat_name] += 1

        if total_cost > 0:
            self._add_inbox_message(player_id, "Car Upgraded",
                f"{stat_name.replace('_', ' ').title()} upgraded! New value: {car[stat_name]}. Cost: ${total_cost}M",
                MessageType.TEAM_UPDATE)
            return True
        return False

    # ==================== DEVELOPMENT TREE ====================

    def start_development(self, player_id: str, node_id: str) -> bool:
        """Start a development node."""
        if player_id not in self.player_teams:
            return False

        team = self.player_teams[player_id]
        tree = team["development_tree"]
        nodes = tree["nodes"]

        node = next((n for n in nodes if n["id"] == node_id), None)
        if not node:
            return False

        # Check if already completed or in progress
        if node["id"] in tree["completed_developments"]:
            return False
        if node["id"] in tree["active_developments"]:
            return False

        # Check max active
        if len(tree["active_developments"]) >= 2:
            return False

        # Check prerequisites
        for prereq in node["prerequisites"]:
            if prereq not in tree["completed_developments"]:
                return False

        # Check if branch is locked
        if node["branch"] != "base" and node["category"] in tree["branch_choices"]:
            if tree["branch_choices"][node["category"]] != node["branch"]:
                return False

        # Check budget
        if team["budget"] < node["cost"]:
            return False

        # Start development
        team["budget"] -= node["cost"]
        tree["active_developments"].append(node["id"])
        node["is_in_progress"] = True
        node["races_remaining"] = node["development_time"]

        # Lock other branches in this category
        if node["branch"] != "base":
            tree["branch_choices"][node["category"]] = node["branch"]
            for n in nodes:
                if n["category"] == node["category"] and n["branch"] != "base" and n["branch"] != node["branch"]:
                    n["is_locked"] = True

        self._add_inbox_message(player_id, "Development Started",
            f"Started development: {node['name']}. Will be ready in {node['development_time']} races.",
            MessageType.TEAM_UPDATE)

        return True

    def _process_developments(self, player_id: str):
        """Process development progress after a race."""
        if player_id not in self.player_teams:
            return

        team = self.player_teams[player_id]
        tree = team["development_tree"]
        car = team["car"]

        completed = []
        for node_id in tree["active_developments"]:
            node = next((n for n in tree["nodes"] if n["id"] == node_id), None)
            if node:
                node["races_remaining"] -= 1
                if node["races_remaining"] <= 0:
                    completed.append(node_id)
                    # Apply effects
                    for stat, change in node["effects"].items():
                        if stat in car:
                            car[stat] = max(1, min(100, car[stat] + change))
                    node["is_in_progress"] = False
                    node["is_completed"] = True
                    tree["completed_developments"].append(node_id)
                    self._add_inbox_message(player_id, "Development Complete",
                        f"{node['name']} is complete! Effects applied to your car.",
                        MessageType.TEAM_UPDATE, MessagePriority.IMPORTANT)

        for node_id in completed:
            tree["active_developments"].remove(node_id)

    # ==================== TURN MANAGEMENT ====================

    def _is_player_turn(self, player_id: str) -> bool:
        """Check if it's a player's turn."""
        if len(self.players) < 2:
            return True
        if self.current_turn_index >= len(self.player_order):
            return False
        return self.player_order[self.current_turn_index] == player_id

    def _get_current_player_id(self) -> str:
        """Get the current player's ID."""
        if self.current_turn_index < len(self.player_order):
            return self.player_order[self.current_turn_index]
        return self.player_order[0] if self.player_order else ""

    def _advance_turn(self):
        """Advance to the next player's turn."""
        self.current_turn_index = (self.current_turn_index + 1) % len(self.player_order)

    def _shuffle_turn_order(self):
        """Shuffle turn order for fairness."""
        random.shuffle(self.player_order)
        self.current_turn_index = 0

    def _rotate_turn_order(self):
        """Rotate turn order (first becomes last)."""
        if len(self.player_order) > 1:
            self.player_order.append(self.player_order.pop(0))
        self.current_turn_index = 0

    def mark_ready(self, player_id: str, ready: bool = True) -> bool:
        """Mark a player as ready to proceed."""
        if player_id not in self.players:
            return False
        self.players_ready[player_id] = ready
        return True

    def all_players_ready(self) -> bool:
        """Check if all players are ready."""
        return all(self.players_ready.values())

    def reset_ready(self):
        """Reset all players' ready status."""
        for pid in self.players_ready:
            self.players_ready[pid] = False

    # ==================== RACE WEEKEND ====================

    def start_race_weekend(self, player_id: str = None) -> bool:
        """Start a race weekend."""
        if self.phase != GamePhase.MAIN_MENU:
            return False
        if self.current_race > len(self._tracks):
            return False

        # Both players should be ready or it's single player
        if len(self.players) == 2:
            if player_id:
                self.mark_ready(player_id, True)
            if not self.all_players_ready():
                return True  # Waiting for other player

        self.reset_ready()
        self._generate_weekend_modifiers()
        self._run_qualifying()
        self.phase = GamePhase.QUALIFYING
        return True

    def _generate_weekend_modifiers(self):
        """Generate weekend form modifiers."""
        self._weekend_modifiers = {}
        all_drivers = []
        for team in self.player_teams.values():
            all_drivers.extend(team["drivers"])
        for d in self._all_drivers:
            if d["team_name"] and d not in all_drivers:
                all_drivers.append(d)

        for d in all_drivers:
            consistency_factor = d["stats"]["consistency"] / 100
            form_variance = 5 * (1 - consistency_factor * 0.6)
            weekend_form = random.gauss(0, form_variance)
            quali_bonus = random.gauss(0, 1.5)

            car = self._get_car_for_driver(d)
            car_perf = calc_car_overall(car)
            mech_issue_chance = 0.08 if car_perf > 75 else 0.05 if car_perf > 60 else 0.03
            has_mech_issue = random.random() < mech_issue_chance

            underdog_boost = 0.0
            if car_perf < 65 and random.random() < 0.12:
                underdog_boost = random.uniform(3, 8)

            self._weekend_modifiers[d["name"]] = {
                "weekend_form": weekend_form + underdog_boost,
                "quali_form": quali_bonus,
                "mechanical_issue": has_mech_issue,
                "underdog_weekend": underdog_boost > 0
            }

    def _get_car_for_driver(self, driver: Dict) -> Dict:
        """Get car stats for a driver."""
        team_name = driver.get("team_name")
        if not team_name:
            return {"downforce": 65, "aero_efficiency": 65, "chassis": 65, "power_unit": 65, "reliability": 70, "tire_cooling": 65}

        # Check player teams
        for team in self.player_teams.values():
            if team["name"] == team_name:
                return team["car"]

        # Check AI teams
        if team_name in self._ai_teams:
            return self._ai_teams[team_name]["car"]

        return AI_TEAM_CARS.get(team_name, {"downforce": 65, "aero_efficiency": 65, "chassis": 65, "power_unit": 65, "reliability": 70, "tire_cooling": 65})

    def _run_qualifying(self):
        """Simulate qualifying."""
        self.qualifying_results = []
        track = self._tracks[self.current_race - 1]
        entries = []

        # Gather all drivers
        all_drivers = []
        for team in self.player_teams.values():
            for d in team["drivers"]:
                all_drivers.append((d, team["name"], team.get("player_id")))

        # Add AI drivers
        for d in self._all_drivers:
            if d["team_name"] and d["player_id"] is None:
                # Check if not already in a player team
                in_player_team = any(d in team["drivers"] for team in self.player_teams.values())
                if not in_player_team:
                    all_drivers.append((d, d["team_name"], None))

        for driver, team_name, player_id in all_drivers:
            car = self._get_car_for_driver(driver)
            modifiers = self._weekend_modifiers.get(driver["name"], {})

            entry = {
                "driver": driver,
                "car": car,
                "tire": TireState("soft"),
                "weekend_form": modifiers.get("weekend_form", 0),
                "quali_form": modifiers.get("quali_form", 0),
                "mechanical_issue": modifiers.get("mechanical_issue", False)
            }

            # Simulate 3 quali laps
            lap_times = [self._calculate_lap_time(entry, Weather.DRY, is_qualifying=True) for _ in range(3)]
            best_time = min(lap_times)

            if random.random() < 0.02:  # 2% incident chance
                best_time += 5.0

            entries.append({
                "driver_name": driver["name"],
                "team_name": team_name,
                "lap_time": best_time,
                "is_player_driver": player_id is not None,
                "player_id": player_id
            })

        entries.sort(key=lambda x: x["lap_time"])
        pole_time = entries[0]["lap_time"]

        for i, entry in enumerate(entries):
            mins = int(entry["lap_time"] // 60)
            secs = entry["lap_time"] % 60
            gap = entry["lap_time"] - pole_time

            self.qualifying_results.append({
                "position": i + 1,
                "driver_name": entry["driver_name"],
                "team_name": entry["team_name"],
                "lap_time": f"{mins}:{secs:06.3f}" if i == 0 else f"+{gap:.3f}",
                "is_player_driver": entry["is_player_driver"],
                "player_id": entry["player_id"]
            })

    def _calculate_lap_time(self, entry: Dict, weather: Weather, is_qualifying: bool = False) -> float:
        """Calculate lap time."""
        track = self._tracks[self.current_race - 1]
        base_time = track.get("base_lap_time", 90.0)

        car = entry["car"]
        driver = entry["driver"]
        tire = entry["tire"]

        car_factor = (100 - calc_car_overall(car)) * 0.030
        driver_factor = (100 - driver["stats"]["pace"]) * 0.040
        tire_perf = tire.performance
        tire_factor = (1.0 - tire_perf) * 3.5

        if tire.wear > 70:
            tire_factor += ((tire.wear - 70) / 30) * 1.5

        consistency = driver["stats"]["consistency"]
        variance = random.gauss(0, (100 - consistency) * 0.006)

        modifiers = self._weekend_modifiers.get(driver["name"], {})
        form_factor = -modifiers.get("weekend_form", 0) * 0.02
        if is_qualifying:
            form_factor -= modifiers.get("quali_form", 0) * 0.015

        mech_penalty = random.uniform(0.2, 0.5) if modifiers.get("mechanical_issue", False) else 0

        weather_factor = 0
        if weather == Weather.LIGHT_RAIN:
            if tire.compound in ["soft", "medium", "hard"]:
                weather_factor = 5.0 - (driver["stats"]["wet_skill"] * 0.03)
        elif weather == Weather.HEAVY_RAIN:
            if tire.compound in ["soft", "medium", "hard"]:
                weather_factor = 15.0 - (driver["stats"]["wet_skill"] * 0.05)

        # Morale effect
        morale_factor = (driver.get("morale", 75) - 75) * -0.002

        return base_time + car_factor + driver_factor + tire_factor + variance + weather_factor + form_factor + mech_penalty + morale_factor

    def advance_to_tire_selection(self, player_id: str) -> bool:
        """Move from qualifying to tire selection."""
        if self.phase != GamePhase.QUALIFYING:
            return False

        if len(self.players) == 2 and not self.all_players_ready():
            self.mark_ready(player_id, True)
            if not self.all_players_ready():
                return True

        self.reset_ready()
        self.phase = GamePhase.TIRE_SELECTION
        self.player_tire_selections = {pid: {} for pid in self.players}
        return True

    def select_tire(self, player_id: str, driver_id: str, compound) -> bool:
        """Select starting tire for a driver."""
        if self.phase != GamePhase.TIRE_SELECTION:
            return False
        if player_id not in self.player_tire_selections:
            return False

        # Handle both string and enum
        compound_str = compound.value if hasattr(compound, 'value') else str(compound)
        self.player_tire_selections[player_id][driver_id] = compound_str

        # Check if this player has selected for all their drivers
        team = self.player_teams[player_id]
        all_selected = len(self.player_tire_selections[player_id]) >= len(team["drivers"])
        if all_selected:
            self.players[player_id]["has_selected_tires"] = True

        # Check if all players have selected
        if all(self.players[pid].get("has_selected_tires", False) for pid in self.players):
            self._start_race()

        return True

    def _start_race(self):
        """Initialize race state."""
        track = self._tracks[self.current_race - 1]
        self.total_laps = track["laps"]
        self.current_lap = 0
        self.race_finished = False
        self.race_events = []
        self.race_entries = []
        self.weather = Weather.DRY
        self.safety_car = False
        self.safety_car_laps = 0

        # Reset tire selection flags
        for pid in self.players:
            self.players[pid]["has_selected_tires"] = False

        for q in self.qualifying_results:
            driver = next((d for d in self._all_drivers if d["name"] == q["driver_name"]), None)
            if not driver:
                for team in self.player_teams.values():
                    driver = next((d for d in team["drivers"] if d["name"] == q["driver_name"]), None)
                    if driver:
                        break

            if not driver:
                continue

            car = self._get_car_for_driver(driver)

            # Get tire selection
            tire_compound = "medium"
            if q.get("player_id") and q["player_id"] in self.player_tire_selections:
                selections = self.player_tire_selections[q["player_id"]]
                for did, comp in selections.items():
                    team = self.player_teams.get(q["player_id"])
                    if team:
                        for d in team["drivers"]:
                            if d["id"] == did and d["name"] == q["driver_name"]:
                                tire_compound = comp
                                break
            else:
                # AI tire strategy
                if track["overtaking_difficulty"] >= 7:
                    tire_compound = "medium" if q["position"] <= 5 else "soft"
                else:
                    if q["position"] <= 3:
                        tire_compound = "medium"
                    elif q["position"] <= 10:
                        tire_compound = random.choice(["soft", "medium"])
                    else:
                        tire_compound = "soft"

            modifiers = self._weekend_modifiers.get(driver["name"], {})

            self.race_entries.append({
                "position": q["position"],
                "driver": driver,
                "driver_name": driver["name"],
                "team_name": q["team_name"],
                "car": car,
                "tire": TireState(tire_compound),
                "total_time": 0.0,
                "gap": "Leader" if q["position"] == 1 else f"+{q['position'] * 0.5:.1f}s",
                "pit_stops": 0,
                "status": "racing",
                "is_player_driver": q.get("is_player_driver", False),
                "player_id": q.get("player_id"),
                "weekend_form": modifiers.get("weekend_form", 0),
                "mechanical_issue": modifiers.get("mechanical_issue", False),
                "dnf": False,
                "dnf_reason": ""
            })

        self._simulate_race_start()
        self.phase = GamePhase.RACE_IN_PROGRESS

    def _simulate_race_start(self):
        """Simulate race start."""
        start_scores = []

        for entry in self.race_entries:
            if entry["dnf"]:
                continue

            driver = entry["driver"]
            start_skill = (driver["stats"]["pace"] + driver["stats"]["consistency"]) / 2
            weekend_bonus = entry.get("weekend_form", 0) * 0.3

            base_score = entry["position"] * 2
            variance = random.gauss(0, 2.5)
            skill_factor = (50 - start_skill) * 0.1

            start_score = base_score + variance + skill_factor - weekend_bonus
            start_scores.append((entry, start_score))

        # First lap incident (5% chance)
        if random.random() < 0.05:
            incident_count = random.randint(1, 3)
            active = [e for e, _ in start_scores if not e["dnf"]]
            victims = random.sample(active, min(incident_count, len(active)))

            for victim in victims:
                if random.random() < 0.4:
                    victim["dnf"] = True
                    victim["status"] = "dnf"
                    victim["dnf_reason"] = random.choice([
                        "First lap collision", "Spun off at Turn 1",
                        "Contact with another car", "Crash at the start"
                    ])
                    self.race_events.append({
                        "lap": 1,
                        "event_type": "dnf",
                        "description": f"{victim['driver_name']} OUT - {victim['dnf_reason']}!"
                    })

        start_scores.sort(key=lambda x: x[1])

        pos = 1
        for entry, _ in start_scores:
            if not entry["dnf"]:
                old_pos = entry["position"]
                entry["position"] = pos
                if abs(old_pos - pos) >= 3:
                    event_type = "position"
                    if pos < old_pos:
                        self.race_events.append({
                            "lap": 1, "event_type": event_type,
                            "description": f"{entry['driver_name']} great start! P{old_pos} -> P{pos}"
                        })
                    else:
                        self.race_events.append({
                            "lap": 1, "event_type": event_type,
                            "description": f"{entry['driver_name']} poor start! P{old_pos} -> P{pos}"
                        })
                pos += 1

    def can_simulate_lap(self) -> bool:
        """Check if race simulation can proceed."""
        if self.phase != GamePhase.RACE_IN_PROGRESS:
            return False
        if self.race_paused_for_pits:
            # Check if all players have confirmed their decisions
            for pid in self.players:
                if pid in self.pit_decisions_needed and self.pit_decisions_needed[pid]:
                    if not self.pit_decisions_confirmed.get(pid, False):
                        return False
            # All confirmed, unpause
            self.race_paused_for_pits = False
            self.pit_decisions_needed = {}
            self.pit_decisions_confirmed = {}
        return True

    def _check_driver_needs_pit(self, entry: Dict) -> bool:
        """Check if a driver needs a pit decision."""
        if entry["dnf"]:
            return False

        # High tire wear (70% or more)
        if entry["tire"].wear >= 70:
            return True

        # Wrong tires for weather
        is_wet = self.weather != Weather.DRY
        has_wet_tires = entry["tire"].compound in ["intermediate", "wet"]

        if is_wet and not has_wet_tires:
            return True

        # Weather just changed to dry and on wet tires
        if not is_wet and has_wet_tires and entry["pit_stops"] > 0:
            return True

        return False

    def _check_all_pit_decisions(self):
        """Check if any player drivers need pit decisions and pause if so."""
        if len(self.players) < 2:
            return  # Single player doesn't need sync

        weather_changed = self.weather != self.last_weather and self.weather != Weather.DRY

        pit_needed = {}
        for entry in self.race_entries:
            if not entry.get("is_player_driver") or entry["dnf"]:
                continue

            player_id = entry.get("player_id")
            if not player_id:
                continue

            if self._check_driver_needs_pit(entry) or weather_changed:
                if player_id not in pit_needed:
                    pit_needed[player_id] = []
                pit_needed[player_id].append(entry["driver"]["id"])

        # If ANY player needs a pit decision, pause for ALL players
        if pit_needed:
            self.race_paused_for_pits = True
            self.pit_decisions_needed = pit_needed
            self.pit_decisions_confirmed = {pid: False for pid in self.players}
            # Players who don't need pit decisions are auto-confirmed
            for pid in self.players:
                if pid not in pit_needed:
                    self.pit_decisions_confirmed[pid] = True

        self.last_weather = self.weather

    def confirm_pit_decisions(self, player_id: str) -> bool:
        """Player confirms they've made all their pit decisions (pit or stay out)."""
        if player_id not in self.players:
            return False
        self.pit_decisions_confirmed[player_id] = True
        return True

    def get_pit_decision_status(self, player_id: str) -> Dict:
        """Get pit decision status for a player."""
        my_drivers_needing_pit = self.pit_decisions_needed.get(player_id, [])

        # Check who we're waiting for
        waiting_for = []
        for pid, confirmed in self.pit_decisions_confirmed.items():
            if not confirmed and pid != player_id:
                waiting_for.append(self.players[pid]["username"])

        return {
            "paused_for_pits": self.race_paused_for_pits,
            "my_drivers_needing_pit": my_drivers_needing_pit,
            "i_need_to_decide": player_id in self.pit_decisions_needed and not self.pit_decisions_confirmed.get(player_id, True),
            "i_have_confirmed": self.pit_decisions_confirmed.get(player_id, True),
            "waiting_for_players": waiting_for,
            "all_confirmed": all(self.pit_decisions_confirmed.values()) if self.pit_decisions_confirmed else True
        }

    def simulate_race_lap(self, player_id: str = None):
        """Simulate one lap."""
        if self.phase != GamePhase.RACE_IN_PROGRESS:
            return

        # Check if we can simulate (not paused for pit decisions)
        if not self.can_simulate_lap():
            return  # Race paused, waiting for pit decisions

        self.current_lap += 1
        track = self._tracks[self.current_race - 1]

        # Weather change
        if random.random() < 0.005:
            if self.weather == Weather.DRY:
                self.weather = Weather.LIGHT_RAIN
                self.race_events.append({"lap": self.current_lap, "event_type": "weather", "description": "Light rain starting!"})
            elif self.weather == Weather.LIGHT_RAIN:
                if random.random() < 0.6:
                    self.weather = Weather.HEAVY_RAIN
                    self.race_events.append({"lap": self.current_lap, "event_type": "weather", "description": "HEAVY RAIN!"})
                else:
                    self.weather = Weather.DRY
                    self.race_events.append({"lap": self.current_lap, "event_type": "weather", "description": "Track drying!"})

        # Safety car
        if self.safety_car:
            self.safety_car_laps -= 1
            if self.safety_car_laps <= 0:
                self.safety_car = False
                self.race_events.append({"lap": self.current_lap, "event_type": "safety_car", "description": "Safety car in - RACING RESUMES!"})

        # Process each driver
        for entry in self.race_entries:
            if entry["dnf"]:
                continue

            # DNF chance
            dnf_chance = (100 - entry["car"]["reliability"]) * 0.00004
            if random.random() < dnf_chance:
                entry["dnf"] = True
                entry["status"] = "dnf"
                entry["dnf_reason"] = random.choice([
                    "Engine failure", "Gearbox issue", "Hydraulics problem",
                    "Brake failure", "Suspension failure"
                ])
                self.race_events.append({
                    "lap": self.current_lap, "event_type": "dnf",
                    "description": f"{entry['driver_name']} OUT - {entry['dnf_reason']}!"
                })

                if random.random() < 0.3 and not self.safety_car:
                    self.safety_car = True
                    self.safety_car_laps = random.randint(3, 5)
                    self.race_events.append({"lap": self.current_lap, "event_type": "safety_car", "description": "SAFETY CAR DEPLOYED!"})
                continue

            lap_time = self._calculate_lap_time(entry, self.weather)
            if self.safety_car:
                lap_time = track["base_lap_time"] + 10

            entry["total_time"] += lap_time

            # Tire degradation
            base_deg = entry["tire"].DEGRADATION_RATES.get(entry["tire"].compound, 1.8) * track["tire_degradation"]
            car_cooling = max(0.4, 1.5 - (entry["car"]["tire_cooling"] / 100))
            tire_mgmt = max(0.4, 1.0 - (entry["driver"]["stats"]["tire_management"] / 166.67))
            final_deg = base_deg * car_cooling * tire_mgmt
            entry["tire"].wear = min(100, entry["tire"].wear + final_deg)

        # Overtakes
        if not self.safety_car:
            active = [e for e in self.race_entries if not e["dnf"]]
            active.sort(key=lambda e: e["total_time"])

            for i in range(1, len(active)):
                attacker = active[i]
                defender = active[i - 1]
                gap = attacker["total_time"] - defender["total_time"]

                if gap < 1.5:
                    success, aggressive = self._attempt_overtake(attacker, defender)
                    if success:
                        desc = f"{attacker['driver_name']} makes an AGGRESSIVE move on {defender['driver_name']}!" if aggressive else f"{attacker['driver_name']} overtakes {defender['driver_name']}!"
                        self.race_events.append({"lap": self.current_lap, "event_type": "overtake", "description": desc})

        # AI pit stops
        self._simulate_ai_pits()

        # Update positions
        active = [e for e in self.race_entries if not e["dnf"]]
        active.sort(key=lambda e: e["total_time"])

        for i, entry in enumerate(active):
            entry["position"] = i + 1
            entry["gap"] = "Leader" if i == 0 else f"+{entry['total_time'] - active[0]['total_time']:.1f}s"

        # Check if any player needs pit decision (multiplayer sync)
        if self.current_lap < self.total_laps:
            self._check_all_pit_decisions()

        if self.current_lap >= self.total_laps:
            self._finish_race()

    def _attempt_overtake(self, attacker: Dict, defender: Dict) -> Tuple[bool, bool]:
        """Attempt overtake."""
        if attacker["dnf"] or defender["dnf"]:
            return False, False

        track = self._tracks[self.current_race - 1]
        att = attacker["driver"]
        deff = defender["driver"]

        pace_diff = att["stats"]["pace"] - deff["stats"]["pace"]
        skill_diff = att["stats"]["overtaking"] - deff["stats"]["defending"]
        car_diff = calc_car_overall(attacker["car"]) - calc_car_overall(defender["car"])
        tire_diff = attacker["tire"].performance - defender["tire"].performance
        track_factor = (10 - track["overtaking_difficulty"]) * 2

        probability = 20 + pace_diff * 0.3 + skill_diff * 0.2 + car_diff * 0.1 + tire_diff * 20 + track_factor

        success = random.random() * 100 < probability
        aggressive = success and probability < 40 and random.random() < 0.3
        return success, aggressive

    def _simulate_ai_pits(self):
        """AI pit stop decisions."""
        track = self._tracks[self.current_race - 1]

        for entry in self.race_entries:
            if entry["dnf"] or entry["is_player_driver"]:
                continue

            should_pit = False
            new_compound = "medium"

            if self.weather == Weather.HEAVY_RAIN and entry["tire"].compound not in ["wet"]:
                should_pit = True
                new_compound = "wet"
            elif self.weather == Weather.LIGHT_RAIN and entry["tire"].compound not in ["intermediate", "wet"]:
                should_pit = True
                new_compound = "intermediate"
            elif self.weather == Weather.DRY and entry["tire"].compound in ["intermediate", "wet"]:
                should_pit = True
                new_compound = "medium"
            elif entry["tire"].wear > 70:
                should_pit = True
                laps_remaining = self.total_laps - self.current_lap
                if laps_remaining > 25:
                    new_compound = "hard"
                elif laps_remaining > 15:
                    new_compound = "medium"
                else:
                    new_compound = "soft"

            if should_pit:
                entry["tire"] = TireState(new_compound)
                entry["total_time"] += track["pit_loss_time"]
                entry["pit_stops"] += 1
                self.race_events.append({
                    "lap": self.current_lap, "event_type": "pit_stop",
                    "description": f"{entry['driver_name']} pits for {new_compound.upper()} tires"
                })

    def pit_player_driver(self, player_id: str, driver_id: str, compound: str) -> bool:
        """Pit a player's driver."""
        if self.phase != GamePhase.RACE_IN_PROGRESS:
            return False

        track = self._tracks[self.current_race - 1]

        for entry in self.race_entries:
            if entry["player_id"] == player_id and entry["driver"]["id"] == driver_id and not entry["dnf"]:
                entry["tire"] = TireState(compound)
                entry["total_time"] += track["pit_loss_time"]
                entry["pit_stops"] += 1
                self.race_events.append({
                    "lap": self.current_lap, "event_type": "pit_stop",
                    "description": f"{entry['driver_name']} pits for {compound.upper()} tires"
                })
                return True
        return False

    def simulate_full_race(self, player_id: str = None):
        """Simulate entire race."""
        while self.phase == GamePhase.RACE_IN_PROGRESS:
            self.simulate_race_lap(player_id)

    def _finish_race(self):
        """Finish race and award points."""
        self.race_finished = True
        self.phase = GamePhase.RACE_RESULTS

        active = [e for e in self.race_entries if not e["dnf"]]
        active.sort(key=lambda e: e["total_time"])

        for i, entry in enumerate(active):
            pos = i + 1
            entry["position"] = pos
            entry["status"] = "finished"

            pts = POINTS_SYSTEM.get(pos, 0)

            # Update driver standings
            for ds in self._driver_standings:
                if ds["driver_name"] == entry["driver_name"]:
                    ds["points"] += pts
                    if pos == 1:
                        ds["wins"] += 1
                    if pos <= 3:
                        ds["podiums"] += 1
                    break

            # Update constructor standings
            for cs in self._constructor_standings:
                if cs["team_name"] == entry["team_name"]:
                    cs["points"] += pts
                    if pos == 1:
                        cs["wins"] += 1
                    break

            # Update player team
            if entry["player_id"]:
                team = self.player_teams.get(entry["player_id"])
                if team:
                    team["season_points"] += pts
                    if pos == 1:
                        team["race_wins"] += 1

                    # Prize money
                    prize = RACE_PRIZE_MONEY.get(pos, 0.25)
                    team["budget"] += prize

                    # Sponsor objective
                    sponsor = team.get("sponsor")
                    if sponsor:
                        sponsor["races_completed"] += 1
                        obj_met = self._check_sponsor_objective(sponsor, pos)
                        if obj_met:
                            sponsor["objectives_met"] += 1
                            team["budget"] += sponsor["payment_per_race"]

                    # Update driver
                    for d in team["drivers"]:
                        if d["name"] == entry["driver_name"]:
                            d["season_points"] += pts
                            if pos == 1:
                                d["race_wins"] += 1
                                d["win_streak"] += 1
                                d["morale"] = min(100, d["morale"] + 15)
                            else:
                                d["win_streak"] = 0
                            if pos <= 3:
                                d["podiums"] += 1
                                d["podium_streak"] += 1
                                d["morale"] = min(100, d["morale"] + 10)
                            else:
                                d["podium_streak"] = 0
                            if pos > 10:
                                d["no_points_streak"] += 1
                                d["morale"] = max(0, d["morale"] - 3)
                            else:
                                d["no_points_streak"] = 0
                            break

        # Handle DNFs
        for entry in self.race_entries:
            if entry["dnf"] and entry["player_id"]:
                team = self.player_teams.get(entry["player_id"])
                if team:
                    for d in team["drivers"]:
                        if d["name"] == entry["driver_name"]:
                            d["dnfs"] += 1
                            d["dnf_streak"] += 1
                            d["morale"] = max(0, d["morale"] - 8)
                            break

        # Sort standings
        self._driver_standings.sort(key=lambda x: (x["points"], x["wins"]), reverse=True)
        self._constructor_standings.sort(key=lambda x: (x["points"], x["wins"]), reverse=True)

        for i, ds in enumerate(self._driver_standings):
            ds["position"] = i + 1
        for i, cs in enumerate(self._constructor_standings):
            cs["position"] = i + 1

        # Process developments
        for pid in self.players:
            self._process_developments(pid)

        # Update player team reputation based on results
        self._update_team_reputations()

        # AI teams get prize money and upgrades
        self._process_ai_teams_race_end()

        # Rotate turn order for fairness
        self._rotate_turn_order()

    def _check_sponsor_objective(self, sponsor: Dict, best_finish: int) -> bool:
        """Check if sponsor objective was met."""
        obj_type = sponsor.get("objective_type", "")
        target = sponsor.get("objective_target", 99)

        if obj_type == "finish_position":
            return best_finish <= target
        elif obj_type == "points_finish":
            return best_finish <= 10
        elif obj_type == "podium":
            return best_finish <= 3
        elif obj_type == "win":
            return best_finish == 1
        return False

    def _update_team_reputations(self):
        """Update team reputations based on race results."""
        for pid, team in self.player_teams.items():
            # Find best finish this race
            best_finish = 99
            for entry in self.race_entries:
                if entry["player_id"] == pid and not entry["dnf"]:
                    best_finish = min(best_finish, entry["position"])

            # Reputation changes based on performance
            rep_change = 0
            if best_finish == 1:
                rep_change = 5  # Win = big reputation boost
            elif best_finish <= 3:
                rep_change = 3  # Podium
            elif best_finish <= 6:
                rep_change = 2  # Strong points
            elif best_finish <= 10:
                rep_change = 1  # Points finish
            elif best_finish <= 15:
                rep_change = 0  # Mid-pack
            else:
                rep_change = -1  # Poor finish

            team["reputation"] = max(10, min(100, team.get("reputation", 20) + rep_change))

            # Also update podiums counter
            for entry in self.race_entries:
                if entry["player_id"] == pid and not entry["dnf"] and entry["position"] <= 3:
                    team["podiums"] = team.get("podiums", 0) + 1

    def _process_ai_teams_race_end(self):
        """Process AI teams after a race - prize money and upgrades."""
        # Award prize money to AI teams
        for entry in self.race_entries:
            if not entry["player_id"] and not entry["dnf"]:
                team_name = entry["team_name"]
                if team_name in self._ai_teams:
                    ai_team = self._ai_teams[team_name]
                    pos = entry["position"]

                    # Prize money
                    prize = RACE_PRIZE_MONEY.get(pos, 0.25)
                    ai_team["budget"] += prize
                    ai_team["upgrade_budget"] += prize * 0.5  # Half goes to upgrade fund

                    # Track wins and podiums
                    if pos == 1:
                        ai_team["race_wins"] += 1
                    if pos <= 3:
                        ai_team["podiums"] = ai_team.get("podiums", 0) + 1

                    # Update season points
                    pts = POINTS_SYSTEM.get(pos, 0)
                    ai_team["season_points"] += pts

        # AI teams decide to upgrade (every few races or when they have enough budget)
        if self.current_race % 3 == 0:  # Every 3 races
            self._ai_teams_upgrade()

    def _ai_teams_upgrade(self):
        """AI teams spend their upgrade budgets."""
        for team_name, ai_team in self._ai_teams.items():
            upgrade_budget = ai_team.get("upgrade_budget", 0)

            # Only upgrade if enough budget
            if upgrade_budget < 5:
                continue

            car = ai_team["car"]

            # Find weakest stat to upgrade
            stats = ["downforce", "aero_efficiency", "chassis", "power_unit", "reliability", "tire_cooling"]
            weakest_stat = min(stats, key=lambda s: car[s])
            current_value = car[weakest_stat]

            # Get upgrade cost
            cost = get_upgrade_cost(current_value)

            # Perform upgrades while affordable
            upgrades_done = 0
            while upgrade_budget >= cost and current_value < 98 and upgrades_done < 3:
                car[weakest_stat] = current_value + 1
                upgrade_budget -= cost
                current_value = car[weakest_stat]
                cost = get_upgrade_cost(current_value)
                upgrades_done += 1

                # Maybe switch to another weak stat
                if upgrades_done >= 2:
                    weakest_stat = min(stats, key=lambda s: car[s])
                    current_value = car[weakest_stat]
                    cost = get_upgrade_cost(current_value)

            ai_team["upgrade_budget"] = upgrade_budget

            # Update AI team reputation based on car quality
            ai_team["reputation"] = calc_car_overall(car)

    def _process_driver_growth(self):
        """Process driver stat growth/decline at season end."""
        for driver in self._all_drivers:
            age = driver["age"]
            overall = driver["overall"]
            stats = driver["stats"]

            # Determine growth potential based on age
            if age <= 22:
                # Young talents - high growth potential
                growth_chance = 0.9
                max_growth = 4
                decline_chance = 0.05
            elif age <= 25:
                # Developing - good growth
                growth_chance = 0.75
                max_growth = 3
                decline_chance = 0.1
            elif age <= 28:
                # Prime - moderate growth
                growth_chance = 0.5
                max_growth = 2
                decline_chance = 0.15
            elif age <= 32:
                # Late prime - stable/slight decline
                growth_chance = 0.25
                max_growth = 1
                decline_chance = 0.3
            elif age <= 35:
                # Veteran - mostly decline
                growth_chance = 0.1
                max_growth = 1
                decline_chance = 0.5
            else:
                # Old - decline
                growth_chance = 0.05
                max_growth = 1
                decline_chance = 0.7

            # Performance modifier - good results increase growth
            performance_mod = 0
            if driver.get("race_wins", 0) > 0:
                performance_mod = 0.2
            elif driver.get("podiums", 0) > 0:
                performance_mod = 0.1
            elif driver.get("season_points", 0) > 30:
                performance_mod = 0.05

            growth_chance = min(1.0, growth_chance + performance_mod)

            # Apply growth or decline to each stat
            stat_names = ["pace", "overtaking", "defending", "consistency", "tire_management", "wet_skill"]
            for stat_name in stat_names:
                current = stats[stat_name]

                if random.random() < growth_chance:
                    # Growth
                    growth = random.randint(1, max_growth)
                    # Limit growth near ceiling
                    if current >= 90:
                        growth = min(growth, 1)
                    if current >= 95:
                        growth = 0
                    stats[stat_name] = min(99, current + growth)
                elif random.random() < decline_chance:
                    # Decline
                    decline = random.randint(1, 2)
                    stats[stat_name] = max(40, current - decline)

            # Update overall
            driver["overall"] = calc_overall(stats)

            # Age the driver
            driver["age"] += 1

            # Update potential based on new age/overall
            driver["potential"] = calc_potential(driver["age"], driver["overall"])

            # Update minimum prestige requirement
            driver["min_team_prestige"] = self._calculate_driver_min_prestige(driver["overall"], driver["age"])

            # Reset season stats
            driver["season_points"] = 0
            driver["race_wins"] = 0
            driver["podiums"] = 0
            driver["dnfs"] = 0

            # Contract handling
            if driver.get("contract_years", 0) > 0:
                driver["contract_years"] -= 1
                if driver["contract_years"] <= 0:
                    driver["is_free_agent"] = True

    def advance_to_next_race(self, player_id: str) -> bool:
        """Move to next race."""
        if self.phase != GamePhase.RACE_RESULTS:
            return False

        if len(self.players) == 2 and not self.all_players_ready():
            self.mark_ready(player_id, True)
            if not self.all_players_ready():
                return True

        self.reset_ready()
        self.current_race += 1

        if self.current_race > len(self._tracks):
            self.phase = GamePhase.SEASON_END
            self._end_season()
        else:
            self.phase = GamePhase.MAIN_MENU
            self.qualifying_results = []
            self.race_entries = []
            self.race_events = []
            self.player_tire_selections = {}

        return True

    def _end_season(self):
        """End of season processing."""
        # Award prize money to player teams
        for pid, team in self.player_teams.items():
            pos = next((cs["position"] for cs in self._constructor_standings if cs["team_name"] == team["name"]), 11)
            prize = SEASON_PRIZE_MONEY.get(pos, 25)
            team["budget"] += prize

            # Sponsor bonus
            sponsor = team.get("sponsor")
            if sponsor and sponsor.get("success_rate", 0) >= 80:
                team["budget"] += sponsor["season_bonus"]
                self._add_inbox_message(pid, "Sponsor Bonus",
                    f"Congratulations! You've met your sponsor objectives. Bonus: ${sponsor['season_bonus']}M!",
                    MessageType.ACHIEVEMENT, MessagePriority.IMPORTANT)

            # Increment seasons completed
            team["seasons_completed"] = team.get("seasons_completed", 0) + 1

            # Generate season summary message
            team_pos = pos
            driver_names = [d["name"] for d in team["drivers"]]
            self._add_inbox_message(pid, f"Season {self.current_season} Complete",
                f"Your team finished P{team_pos} in the Constructors' Championship!\n\n"
                f"Drivers: {', '.join(driver_names)}\n"
                f"Season Prize: ${prize}M\n"
                f"Your car and reputation have improved. Better drivers may now be interested!",
                MessageType.TEAM_UPDATE, MessagePriority.IMPORTANT)

        # Award prize money to AI teams
        for cs in self._constructor_standings:
            team_name = cs["team_name"]
            if team_name in self._ai_teams:
                pos = cs["position"]
                prize = SEASON_PRIZE_MONEY.get(pos, 25)
                self._ai_teams[team_name]["budget"] += prize

        # Process driver growth/decline for ALL drivers
        self._process_driver_growth()

        # Process AI team upgrades at season end (big upgrade session)
        for _ in range(3):  # Multiple upgrade rounds
            self._ai_teams_upgrade()

        # Go to transfer window phase
        self.phase = GamePhase.TRANSFER_WINDOW
        self.reset_ready()

        # Notify players about transfer window
        for pid in self.players:
            team = self.player_teams[pid]
            prestige = self.get_team_prestige(pid)
            self._add_inbox_message(pid, "Transfer Window Open",
                f"The transfer window is now open! Your team prestige is {prestige}/100.\n\n"
                f"You can now sign new drivers. Higher prestige attracts better talent.\n"
                f"Budget available: ${team['budget']:.1f}M",
                MessageType.TEAM_UPDATE, MessagePriority.URGENT)

    def skip_transfer_window(self, player_id: str) -> bool:
        """Skip the transfer window and start next season."""
        if self.phase != GamePhase.TRANSFER_WINDOW:
            return False

        if len(self.players) == 2 and not self.all_players_ready():
            self.mark_ready(player_id, True)
            if not self.all_players_ready():
                return True  # Waiting for other player

        self._start_new_season()
        return True

    def sign_driver_transfer(self, player_id: str, driver_id: str, salary: float, years: int) -> bool:
        """Sign a driver during transfer window (can replace existing driver)."""
        if self.phase != GamePhase.TRANSFER_WINDOW:
            return False

        if player_id not in self.player_teams:
            return False

        team = self.player_teams[player_id]
        driver = next((d for d in self._all_drivers if d["id"] == driver_id), None)
        if not driver:
            return False

        # Check if driver is interested
        team_prestige = self.get_team_prestige(player_id)
        min_prestige = driver.get("min_team_prestige", 0)
        if team_prestige < min_prestige:
            return False

        # Check affordability
        if driver["market_value"] > team["budget"]:
            return False

        # If team already has 2 drivers, must release one first
        if len(team["drivers"]) >= 2:
            return False

        # Sign the driver
        team["budget"] -= driver["market_value"]
        driver["team_name"] = team["name"]
        driver["player_id"] = player_id
        driver["contract_years"] = years
        driver["is_free_agent"] = False
        team["drivers"].append(driver)

        self._add_inbox_message(player_id, "Driver Signed",
            f"{driver['name']} has joined your team! Contract: {years} years at ${salary}M/year.",
            MessageType.TEAM_UPDATE)

        return True

    def release_driver_transfer(self, player_id: str, driver_id: str) -> bool:
        """Release a driver during transfer window."""
        if self.phase != GamePhase.TRANSFER_WINDOW:
            return False

        if player_id not in self.player_teams:
            return False

        team = self.player_teams[player_id]

        # Can't release if only 1 driver
        if len(team["drivers"]) <= 1:
            return False

        driver = next((d for d in team["drivers"] if d["id"] == driver_id), None)
        if not driver:
            return False

        # Release the driver
        team["drivers"].remove(driver)
        driver["team_name"] = None
        driver["player_id"] = None
        driver["is_free_agent"] = True

        self._add_inbox_message(player_id, "Driver Released",
            f"{driver['name']} has been released from your team. They are now a free agent.",
            MessageType.TEAM_UPDATE)

        return True

    def _start_new_season(self):
        """Start a new season after transfer window."""
        self.current_season += 1
        self.current_race = 1
        self.phase = GamePhase.MAIN_MENU
        self.reset_ready()

        # Reset season stats
        for team in self.player_teams.values():
            team["season_points"] = 0
            team["race_wins"] = 0
            team["podiums"] = 0

        for ai_team in self._ai_teams.values():
            ai_team["season_points"] = 0
            ai_team["race_wins"] = 0
            ai_team["podiums"] = 0

        # Re-initialize standings
        self._initialize_standings()

        # Clear race state
        self.qualifying_results = []
        self.race_entries = []
        self.race_events = []
        self.player_tire_selections = {}

        # Notify players
        for pid in self.players:
            self._add_inbox_message(pid, f"Season {self.current_season} Begins",
                f"Welcome to Season {self.current_season}! The championship starts fresh.\n"
                f"Good luck this season!",
                MessageType.TEAM_UPDATE, MessagePriority.IMPORTANT)

    def _initialize_standings(self):
        """Initialize championship standings."""
        self._driver_standings = []
        self._constructor_standings = []

        all_drivers = []
        for team in self.player_teams.values():
            for d in team["drivers"]:
                all_drivers.append((d, team["name"], team.get("player_id")))

        for d in self._all_drivers:
            if d["team_name"] and d["player_id"] is None:
                in_player = any(d in t["drivers"] for t in self.player_teams.values())
                if not in_player:
                    all_drivers.append((d, d["team_name"], None))

        pos = 1
        for driver, team_name, pid in all_drivers:
            self._driver_standings.append({
                "position": pos,
                "driver_name": driver["name"],
                "team_name": team_name,
                "points": 0,
                "wins": 0,
                "podiums": 0,
                "is_player_driver": pid is not None,
                "player_id": pid
            })
            pos += 1

        teams = {}
        for _, team_name, pid in all_drivers:
            if team_name not in teams:
                teams[team_name] = pid

        pos = 1
        for team_name, pid in teams.items():
            self._constructor_standings.append({
                "position": pos,
                "team_name": team_name,
                "points": 0,
                "wins": 0,
                "is_player_team": pid is not None,
                "player_id": pid
            })
            pos += 1

    # ==================== INBOX ====================

    def _add_inbox_message(self, player_id: str, subject: str, body: str, msg_type: MessageType, priority: MessagePriority = MessagePriority.NORMAL):
        """Add inbox message for a player."""
        if player_id not in self.inboxes:
            self.inboxes[player_id] = []

        self.inboxes[player_id].insert(0, {
            "id": str(uuid.uuid4())[:8],
            "type": msg_type.value if isinstance(msg_type, MessageType) else msg_type,
            "priority": priority.value if isinstance(priority, MessagePriority) else priority,
            "subject": subject,
            "body": body,
            "timestamp": datetime.utcnow().isoformat(),
            "is_read": False,
            "sender": "Team Principal"
        })

        # Keep only last 50 messages
        self.inboxes[player_id] = self.inboxes[player_id][:50]

    def _add_inbox_message_all(self, subject: str, body: str, msg_type: MessageType, priority: MessagePriority = MessagePriority.NORMAL):
        """Add inbox message to all players."""
        for pid in self.players:
            self._add_inbox_message(pid, subject, body, msg_type, priority)

    def mark_message_read(self, player_id: str, message_id: str) -> bool:
        """Mark a message as read."""
        if player_id not in self.inboxes:
            return False
        for msg in self.inboxes[player_id]:
            if msg["id"] == message_id:
                msg["is_read"] = True
                return True
        return False

    # ==================== STATE RESPONSE ====================

    def get_state_response(self, player_id: str) -> GameStateResponse:
        """Generate state response for a specific player."""
        is_multiplayer = len(self.players) >= 2

        # Player states
        player_states = [
            PlayerState(
                player_id=p["player_id"],
                username=p["username"],
                team_name=p["team_name"],
                is_ready=self.players_ready.get(p["player_id"], False),
                has_set_team_name=p.get("has_set_team_name", False),
                has_selected_sponsor=p["has_selected_sponsor"],
                has_selected_tires=p.get("has_selected_tires", False),
                drivers_signed=p["drivers_signed"]
            )
            for p in self.players.values()
        ]

        # Turn info
        turn_info = None
        is_your_turn = True
        if is_multiplayer:
            current_pid = self._get_current_player_id()
            current_player = self.players.get(current_pid, {})
            action = self._get_action_required()
            is_your_turn = current_pid == player_id or self.phase not in [GamePhase.TEAM_SETUP]

            turn_info = TurnInfo(
                current_player_id=current_pid,
                current_player_username=current_player.get("username", "Unknown"),
                action_required=action,
                waiting_for=[pid for pid, ready in self.players_ready.items() if not ready],
                turn_order=self.player_order
            )

        # Player team
        player_team = None
        team_data = self.player_teams.get(player_id)
        if team_data:
            player_team = self._build_team_info(team_data)

        # Opponent team
        opponent_team = None
        if is_multiplayer:
            other_pid = next((pid for pid in self.players if pid != player_id), None)
            if other_pid:
                other_data = self.player_teams.get(other_pid)
                if other_data:
                    opponent_team = self._build_team_info(other_data)

        # Current track
        current_track = None
        if 1 <= self.current_race <= len(self._tracks):
            t = self._tracks[self.current_race - 1]
            current_track = TrackInfo(
                id=str(self.current_race - 1),
                name=t["name"], country=t["country"], city=t["city"],
                laps=t["laps"], track_type=t.get("track_type", "CIRCUIT"),
                tire_degradation=t.get("tire_degradation", 1.0),
                overtaking_difficulty=t.get("overtaking_difficulty", 5) / 10.0
            )

        # Qualifying results
        qual_results = [
            QualifyingResult(
                position=q["position"], driver_name=q["driver_name"],
                team_name=q["team_name"], lap_time=q["lap_time"],
                is_player_driver=q.get("is_player_driver", False),
                player_id=q.get("player_id")
            )
            for q in self.qualifying_results
        ]

        # Race state
        race_state = None
        if self.phase in [GamePhase.RACE_IN_PROGRESS, GamePhase.RACE_RESULTS]:
            positions = []
            for entry in sorted(self.race_entries, key=lambda e: e["position"] if not e["dnf"] else 999):
                positions.append(RaceEntry(
                    position=entry["position"],
                    driver_name=entry["driver_name"],
                    team_name=entry["team_name"],
                    gap=entry["gap"],
                    tire=TireCompound(entry["tire"].compound),
                    tire_wear=int(entry["tire"].wear),
                    pit_stops=entry["pit_stops"],
                    status=entry["status"],
                    is_player_driver=entry.get("is_player_driver", False),
                    player_id=entry.get("player_id")
                ))

            # Build pit decision status for multiplayer
            pit_status = None
            if len(self.players) >= 2:
                pit_info = self.get_pit_decision_status(player_id)
                pit_status = PitDecisionStatus(
                    paused_for_pits=pit_info["paused_for_pits"],
                    my_drivers_needing_pit=pit_info["my_drivers_needing_pit"],
                    i_need_to_decide=pit_info["i_need_to_decide"],
                    i_have_confirmed=pit_info["i_have_confirmed"],
                    waiting_for_players=pit_info["waiting_for_players"],
                    all_confirmed=pit_info["all_confirmed"]
                )

            race_state = RaceState(
                current_lap=self.current_lap,
                total_laps=self.total_laps,
                positions=positions,
                events=[RaceEvent(lap=e["lap"], event_type=e["event_type"], description=e["description"]) for e in self.race_events[-30:]],
                weather=self.weather.value,
                safety_car=self.safety_car,
                safety_car_laps=self.safety_car_laps,
                pit_decision_status=pit_status
            )

        # Standings
        driver_standings = [
            DriverStanding(
                position=ds["position"], driver_name=ds["driver_name"],
                team_name=ds["team_name"], points=ds["points"],
                wins=ds["wins"], podiums=ds.get("podiums", 0),
                is_player_driver=ds.get("is_player_driver", False),
                player_id=ds.get("player_id")
            )
            for ds in self._driver_standings
        ]

        constructor_standings = [
            ConstructorStanding(
                position=cs["position"], team_name=cs["team_name"],
                points=cs["points"], wins=cs["wins"],
                is_player_team=cs.get("is_player_team", False),
                player_id=cs.get("player_id")
            )
            for cs in self._constructor_standings
        ]

        # Calendar
        calendar = [
            SeasonCalendarEntry(
                race_number=i + 1,
                track=TrackInfo(
                    id=str(i), name=t["name"], country=t["country"],
                    city=t["city"], laps=t["laps"],
                    track_type=t.get("track_type", "CIRCUIT"),
                    tire_degradation=t.get("tire_degradation", 1.0),
                    overtaking_difficulty=t.get("overtaking_difficulty", 5) / 10.0
                ),
                is_completed=i + 1 < self.current_race,
                is_current=i + 1 == self.current_race
            )
            for i, t in enumerate(self._tracks)
        ]

        # Market drivers
        market_drivers = []
        if self.phase in [GamePhase.TEAM_SETUP, GamePhase.TRANSFER_WINDOW]:
            for d in self.get_available_drivers(player_id):
                market_drivers.append(MarketDriver(
                    id=d["id"], name=d["name"], age=d["age"],
                    nationality=d["nationality"],
                    stats=DriverStats(**d["stats"]),
                    market_value=d["market_value"],
                    salary=d["salary"],
                    potential=d["potential"],
                    current_team=d.get("original_team"),
                    is_free_agent=d.get("is_free_agent", True),
                    min_team_prestige=d.get("min_team_prestige", 0),
                    interested=d.get("interested", True),
                    interest_reason=d.get("interest_reason", "")
                ))

        # Available sponsors
        available_sponsors = []
        if self.phase == GamePhase.SPONSOR_SELECTION and player_id in self.available_sponsors:
            for s in self.available_sponsors[player_id]:
                available_sponsors.append(SponsorInfo(
                    id=s["id"], name=s["name"],
                    tier=SponsorTier(s["tier"]),
                    payment_per_race=s["payment_per_race"],
                    season_bonus=s["season_bonus"],
                    objective=SponsorObjective(
                        type=s["objective_type"],
                        target=s["objective_target"],
                        description=s["objective_description"]
                    )
                ))

        # Upgrade options
        upgrade_options = [
            UpgradeOption(**opt) for opt in self.get_upgrade_options(player_id)
        ] if self.phase == GamePhase.MAIN_MENU else []

        # Development tree
        dev_tree = None
        if team_data and team_data.get("development_tree"):
            tree = team_data["development_tree"]
            dev_tree = DevelopmentTree(
                nodes=[DevelopmentNode(**n) for n in tree["nodes"]],
                active_developments=tree["active_developments"],
                completed_developments=tree["completed_developments"],
                branch_choices=tree["branch_choices"]
            )

        # Inbox
        inbox = [
            InboxMessage(
                id=m["id"],
                type=MessageType(m["type"]) if m["type"] in [mt.value for mt in MessageType] else MessageType.TEAM_UPDATE,
                priority=MessagePriority(m["priority"]) if m["priority"] in [mp.value for mp in MessagePriority] else MessagePriority.NORMAL,
                subject=m["subject"],
                body=m["body"],
                timestamp=datetime.fromisoformat(m["timestamp"]) if isinstance(m["timestamp"], str) else m["timestamp"],
                is_read=m["is_read"],
                sender=m.get("sender", "System")
            )
            for m in self.inboxes.get(player_id, [])[:15]
        ]

        min_cost = self.get_min_driver_cost(player_id) if self.phase == GamePhase.TEAM_SETUP else 0
        drivers_needed = 2 - len(team_data["drivers"]) if team_data else 2

        return GameStateResponse(
            game_id=self.game_id,
            phase=self.phase,
            current_season=self.current_season,
            current_race=self.current_race,
            total_races=self.total_races,
            is_multiplayer=is_multiplayer,
            player_count=len(self.players),
            players=player_states,
            turn_info=turn_info,
            your_player_id=player_id,
            is_your_turn=is_your_turn,
            player_team=player_team,
            opponent_team=opponent_team,
            current_track=current_track,
            qualifying_results=qual_results,
            race_state=race_state,
            driver_standings=driver_standings,
            constructor_standings=constructor_standings,
            calendar=calendar,
            available_sponsors=available_sponsors if available_sponsors else None,
            market_drivers=market_drivers if market_drivers else None,
            upgrade_options=upgrade_options if upgrade_options else None,
            development_tree=dev_tree,
            inbox=inbox if inbox else None,
            min_driver_cost=min_cost,
            drivers_needed=drivers_needed
        )

    def _build_team_info(self, team_data: Dict) -> TeamInfo:
        """Build TeamInfo from internal data."""
        drivers = []
        for d in team_data.get("drivers", []):
            contract = None
            if d.get("contract_years"):
                contract = DriverContract(
                    years_remaining=d["contract_years"],
                    salary=d["salary"],
                    is_number_one=d.get("is_number_one", False)
                )
            drivers.append(DriverInfo(
                id=d["id"], name=d["name"], age=d["age"],
                nationality=d["nationality"],
                stats=DriverStats(**d["stats"]),
                salary=d["salary"], market_value=d["market_value"],
                potential=d["potential"], team_name=d.get("team_name"),
                season_points=d.get("season_points", 0),
                race_wins=d.get("race_wins", 0),
                podiums=d.get("podiums", 0),
                dnfs=d.get("dnfs", 0),
                morale=d.get("morale", 75),
                confidence=d.get("confidence", 75),
                contract=contract,
                is_player_driver=d.get("player_id") is not None,
                player_id=d.get("player_id")
            ))

        car = team_data.get("car", {})
        sponsor = team_data.get("sponsor")
        sponsor_info = None
        if sponsor:
            sponsor_info = SponsorInfo(
                id=sponsor.get("id", ""),
                name=sponsor.get("name", ""),
                tier=SponsorTier(sponsor.get("tier", "bronze")),
                payment_per_race=sponsor.get("payment_per_race", 0),
                season_bonus=sponsor.get("season_bonus", 0),
                objective=SponsorObjective(
                    type=sponsor.get("objective_type", "finish_position"),
                    target=sponsor.get("objective_target", 20),
                    description=sponsor.get("objective_description", "")
                ),
                races_completed=sponsor.get("races_completed", 0),
                objectives_met=sponsor.get("objectives_met", 0)
            )

        return TeamInfo(
            id=team_data.get("id", ""),
            name=team_data.get("name", "Unknown"),
            budget=team_data.get("budget", 0),
            car=CarStats(**car),
            drivers=drivers,
            season_points=team_data.get("season_points", 0),
            race_wins=team_data.get("race_wins", 0),
            is_player_team=True,
            player_id=team_data.get("player_id"),
            player_username=team_data.get("player_username"),
            sponsor=sponsor_info
        )

    def _get_action_required(self) -> str:
        """Get description of required action."""
        if self.phase == GamePhase.WAITING_FOR_PLAYERS:
            return "Waiting for another player to join"
        elif self.phase == GamePhase.SPONSOR_SELECTION:
            return "Select your sponsor"
        elif self.phase == GamePhase.TEAM_SETUP:
            return "Sign a driver"
        elif self.phase == GamePhase.MAIN_MENU:
            return "Start race weekend or manage team"
        elif self.phase == GamePhase.QUALIFYING:
            return "Review qualifying results"
        elif self.phase == GamePhase.TIRE_SELECTION:
            return "Select starting tires"
        elif self.phase == GamePhase.RACE_IN_PROGRESS:
            return "Manage race strategy"
        elif self.phase == GamePhase.RACE_RESULTS:
            return "Review race results"
        elif self.phase == GamePhase.SEASON_END:
            return "Season complete"
        return "Continue"


# ==================== GAME STATE MANAGER ====================

class GameStateManager:
    """Manages all active multiplayer game states."""

    def __init__(self):
        self._games: Dict[str, MultiplayerGameState] = {}

    def create_game(self, game_id: str, player_id: str = None, username: str = None) -> MultiplayerGameState:
        """Create a new game state and optionally add the first player."""
        game = MultiplayerGameState(game_id)
        if player_id and username:
            game.add_player(player_id, username)
        self._games[game_id] = game
        return game

    def get_game(self, game_id: str) -> Optional[MultiplayerGameState]:
        """Get an existing game state."""
        return self._games.get(game_id)

    def delete_game(self, game_id: str) -> bool:
        """Delete a game state."""
        if game_id in self._games:
            del self._games[game_id]
            return True
        return False

    def add_player_to_game(self, game_id: str, player_id: str, username: str) -> Optional[MultiplayerGameState]:
        """Add a player to a game, creating it if needed."""
        game = self.get_game(game_id)
        if not game:
            game = self.create_game(game_id)
        game.add_player(player_id, username)
        return game


# Global game state manager
game_state_manager = GameStateManager()
