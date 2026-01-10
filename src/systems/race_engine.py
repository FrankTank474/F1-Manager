"""Race Simulation Engine with Strategy"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional
from ..models import Driver, Team, Track, Car
from ..ui.colors import get_team_color, Colors
from .incidents import IncidentSystem, RaceIncident
from .rivalry import RivalryManager


class TireCompound(Enum):
    SOFT = "Soft"
    MEDIUM = "Medium"
    HARD = "Hard"
    INTERMEDIATE = "Intermediate"
    WET = "Wet"


class Weather(Enum):
    DRY = "Dry"
    LIGHT_RAIN = "Light Rain"
    HEAVY_RAIN = "Heavy Rain"


@dataclass
class TireState:
    compound: TireCompound
    wear: float = 0.0  # 0-100, 100 = dead tire

    @property
    def performance(self) -> float:
        """
        Calculate tire performance based on compound and wear.
        Fresh tires give significant advantage, worn tires have a "cliff" effect.
        """
        # Base grip levels - fresh tire performance
        base_performance = {
            TireCompound.SOFT: 1.0,      # Fastest but wears quickly
            TireCompound.MEDIUM: 0.75,   # Good balance
            TireCompound.HARD: 0.55,     # Slowest but very durable
            TireCompound.INTERMEDIATE: 0.65,
            TireCompound.WET: 0.55,
        }
        base = base_performance[self.compound]

        # Tire wear affects performance non-linearly (cliff effect)
        # 0-30% wear: minimal performance loss
        # 30-60% wear: gradual performance loss
        # 60-80% wear: significant performance loss
        # 80%+ wear: severe "cliff" - tires falling apart
        if self.wear <= 30:
            wear_penalty = (self.wear / 100) * 0.15  # Only 15% of wear affects performance
        elif self.wear <= 60:
            wear_penalty = 0.045 + ((self.wear - 30) / 100) * 0.4  # Moderate penalty
        elif self.wear <= 80:
            wear_penalty = 0.165 + ((self.wear - 60) / 100) * 0.6  # Significant penalty
        else:
            # The cliff - severe performance drop
            wear_penalty = 0.285 + ((self.wear - 80) / 100) * 1.2  # Severe penalty

        return max(0.05, base - wear_penalty)

    @property
    def grip_level(self) -> str:
        """Return a descriptive grip level for display."""
        if self.wear <= 20:
            return "OPTIMAL"
        elif self.wear <= 40:
            return "GOOD"
        elif self.wear <= 60:
            return "WORN"
        elif self.wear <= 80:
            return "CRITICAL"
        else:
            return "DEAD"

    @property
    def degradation_rate(self) -> float:
        """How fast the tire degrades per lap (base rate before driver skill)."""
        rates = {
            TireCompound.SOFT: 3.0,      # Wears fast
            TireCompound.MEDIUM: 1.8,    # Moderate wear
            TireCompound.HARD: 1.0,      # Very durable
            TireCompound.INTERMEDIATE: 1.4,
            TireCompound.WET: 1.2,
        }
        return rates[self.compound]

    @property
    def optimal_window(self) -> int:
        """Number of laps tire is in optimal performance window."""
        windows = {
            TireCompound.SOFT: 12,
            TireCompound.MEDIUM: 22,
            TireCompound.HARD: 35,
            TireCompound.INTERMEDIATE: 25,
            TireCompound.WET: 30,
        }
        return windows[self.compound]


@dataclass
class RaceEntry:
    driver: Driver
    team: Team
    car: Car
    tire: TireState
    position: int
    gap_to_leader: float = 0.0
    total_time: float = 0.0
    pit_stops: int = 0
    dnf: bool = False
    dnf_reason: str = ""
    laps_on_tire: int = 0
    # Weekend form modifiers (set at start of weekend)
    weekend_form: float = 0.0  # -10 to +10 performance modifier
    quali_form: float = 0.0  # Additional qualifying modifier
    mechanical_issue: bool = False  # Minor mechanical issue affecting pace
    no_more_pit_prompts: bool = False  # Player chose to stay out until end


@dataclass
class RaceState:
    entries: List[RaceEntry]
    current_lap: int = 0
    total_laps: int = 0
    weather: Weather = Weather.DRY
    safety_car: bool = False
    safety_car_laps: int = 0


class RaceEngine:
    def __init__(self, track: Track, teams: List[Team], player_team: Team, rivalry_manager: Optional[RivalryManager] = None):
        self.track = track
        self.teams = teams
        self.player_team = player_team
        self.race_state: Optional[RaceState] = None
        self.qualifying_results: List[RaceEntry] = []
        self.race_log: List[str] = []
        self.weekend_modifiers: Dict[str, Dict] = {}  # driver_name -> modifiers
        self.incident_system = IncidentSystem()
        self.rivalry_manager = rivalry_manager or RivalryManager()
        self.race_incidents: List[RaceIncident] = []  # Track all incidents this race
        self.qualifying_positions: Dict[str, int] = {}  # Track quali positions for headlines
        self._generate_weekend_modifiers()

    def _generate_weekend_modifiers(self) -> None:
        """Generate random weekend form modifiers for all drivers."""
        for team in self.teams:
            for driver in team.drivers:
                # Base weekend form: stronger drivers more consistent
                # Reduced variance so driver skill matters more
                consistency_factor = driver.stats.consistency / 100
                form_variance = 5 * (1 - consistency_factor * 0.6)  # 2-5 range based on consistency

                # Weekend form affects overall pace (-5 to +5 typically)
                weekend_form = random.gauss(0, form_variance)

                # Qualifying-specific form (some drivers are better qualifiers) - reduced
                quali_bonus = random.gauss(0, 1.5)

                # Mechanical issues - top teams have more complex cars
                # Calculate team strength (rough estimate from car performance)
                car_perf = team.car.performance
                # Top teams (perf > 75) have 8% chance of minor issues
                # Mid teams (60-75) have 5% chance
                # Backmarkers (< 60) have 3% chance (simpler, more reliable setups)
                if car_perf > 75:
                    mech_issue_chance = 0.08
                elif car_perf > 60:
                    mech_issue_chance = 0.05
                else:
                    mech_issue_chance = 0.03

                has_mech_issue = random.random() < mech_issue_chance

                # Underdog boost - backmarker drivers occasionally have standout weekends
                underdog_boost = 0.0
                if car_perf < 65 and random.random() < 0.12:  # 12% chance for backmarkers
                    underdog_boost = random.uniform(3, 8)  # Significant boost

                self.weekend_modifiers[driver.name] = {
                    'weekend_form': weekend_form + underdog_boost,
                    'quali_form': quali_bonus,
                    'mechanical_issue': has_mech_issue,
                    'underdog_weekend': underdog_boost > 0
                }

    def _calculate_car_performance(self, car: Car) -> float:
        """
        Calculate car performance adjusted for track characteristics.
        Different tracks favor different car attributes significantly.
        """
        from ..models.track import TrackType

        # Base performance from car stats
        base = car.performance

        # Track-specific bonuses (stronger effect than before)
        # Each stat point above/below 50 gives bonus/penalty scaled by track type

        # DOWNFORCE - crucial at high downforce tracks, less important at power tracks
        downforce_diff = car.downforce - 50
        if self.track.track_type == TrackType.HIGH_DOWNFORCE:
            # Monaco, Hungary, Singapore - downforce is KING
            downforce_bonus = downforce_diff * 0.12
        elif self.track.track_type == TrackType.STREET:
            # Street circuits need good downforce for tight corners
            downforce_bonus = downforce_diff * 0.08
        elif self.track.track_type == TrackType.POWER:
            # Spa, Monza, Las Vegas - downforce matters less
            downforce_bonus = downforce_diff * 0.03
        else:  # BALANCED
            downforce_bonus = downforce_diff * 0.06

        # POWER UNIT - crucial at power tracks, less important at high downforce
        power_diff = car.power_unit - 50
        if self.track.track_type == TrackType.POWER:
            # Monza, Spa, Las Vegas, Austria - ENGINE POWER is everything
            power_bonus = power_diff * 0.12
        elif self.track.track_type == TrackType.BALANCED:
            power_bonus = power_diff * 0.07
        elif self.track.track_type == TrackType.STREET:
            # Street circuits - power helps on straights but less crucial
            power_bonus = power_diff * 0.05
        else:  # HIGH_DOWNFORCE
            power_bonus = power_diff * 0.03

        # AERO EFFICIENCY - helps everywhere but especially at tracks with long straights AND corners
        aero_diff = car.aero_efficiency - 50
        if self.track.track_type == TrackType.BALANCED:
            # Silverstone, Suzuka - need both straight speed AND cornering
            aero_bonus = aero_diff * 0.08
        elif self.track.track_type == TrackType.POWER:
            # Low drag helps on straights
            aero_bonus = aero_diff * 0.06
        else:
            aero_bonus = aero_diff * 0.05

        # CHASSIS - crucial at street circuits with bumps and curbs
        chassis_diff = car.chassis - 50
        if self.track.track_type == TrackType.STREET:
            # Street circuits have bumps, curbs, walls - chassis handling crucial
            chassis_bonus = chassis_diff * 0.10
        elif self.track.track_type == TrackType.HIGH_DOWNFORCE:
            # Tight corners need good mechanical grip
            chassis_bonus = chassis_diff * 0.07
        else:
            chassis_bonus = chassis_diff * 0.05

        return base + downforce_bonus + power_bonus + aero_bonus + chassis_bonus

    def _calculate_lap_time(self, entry: RaceEntry, weather: Weather, is_qualifying: bool = False) -> float:
        """Calculate lap time for a driver."""
        base_time = self.track.base_lap_time

        # Car performance (30% influence)
        car_factor = (100 - self._calculate_car_performance(entry.car)) * 0.030

        # Driver pace (40% influence) - SIGNIFICANTLY impacts lap time
        # A 92-rated driver vs 75-rated = (100-75)*0.04 - (100-92)*0.04 = 1.0 - 0.32 = 0.68s per lap
        driver_factor = (100 - entry.driver.stats.pace) * 0.040

        # TIRE PERFORMANCE (30% influence - this is where strategy matters!)
        # Fresh soft tires vs dead tires can be 2-3 seconds difference
        tire_perf = entry.tire.performance
        # Base penalty for not having perfect tires
        # tire_perf of 1.0 (fresh soft) = 0 penalty
        # tire_perf of 0.5 (worn medium) = ~1.5s penalty
        # tire_perf of 0.1 (dead tires) = ~3s penalty
        tire_factor = (1.0 - tire_perf) * 3.5

        # Additional penalty when tires are in critical state (cliff effect visible in lap times)
        if entry.tire.wear > 70:
            cliff_penalty = ((entry.tire.wear - 70) / 30) * 1.5  # Up to 1.5s extra at 100% wear
            tire_factor += cliff_penalty

        # Consistency variance - reduced to let skill shine through more
        # High consistency = very predictable, low consistency = erratic
        consistency = entry.driver.stats.consistency
        variance = random.gauss(0, (100 - consistency) * 0.006)

        # Weekend form modifier (key for variety!)
        modifiers = self.weekend_modifiers.get(entry.driver.name, {})
        weekend_form = modifiers.get('weekend_form', 0)
        form_factor = -weekend_form * 0.02  # Convert to time (positive form = faster)

        # Qualifying-specific form
        if is_qualifying:
            quali_form = modifiers.get('quali_form', 0)
            form_factor -= quali_form * 0.015

        # Mechanical issue penalty (affects pace by 0.2-0.5s per lap)
        mech_penalty = 0
        if modifiers.get('mechanical_issue', False):
            mech_penalty = random.uniform(0.2, 0.5)

        # Weather effects - wet weather creates MORE variance (helps underdogs)
        weather_factor = 0
        if weather == Weather.LIGHT_RAIN:
            if entry.tire.compound in [TireCompound.SOFT, TireCompound.MEDIUM, TireCompound.HARD]:
                weather_factor = 5.0 - (entry.driver.stats.wet_skill * 0.03)
            elif entry.tire.compound == TireCompound.INTERMEDIATE:
                weather_factor = 0.5
            # Extra variance in wet conditions
            variance += random.gauss(0, 0.3)
        elif weather == Weather.HEAVY_RAIN:
            if entry.tire.compound in [TireCompound.SOFT, TireCompound.MEDIUM, TireCompound.HARD]:
                weather_factor = 15.0 - (entry.driver.stats.wet_skill * 0.05)
            elif entry.tire.compound == TireCompound.INTERMEDIATE:
                weather_factor = 3.0
            elif entry.tire.compound == TireCompound.WET:
                weather_factor = 0.5
            # Even more variance in heavy rain
            variance += random.gauss(0, 0.5)

        return base_time + car_factor + driver_factor + tire_factor + variance + weather_factor + form_factor + mech_penalty

    def run_qualifying(self) -> List[RaceEntry]:
        """Simulate qualifying session."""
        entries = []

        for team in self.teams:
            for driver in team.drivers:
                modifiers = self.weekend_modifiers.get(driver.name, {})
                entry = RaceEntry(
                    driver=driver,
                    team=team,
                    car=team.car,
                    tire=TireState(TireCompound.SOFT),
                    position=0,
                    weekend_form=modifiers.get('weekend_form', 0),
                    quali_form=modifiers.get('quali_form', 0),
                    mechanical_issue=modifiers.get('mechanical_issue', False)
                )

                # Simulate 3 quali laps, take best (using qualifying flag)
                lap_times = [self._calculate_lap_time(entry, Weather.DRY, is_qualifying=True) for _ in range(3)]
                entry.total_time = min(lap_times)

                # Qualifying incidents - small chance of not setting a time (traffic, crash, etc.)
                if random.random() < 0.02:  # 2% chance
                    entry.total_time += 5.0  # Significant time loss
                    self.race_log.append(f"QUALIFYING: {driver.name} had a troubled session!")

                entries.append(entry)

        # Sort by lap time
        entries.sort(key=lambda e: e.total_time)

        # Assign positions
        for i, entry in enumerate(entries):
            entry.position = i + 1

        # Log underdog performances
        for entry in entries:
            if entry.position <= 10:
                modifiers = self.weekend_modifiers.get(entry.driver.name, {})
                if modifiers.get('underdog_weekend', False):
                    self.race_log.append(f"QUALIFYING: {entry.driver.name} is having a standout weekend!")

        self.qualifying_results = entries
        # Store qualifying positions for headline generation
        for entry in entries:
            self.qualifying_positions[entry.driver.name] = entry.position
        return entries

    def display_qualifying_results(self) -> str:
        """Return formatted qualifying results with team colors."""
        lines = [
            "\n" + "=" * 70,
            f"  QUALIFYING RESULTS - {self.track.name}",
            "=" * 70,
            f"  {'Pos':<4} {'Driver':<22} {'Team':<18} {'Time':>10}",
            "-" * 70
        ]

        pole_time = self.qualifying_results[0].total_time

        for entry in self.qualifying_results:
            if entry.position == 1:
                time_str = f"{entry.total_time:.3f}"
            else:
                gap = entry.total_time - pole_time
                time_str = f"+{gap:.3f}"

            color = get_team_color(entry.team.name)
            player_marker = " *" if entry.team == self.player_team else "  "

            lines.append(
                f"{player_marker}{entry.position:<3} "
                f"{color}{entry.driver.name:<22}{Colors.RESET} "
                f"{color}{entry.team.name:<18}{Colors.RESET} "
                f"{time_str:>10}"
            )

        lines.append("=" * 70)
        lines.append("  * = Your team")
        return "\n".join(lines)

    def initialize_race(self, player_tire: TireCompound) -> None:
        """Initialize race state from qualifying results."""
        entries = []

        for quali_entry in self.qualifying_results:
            # Default AI to medium tires
            if quali_entry.team == self.player_team:
                tire = TireState(player_tire)
            else:
                # AI tire strategy based on position and track
                # More aggressive strategies at harder-to-overtake tracks
                if self.track.overtaking_difficulty >= 7:
                    # Hard to overtake - front runners go long, backmarkers go aggressive
                    if quali_entry.position <= 5:
                        tire = TireState(TireCompound.MEDIUM)
                    else:
                        tire = TireState(TireCompound.SOFT)
                else:
                    # Easier overtaking - more variety
                    if quali_entry.position <= 3:
                        tire = TireState(TireCompound.MEDIUM)
                    elif quali_entry.position <= 10:
                        tire = TireState(random.choice([TireCompound.SOFT, TireCompound.MEDIUM]))
                    else:
                        tire = TireState(TireCompound.SOFT)

            # Carry over weekend modifiers
            modifiers = self.weekend_modifiers.get(quali_entry.driver.name, {})

            entry = RaceEntry(
                driver=quali_entry.driver,
                team=quali_entry.team,
                car=quali_entry.car,
                tire=tire,
                position=quali_entry.position,
                weekend_form=modifiers.get('weekend_form', 0),
                quali_form=modifiers.get('quali_form', 0),
                mechanical_issue=modifiers.get('mechanical_issue', False)
            )
            entries.append(entry)

        self.race_state = RaceState(
            entries=entries,
            current_lap=0,
            total_laps=self.track.laps,
            weather=Weather.DRY
        )
        self.race_log = []
        self.race_incidents = []
        self.incident_system.reset()

    def _simulate_race_start(self) -> None:
        """Simulate race start with position changes and potential incidents."""
        start_scores = []

        for entry in self.race_state.entries:
            if entry.dnf:
                continue

            # Start performance based on reaction, consistency, and weekend form
            start_skill = (entry.driver.stats.pace + entry.driver.stats.consistency) / 2
            weekend_bonus = entry.weekend_form * 0.3

            # Base score from grid position (lower is better)
            base_score = entry.position * 2

            # Random factor - bigger variance allows underdogs to jump
            variance = random.gauss(0, 2.5)

            # Skill factor - better starters lose less/gain more
            skill_factor = (50 - start_skill) * 0.1

            start_score = base_score + variance + skill_factor - weekend_bonus
            start_scores.append((entry, start_score))

        # First lap incident chance (5% of races have a significant first lap incident)
        if random.random() < 0.05:
            # Pick 1-3 random cars to have incidents
            incident_count = random.randint(1, 3)
            active_entries = [e for e, _ in start_scores]
            incident_victims = random.sample(active_entries, min(incident_count, len(active_entries)))

            for victim in incident_victims:
                if random.random() < 0.4:  # 40% of incidents are DNFs
                    victim.dnf = True
                    victim.dnf_reason = random.choice([
                        "First lap collision", "Spun off at Turn 1",
                        "Contact with another car", "Crash at the start"
                    ])
                    self.race_log.append(f"LAP 1: {victim.driver.name} OUT - {victim.dnf_reason}!")
                else:
                    # Just lose positions (damage)
                    for i, (e, score) in enumerate(start_scores):
                        if e == victim:
                            start_scores[i] = (e, score + random.uniform(5, 15))
                            self.race_log.append(f"LAP 1: {victim.driver.name} loses positions after contact!")
                            break

        # Sort by start score (lower is better)
        start_scores.sort(key=lambda x: x[1])

        # Assign new positions
        pos = 1
        for entry, _ in start_scores:
            if not entry.dnf:
                old_pos = entry.position
                entry.position = pos
                if abs(old_pos - pos) >= 3:
                    if pos < old_pos:
                        self.race_log.append(f"LAP 1: {entry.driver.name} great start! P{old_pos} -> P{pos}")
                    else:
                        self.race_log.append(f"LAP 1: {entry.driver.name} poor start! P{old_pos} -> P{pos}")
                pos += 1

    def _attempt_overtake(self, attacker: RaceEntry, defender: RaceEntry) -> Tuple[bool, bool]:
        """
        Attempt an overtake.
        Returns (successful, was_aggressive) - aggressive moves may create rivalries.
        """
        if attacker.dnf or defender.dnf:
            return False, False

        # Calculate overtake probability
        pace_diff = attacker.driver.stats.pace - defender.driver.stats.pace
        overtake_skill = attacker.driver.stats.overtaking
        defend_skill = defender.driver.stats.defending
        car_diff = self._calculate_car_performance(attacker.car) - self._calculate_car_performance(defender.car)
        tire_diff = attacker.tire.performance - defender.tire.performance

        # Weekend form affects overtaking (good form = more aggressive)
        form_diff = attacker.weekend_form - defender.weekend_form

        # Track difficulty affects overtaking
        track_factor = (10 - self.track.overtaking_difficulty) * 2

        # DRS zones help overtaking
        drs_bonus = self.track.drs_zones * 1.5

        # Mechanical issues make defending harder
        mech_penalty = 0
        if defender.mechanical_issue:
            mech_penalty = 5  # Easier to pass cars with issues

        # Rivalry modifier - rivals are more aggressive
        rivalry_mod = self.rivalry_manager.get_battle_intensity_modifier(
            attacker.driver.name, defender.driver.name
        )

        probability = (20 + pace_diff * 0.3 + (overtake_skill - defend_skill) * 0.2 +
                      car_diff * 0.1 + tire_diff * 20 + track_factor + drs_bonus +
                      form_diff * 0.5 + mech_penalty) * rivalry_mod

        success = random.random() * 100 < probability

        # Determine if it was an aggressive move (close battle, high probability required)
        was_aggressive = success and probability < 40 and random.random() < 0.3

        return success, was_aggressive

    def _simulate_lap(self) -> List[str]:
        """Simulate a single lap and return events."""
        events = []
        state = self.race_state
        state.current_lap += 1

        # Weather change chance (rare - about 15% of races see rain)
        if random.random() < 0.005:  # 0.5% per lap
            if state.weather == Weather.DRY:
                state.weather = Weather.LIGHT_RAIN
                events.append(f"LAP {state.current_lap}: Weather change - Light rain starting!")
            elif state.weather == Weather.LIGHT_RAIN:
                if random.random() < 0.6:  # 60% chance to get heavier
                    state.weather = Weather.HEAVY_RAIN
                    events.append(f"LAP {state.current_lap}: Weather change - HEAVY RAIN!")
                else:
                    state.weather = Weather.DRY
                    events.append(f"LAP {state.current_lap}: Weather change - Track drying!")
            else:  # Heavy rain
                if random.random() < 0.7:  # 70% chance to ease
                    state.weather = Weather.LIGHT_RAIN
                    events.append(f"LAP {state.current_lap}: Weather change - Rain easing!")
                # 30% chance heavy rain continues

        # Check for incidents using the incident system
        incident = self.incident_system.check_for_incident(
            state.entries,
            state.current_lap,
            state.total_laps,
            state.weather.value,
            self.track.overtaking_difficulty
        )

        if incident:
            self.race_incidents.append(incident)
            events.append(f"LAP {state.current_lap}: {incident.description}")

            if incident.causes_red_flag:
                events.append(f"LAP {state.current_lap}: RED FLAG! Race suspended!")
            elif incident.causes_safety_car:
                state.safety_car = True
                events.append(f"LAP {state.current_lap}: SAFETY CAR DEPLOYED!")

            # Record collision in rivalry system
            if incident.secondary_driver:
                self.rivalry_manager.record_collision(
                    incident.primary_driver,
                    incident.secondary_driver,
                    self.track.name,
                    state.current_lap,
                    aggressor=incident.primary_driver
                )

        # Update safety car status
        if self.incident_system.safety_car_active:
            state.safety_car = True
            still_active, sc_message = self.incident_system.update_safety_car()
            if sc_message:
                events.append(f"LAP {state.current_lap}: {sc_message}")
            if not still_active:
                state.safety_car = False

        # Update red flag status
        if self.incident_system.red_flag_active:
            still_active, rf_message = self.incident_system.update_red_flag(state.current_lap)
            if rf_message:
                events.append(f"LAP {state.current_lap}: {rf_message}")

        # Calculate lap times and update positions
        for entry in state.entries:
            if entry.dnf:
                continue

            # DNF chance based on reliability (realistic: ~2-3 DNFs per race)
            dnf_chance = (100 - entry.car.reliability) * 0.00004
            if random.random() < dnf_chance:
                entry.dnf = True
                entry.dnf_reason = random.choice([
                    "Engine failure", "Gearbox issue", "Hydraulics problem",
                    "Collision damage", "Brake failure", "Suspension failure"
                ])
                events.append(f"LAP {state.current_lap}: {entry.driver.name} OUT - {entry.dnf_reason}!")
                continue

            # Calculate lap time
            lap_time = self._calculate_lap_time(entry, state.weather)
            if state.safety_car:
                lap_time = self.track.base_lap_time + 10  # Slow pace under SC

            entry.total_time += lap_time

            # TIRE DEGRADATION - Affected by driver skill AND car tire cooling!
            # Base degradation from tire compound and track
            base_deg = entry.tire.degradation_rate * self.track.tire_degradation

            # CAR TIRE COOLING - Major factor in tire wear!
            # tire_cooling 100 = 0.5x wear (excellent cooling, tires stay in window)
            # tire_cooling 65 = 0.85x wear (average)
            # tire_cooling 30 = 1.2x wear (poor cooling, tires overheat)
            car_cooling_factor = entry.car.tire_wear_factor

            # DRIVER tire management skill (40-100% of remaining rate)
            # tire_management 100 = only 40% wear rate (excellent tire whisperer)
            # tire_management 50 = 70% wear rate (average)
            # tire_management 0 = 100% wear rate (destroys tires)
            tire_mgmt_factor = 1.0 - (entry.driver.stats.tire_management / 166.67)  # Range: 0.4 to 1.0
            driver_factor = max(0.4, tire_mgmt_factor)

            # Combine car and driver factors
            deg_rate = base_deg * car_cooling_factor * driver_factor

            # Pushing hard (aggressive driving) wears tires faster
            # Drivers with lower consistency push harder inconsistently
            aggression_factor = 1.0 + (100 - entry.driver.stats.consistency) * 0.002

            # Apply final degradation
            final_deg = deg_rate * aggression_factor
            entry.tire.wear = min(100, entry.tire.wear + final_deg)
            entry.laps_on_tire += 1

            # Warn about tire cliff
            if entry.tire.wear > 70 and entry.tire.wear - final_deg <= 70:
                if entry.team == self.player_team:
                    events.append(f"RADIO: {entry.driver.name}'s tires entering CRITICAL wear zone!")

        # Attempt overtakes (not under safety car or red flag)
        if not state.safety_car and not self.incident_system.red_flag_active:
            active = [e for e in state.entries if not e.dnf]
            active.sort(key=lambda e: e.total_time)

            for i in range(1, len(active)):
                attacker = active[i]
                defender = active[i - 1]

                # Only attempt if within 1.5 seconds
                gap = attacker.total_time - defender.total_time
                if gap < 1.5:
                    success, was_aggressive = self._attempt_overtake(attacker, defender)
                    if success:
                        if was_aggressive:
                            events.append(
                                f"LAP {state.current_lap}: {attacker.driver.name} makes an AGGRESSIVE move on {defender.driver.name}!"
                            )
                            # Record in rivalry system
                            msg = self.rivalry_manager.record_aggressive_move(
                                attacker.driver.name,
                                defender.driver.name,
                                self.track.name,
                                state.current_lap
                            )
                            if msg:
                                events.append(f"  {msg}")
                        else:
                            events.append(
                                f"LAP {state.current_lap}: {attacker.driver.name} overtakes {defender.driver.name}!"
                            )

        # Update positions based on total time
        active = [e for e in state.entries if not e.dnf]
        active.sort(key=lambda e: e.total_time)
        for i, entry in enumerate(active):
            entry.position = i + 1
            if i == 0:
                entry.gap_to_leader = 0
            else:
                entry.gap_to_leader = entry.total_time - active[0].total_time

        return events

    def get_player_pit_prompt(self) -> Optional[List[Dict]]:
        """Check if any player drivers should be prompted for pit stop."""
        if not self.race_state:
            return None

        drivers_needing_pit = []

        for entry in self.race_state.entries:
            if entry.team == self.player_team and not entry.dnf:
                # Skip if player chose to stay out until end
                if entry.no_more_pit_prompts:
                    continue

                tire_wear = entry.tire.wear
                grip_level = entry.tire.grip_level

                # Prompt if tires are worn (past GOOD) or weather changed
                if tire_wear > 50 or (
                    self.race_state.weather != Weather.DRY and
                    entry.tire.compound not in [TireCompound.INTERMEDIATE, TireCompound.WET]
                ):
                    drivers_needing_pit.append({
                        "driver": entry.driver.name,
                        "tire_wear": tire_wear,
                        "current_compound": entry.tire.compound.value,
                        "weather": self.race_state.weather.value,
                        "position": entry.position,
                        "laps_remaining": self.race_state.total_laps - self.race_state.current_lap,
                        "grip_level": grip_level
                    })

        return drivers_needing_pit if drivers_needing_pit else None

    def set_driver_no_pit_prompts(self, driver_name: str) -> None:
        """Set a driver to not receive any more pit prompts."""
        for entry in self.race_state.entries:
            if entry.driver.name == driver_name:
                entry.no_more_pit_prompts = True
                break

    def pit_driver(self, driver_name: str, new_compound: TireCompound) -> str:
        """Pit a driver and change tires."""
        for entry in self.race_state.entries:
            if entry.driver.name == driver_name and not entry.dnf:
                entry.tire = TireState(new_compound)
                entry.total_time += self.track.pit_loss_time
                entry.pit_stops += 1
                entry.laps_on_tire = 0
                return f"{driver_name} pits for {new_compound.value} tires!"
        return "Driver not found or retired."

    def simulate_ai_pits(self) -> List[str]:
        """AI teams decide on pit stops."""
        events = []
        state = self.race_state

        for entry in state.entries:
            if entry.dnf or entry.team == self.player_team:
                continue

            should_pit = False
            new_compound = TireCompound.MEDIUM

            # Weather-based pitting
            if state.weather == Weather.HEAVY_RAIN and entry.tire.compound not in [TireCompound.WET]:
                should_pit = True
                new_compound = TireCompound.WET
            elif state.weather == Weather.LIGHT_RAIN and entry.tire.compound not in [TireCompound.INTERMEDIATE, TireCompound.WET]:
                should_pit = True
                new_compound = TireCompound.INTERMEDIATE
            elif state.weather == Weather.DRY and entry.tire.compound in [TireCompound.INTERMEDIATE, TireCompound.WET]:
                should_pit = True
                new_compound = TireCompound.MEDIUM
            # Wear-based pitting
            elif entry.tire.wear > 70:
                should_pit = True
                laps_remaining = state.total_laps - state.current_lap
                if laps_remaining > 25:
                    new_compound = TireCompound.HARD
                elif laps_remaining > 15:
                    new_compound = TireCompound.MEDIUM
                else:
                    new_compound = TireCompound.SOFT

            if should_pit:
                entry.tire = TireState(new_compound)
                entry.total_time += self.track.pit_loss_time
                entry.pit_stops += 1
                entry.laps_on_tire = 0
                events.append(f"{entry.driver.name} pits for {new_compound.value} tires")

        return events

    def get_race_status(self) -> str:
        """Return current race status display with team colors."""
        state = self.race_state
        active = [e for e in state.entries if not e.dnf]
        active.sort(key=lambda e: e.position)

        sc_indicator = "  |  SAFETY CAR" if state.safety_car else ""

        lines = [
            "\n" + "-" * 85,
            f"  LAP {state.current_lap}/{state.total_laps}  |  Weather: {state.weather.value}{sc_indicator}",
            "-" * 85,
            f"  {'Pos':<4} {'Driver':<20} {'Team':<15} {'Gap':>10} {'Tire':>6} {'Wear':>5} {'Grip':>9}",
            "-" * 85
        ]

        for entry in active:  # Show all drivers
            if entry.position == 1:
                gap_str = "LEADER"
            else:
                gap_str = f"+{entry.gap_to_leader:.1f}s"

            color = get_team_color(entry.team.name)
            player_marker = " *" if entry.team == self.player_team else "  "

            # Color-code grip level
            grip = entry.tire.grip_level
            if grip == "OPTIMAL":
                grip_display = f"{Colors.GREEN}{grip}{Colors.RESET}"
            elif grip == "GOOD":
                grip_display = f"{Colors.CYAN}{grip}{Colors.RESET}"
            elif grip == "WORN":
                grip_display = f"{Colors.YELLOW}{grip}{Colors.RESET}"
            elif grip == "CRITICAL":
                grip_display = f"{Colors.RED}{grip}{Colors.RESET}"
            else:  # DEAD
                grip_display = f"{Colors.RED}{grip}{Colors.RESET}"

            lines.append(
                f"{player_marker}{entry.position:<3} "
                f"{color}{entry.driver.name:<20}{Colors.RESET} "
                f"{color}{entry.team.name:<15}{Colors.RESET} "
                f"{gap_str:>10} "
                f"{entry.tire.compound.value[:3]:>6} {entry.tire.wear:>4.0f}% {grip_display:>9}"
            )

        # Show DNFs
        dnfs = [e for e in state.entries if e.dnf]
        if dnfs:
            lines.append("-" * 85)
            lines.append("  RETIRED:")
            for entry in dnfs:
                color = get_team_color(entry.team.name)
                lines.append(f"    {color}{entry.driver.name}{Colors.RESET} - {entry.dnf_reason}")

        lines.append("-" * 85)
        return "\n".join(lines)

    def run_full_race(self, player_initial_tire: TireCompound) -> List[Tuple[Driver, Team, int]]:
        """Run the complete race and return results."""
        self.initialize_race(player_initial_tire)
        self._simulate_race_start()

        while self.race_state.current_lap < self.race_state.total_laps:
            events = self._simulate_lap()
            self.race_log.extend(events)

            # AI pit stops
            ai_events = self.simulate_ai_pits()
            self.race_log.extend(ai_events)

        return self.get_final_results()

    def run_quick_race(self) -> List[Tuple[Driver, Team, int]]:
        """Run a fully automated race for fast-forward mode."""
        # Auto-select medium tires for player
        self.initialize_race(TireCompound.MEDIUM)
        self._simulate_race_start()

        while self.race_state.current_lap < self.race_state.total_laps:
            self._simulate_lap()

            # All teams pit automatically (including player)
            self._auto_pit_all_teams()

        return self.get_final_results()

    def _auto_pit_all_teams(self) -> None:
        """Automatically handle pit stops for all teams including player."""
        state = self.race_state

        for entry in state.entries:
            if entry.dnf:
                continue

            should_pit = False
            new_compound = TireCompound.MEDIUM

            # Weather-based pitting
            if state.weather == Weather.HEAVY_RAIN and entry.tire.compound not in [TireCompound.WET]:
                should_pit = True
                new_compound = TireCompound.WET
            elif state.weather == Weather.LIGHT_RAIN and entry.tire.compound not in [TireCompound.INTERMEDIATE, TireCompound.WET]:
                should_pit = True
                new_compound = TireCompound.INTERMEDIATE
            elif state.weather == Weather.DRY and entry.tire.compound in [TireCompound.INTERMEDIATE, TireCompound.WET]:
                should_pit = True
                new_compound = TireCompound.MEDIUM
            # Wear-based pitting
            elif entry.tire.wear > 70:
                should_pit = True
                laps_remaining = state.total_laps - state.current_lap
                if laps_remaining > 25:
                    new_compound = TireCompound.HARD
                elif laps_remaining > 15:
                    new_compound = TireCompound.MEDIUM
                else:
                    new_compound = TireCompound.SOFT

            if should_pit:
                entry.tire = TireState(new_compound)
                entry.total_time += self.track.pit_loss_time
                entry.pit_stops += 1
                entry.laps_on_tire = 0

    def get_final_results(self) -> List[Tuple[Driver, Team, int]]:
        """Get final race results."""
        results = []
        active = [e for e in self.race_state.entries if not e.dnf]
        active.sort(key=lambda e: e.total_time)

        for i, entry in enumerate(active):
            results.append((entry.driver, entry.team, i + 1))

        # DNFs get position 0
        for entry in self.race_state.entries:
            if entry.dnf:
                results.append((entry.driver, entry.team, 0))

        return results

    def display_race_results(self) -> str:
        """Return formatted race results with team colors."""
        results = self.get_final_results()
        active = [(d, t, p) for d, t, p in results if p > 0]
        dnfs = [(d, t, p) for d, t, p in results if p == 0]

        lines = [
            "\n" + "=" * 70,
            f"  RACE RESULTS - {self.track.name}",
            "=" * 70,
            f"  {'Pos':<4} {'Driver':<22} {'Team':<20} {'Points':>6}",
            "-" * 70
        ]

        from .standings import POINTS_SYSTEM
        for driver, team, pos in active:
            points = POINTS_SYSTEM.get(pos, 0)
            color = get_team_color(team.name)
            marker = " *" if team == self.player_team else "  "
            lines.append(
                f"{marker}{pos:<3} "
                f"{color}{driver.name:<22}{Colors.RESET} "
                f"{color}{team.name:<20}{Colors.RESET} "
                f"{points:>6}"
            )

        if dnfs:
            lines.append("-" * 70)
            lines.append("  DNF:")
            for driver, team, _ in dnfs:
                color = get_team_color(team.name)
                lines.append(f"    {color}{driver.name}{Colors.RESET} ({color}{team.name}{Colors.RESET})")

        lines.append("=" * 70)
        lines.append("  * = Your team")
        return "\n".join(lines)
