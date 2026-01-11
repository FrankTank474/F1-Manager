"""Game state models for web version - Full multiplayer support."""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class GamePhase(str, Enum):
    """Current phase of the game."""
    WAITING_FOR_PLAYERS = "waiting_for_players"  # Waiting for 2nd player
    TEAM_NAME_SELECTION = "team_name_selection"  # Choose team name
    SPONSOR_SELECTION = "sponsor_selection"  # Each player selects sponsor
    TEAM_SETUP = "team_setup"  # Initial driver selection (alternating turns)
    MAIN_MENU = "main_menu"  # Between races - team management
    RACE_WEEKEND = "race_weekend"  # During a race weekend
    QUALIFYING = "qualifying"
    TIRE_SELECTION = "tire_selection"
    RACE_IN_PROGRESS = "race_in_progress"
    RACE_RESULTS = "race_results"
    SEASON_END = "season_end"
    TRANSFER_WINDOW = "transfer_window"  # End of season driver transfers


class TireCompound(str, Enum):
    SOFT = "soft"
    MEDIUM = "medium"
    HARD = "hard"
    INTERMEDIATE = "intermediate"
    WET = "wet"


class SponsorTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class MessagePriority(str, Enum):
    URGENT = "urgent"
    IMPORTANT = "important"
    NORMAL = "normal"
    INFO = "info"


class MessageType(str, Enum):
    DRIVER_COMPLAINT = "driver_complaint"
    SPONSOR_WARNING = "sponsor_warning"
    RIVAL_NEWS = "rival_news"
    TRANSFER_RUMOR = "transfer_rumor"
    TEAM_UPDATE = "team_update"
    CONTRACT_ALERT = "contract_alert"
    MEDIA = "media"
    ACHIEVEMENT = "achievement"


class ContractStatus(str, Enum):
    ACTIVE = "active"
    EXPIRING = "expiring"
    NEGOTIATING = "negotiating"
    EXPIRED = "expired"


# ==================== DRIVER MODELS ====================

class DriverStats(BaseModel):
    """Driver statistics."""
    pace: int = Field(ge=1, le=99)
    overtaking: int = Field(ge=1, le=99)
    defending: int = Field(ge=1, le=99)
    consistency: int = Field(ge=1, le=99)
    tire_management: int = Field(ge=1, le=99)
    wet_skill: int = Field(ge=1, le=99)

    @property
    def overall(self) -> int:
        """CLI weighted overall calculation."""
        return int(
            self.pace * 0.25 +
            self.overtaking * 0.15 +
            self.defending * 0.15 +
            self.consistency * 0.20 +
            self.tire_management * 0.15 +
            self.wet_skill * 0.10
        )


class ContractDemand(BaseModel):
    """A demand in contract negotiation."""
    type: str  # salary_increase, number_one_status, longer_contract, release_clause
    description: str
    importance: int  # 1-10 how important to driver
    satisfied: bool = False


class DriverContract(BaseModel):
    """Driver contract information."""
    years_remaining: int
    salary: float  # Per season in millions
    is_number_one: bool = False
    has_release_clause: bool = False
    status: ContractStatus = ContractStatus.ACTIVE
    demands: List[ContractDemand] = []
    negotiation_deadline: Optional[int] = None  # Race number deadline


class DriverInfo(BaseModel):
    """Driver information."""
    id: str
    name: str
    age: int
    nationality: str
    stats: DriverStats
    salary: float  # In millions per year
    market_value: float
    potential: int
    team_name: Optional[str] = None

    # Season stats
    season_points: int = 0
    race_wins: int = 0
    podiums: int = 0
    dnfs: int = 0
    best_finish: int = 99

    # Morale system (0-100)
    morale: int = 75
    confidence: int = 75

    # Streaks
    win_streak: int = 0
    podium_streak: int = 0
    no_points_streak: int = 0
    dnf_streak: int = 0
    beaten_by_teammate_streak: int = 0

    # Contract
    contract: Optional[DriverContract] = None

    # Rising star
    rising_star_races: int = 0

    # Is this a player's driver?
    is_player_driver: bool = False
    player_id: Optional[str] = None  # Which player owns this driver


class MarketDriver(BaseModel):
    """Driver available in the market."""
    id: str
    name: str
    age: int
    nationality: str
    stats: DriverStats
    market_value: float
    salary: float
    potential: int
    current_team: Optional[str] = None  # If contracted
    is_free_agent: bool = True

    # Signing interest system
    min_team_prestige: int = 0  # Minimum team prestige required (0-100)
    interested: bool = True  # Would they join this team?
    interest_reason: str = ""  # Why interested or not


# ==================== CAR MODELS ====================

class CarStats(BaseModel):
    """Car statistics."""
    downforce: int = Field(ge=1, le=100, default=65)
    aero_efficiency: int = Field(ge=1, le=100, default=65)
    chassis: int = Field(ge=1, le=100, default=65)
    power_unit: int = Field(ge=1, le=100, default=65)
    reliability: int = Field(ge=1, le=100, default=70)
    tire_cooling: int = Field(ge=1, le=100, default=65)

    @property
    def overall(self) -> int:
        """CLI weighted overall calculation."""
        return int(
            self.downforce * 0.18 +
            self.aero_efficiency * 0.18 +
            self.chassis * 0.22 +
            self.power_unit * 0.18 +
            self.reliability * 0.12 +
            self.tire_cooling * 0.12
        )


class UpgradeOption(BaseModel):
    """Car upgrade option."""
    stat_name: str
    display_name: str
    current_value: int
    upgrade_cost: float  # In millions
    new_value: int
    can_afford: bool = True


class DevelopmentNode(BaseModel):
    """A node in the development tree."""
    id: str
    name: str
    description: str
    category: str  # aerodynamics, power_unit, chassis, tire_management
    branch: str  # high_downforce, low_drag, balanced, etc.
    cost: float  # In millions
    development_time: int  # Races to complete
    effects: Dict[str, int]  # stat_name -> change (can be negative for trade-offs)
    prerequisites: List[str] = []  # Node IDs required first
    is_completed: bool = False
    is_in_progress: bool = False
    races_remaining: int = 0
    is_locked: bool = False  # True if branch choice excluded this


class DevelopmentTree(BaseModel):
    """Full development tree state."""
    nodes: List[DevelopmentNode]
    active_developments: List[str] = []  # Node IDs currently in progress (max 2)
    completed_developments: List[str] = []
    branch_choices: Dict[str, str] = {}  # category -> chosen branch


# ==================== SPONSOR MODELS ====================

class SponsorObjective(BaseModel):
    """A sponsor objective."""
    type: str  # finish_position, points_finish, podium, win, constructor_position
    target: int  # Target position or count
    description: str


class SponsorInfo(BaseModel):
    """Sponsor information."""
    id: str
    name: str
    tier: SponsorTier
    payment_per_race: float  # In millions
    season_bonus: float  # If objectives met
    objective: SponsorObjective

    # Progress tracking
    races_completed: int = 0
    objectives_met: int = 0

    @property
    def success_rate(self) -> float:
        if self.races_completed == 0:
            return 0
        return (self.objectives_met / self.races_completed) * 100

    @property
    def bonus_on_track(self) -> bool:
        return self.success_rate >= 80


# ==================== TEAM MODELS ====================

class TeamInfo(BaseModel):
    """Team information."""
    id: str
    name: str
    budget: float  # In millions
    car: CarStats
    drivers: List[DriverInfo] = []
    season_points: int = 0
    race_wins: int = 0

    # Player info
    is_player_team: bool = False
    player_id: Optional[str] = None
    player_username: Optional[str] = None

    # Sponsor
    sponsor: Optional[SponsorInfo] = None

    # Development
    development_tree: Optional[DevelopmentTree] = None


# ==================== INBOX MODELS ====================

class InboxMessage(BaseModel):
    """Inbox message."""
    id: str
    type: MessageType
    priority: MessagePriority
    subject: str
    body: str
    timestamp: datetime
    is_read: bool = False
    sender: str = "System"


# ==================== TRACK & RACE MODELS ====================

class TrackInfo(BaseModel):
    """Track information."""
    id: str
    name: str
    country: str
    city: str
    laps: int
    track_type: str  # STREET, CIRCUIT, HIGH_SPEED, HIGH_DOWNFORCE, POWER
    overtaking_difficulty: float  # 1-10, higher = harder
    tire_degradation: float  # Multiplier, 1.0 = normal


class QualifyingResult(BaseModel):
    """Qualifying result for a driver."""
    position: int
    driver_name: str
    team_name: str
    lap_time: str
    is_player_driver: bool = False
    player_id: Optional[str] = None


class RaceEntry(BaseModel):
    """Race entry/position during race."""
    position: int
    driver_name: str
    team_name: str
    gap: str  # Gap to leader
    tire: TireCompound
    tire_wear: int  # 0-100
    pit_stops: int
    is_player_driver: bool = False
    player_id: Optional[str] = None
    status: str = "racing"  # racing, dnf, finished


class RaceEvent(BaseModel):
    """Event that happened during the race."""
    lap: int
    event_type: str  # overtake, pit_stop, incident, dnf, safety_car, weather
    description: str
    driver_name: Optional[str] = None


class PitDecisionStatus(BaseModel):
    """Status of pit decisions for multiplayer sync."""
    paused_for_pits: bool = False  # Race is paused waiting for pit decisions
    my_drivers_needing_pit: List[str] = []  # Driver IDs that need pit decision
    i_need_to_decide: bool = False  # This player needs to make a decision
    i_have_confirmed: bool = True  # This player has confirmed their decisions
    waiting_for_players: List[str] = []  # Usernames of players we're waiting for
    all_confirmed: bool = True  # All players have confirmed


class RaceState(BaseModel):
    """Current state of an ongoing race."""
    current_lap: int
    total_laps: int
    positions: List[RaceEntry]
    events: List[RaceEvent] = []
    is_finished: bool = False
    weather: str = "dry"
    safety_car: bool = False
    safety_car_laps: int = 0

    # Multiplayer pit decision sync
    pit_decision_status: Optional[PitDecisionStatus] = None


class RaceResult(BaseModel):
    """Final race result."""
    position: int
    driver_name: str
    team_name: str
    total_time: str
    points: int
    fastest_lap: bool = False
    is_player_driver: bool = False
    player_id: Optional[str] = None
    status: str = "finished"


class SeasonCalendarEntry(BaseModel):
    """Entry in the season calendar."""
    race_number: int
    track: TrackInfo
    is_completed: bool = False
    is_current: bool = False
    winner: Optional[str] = None


# ==================== STANDINGS ====================

class DriverStanding(BaseModel):
    """Driver championship standing."""
    position: int
    driver_name: str
    team_name: str
    points: int
    wins: int
    podiums: int
    is_player_driver: bool = False
    player_id: Optional[str] = None


class ConstructorStanding(BaseModel):
    """Constructor championship standing."""
    position: int
    team_name: str
    points: int
    wins: int
    is_player_team: bool = False
    player_id: Optional[str] = None


# ==================== MULTIPLAYER ====================

class PlayerState(BaseModel):
    """State for a single player in multiplayer."""
    player_id: str
    username: str
    team_name: str
    is_ready: bool = False  # Ready to proceed
    has_set_team_name: bool = False
    has_selected_sponsor: bool = False
    has_selected_tires: bool = False
    drivers_signed: int = 0


class TurnInfo(BaseModel):
    """Information about current turn in multiplayer."""
    current_player_id: str
    current_player_username: str
    action_required: str  # What the player needs to do
    waiting_for: List[str] = []  # Player IDs we're waiting for
    turn_order: List[str] = []  # Order of player IDs for this phase


# ==================== MAIN RESPONSE ====================

class GameStateResponse(BaseModel):
    """Full game state response for a player."""
    game_id: str
    phase: GamePhase
    current_season: int
    current_race: int
    total_races: int

    # Multiplayer info
    is_multiplayer: bool = False
    player_count: int = 1
    players: List[PlayerState] = []
    turn_info: Optional[TurnInfo] = None
    your_player_id: str = ""
    is_your_turn: bool = True

    # Your team info
    player_team: Optional[TeamInfo] = None

    # Opponent team (in multiplayer)
    opponent_team: Optional[TeamInfo] = None

    # Current track (if in race weekend)
    current_track: Optional[TrackInfo] = None

    # Race data
    qualifying_results: Optional[List[QualifyingResult]] = None
    race_state: Optional[RaceState] = None
    race_results: Optional[List[RaceResult]] = None

    # Standings
    driver_standings: Optional[List[DriverStanding]] = None
    constructor_standings: Optional[List[ConstructorStanding]] = None

    # Calendar
    calendar: Optional[List[SeasonCalendarEntry]] = None

    # Team management
    available_sponsors: Optional[List[SponsorInfo]] = None
    market_drivers: Optional[List[MarketDriver]] = None
    upgrade_options: Optional[List[UpgradeOption]] = None
    development_tree: Optional[DevelopmentTree] = None
    inbox: Optional[List[InboxMessage]] = None

    # Driver market info
    min_driver_cost: float = 0
    drivers_needed: int = 0

    # All teams (for viewing rivals)
    all_teams: Optional[List[TeamInfo]] = None

    # Messages/notifications
    notifications: List[str] = []

    # Game stopped flag (for multiplayer sync - redirect to lobby)
    game_stopped: bool = False
    stopped_by: Optional[str] = None  # Username of player who stopped


# ==================== REQUEST MODELS ====================

class TireSelectionRequest(BaseModel):
    """Request to select tires for race start."""
    driver_id: str
    compound: TireCompound


class PitStopRequest(BaseModel):
    """Request to make a pit stop."""
    driver_id: str
    compound: TireCompound


class SignDriverRequest(BaseModel):
    """Request to sign a driver."""
    driver_id: str
    salary: float
    years: int = 2
    is_number_one: bool = False


class ReleaseDriverRequest(BaseModel):
    """Request to release a driver."""
    driver_id: str


class UpgradeCarRequest(BaseModel):
    """Request to upgrade car stat."""
    stat_name: str
    points: int = 1


class SelectSponsorRequest(BaseModel):
    """Request to select a sponsor."""
    sponsor_id: str


class StartDevelopmentRequest(BaseModel):
    """Request to start a development node."""
    node_id: str


class NegotiateContractRequest(BaseModel):
    """Request to negotiate a driver contract."""
    driver_id: str
    new_salary: float
    years: int
    is_number_one: bool
    include_release_clause: bool = False


class ReadyRequest(BaseModel):
    """Mark player as ready to proceed."""
    ready: bool = True


class SetTeamNameRequest(BaseModel):
    """Request to set team name."""
    team_name: str
