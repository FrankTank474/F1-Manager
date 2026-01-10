"""Race Incident System - Crashes, Safety Cars, Red Flags"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .race_engine import RaceEntry


class IncidentType(Enum):
    SPIN = "Spin"
    CRASH = "Crash"
    COLLISION = "Collision"
    MECHANICAL = "Mechanical Failure"
    PUNCTURE = "Puncture"
    BARRIER_CONTACT = "Barrier Contact"


class IncidentSeverity(Enum):
    MINOR = "Minor"      # Loses time, continues
    MODERATE = "Moderate" # May cause SC
    MAJOR = "Major"      # DNF, likely SC
    CRITICAL = "Critical" # DNF, likely Red Flag


@dataclass
class RaceIncident:
    lap: int
    incident_type: IncidentType
    severity: IncidentSeverity
    primary_driver: str  # Driver who caused/had the incident
    primary_team: str
    secondary_driver: Optional[str] = None  # Driver also involved (collisions)
    secondary_team: Optional[str] = None
    location: str = ""  # Turn/sector where it happened
    causes_safety_car: bool = False
    causes_red_flag: bool = False
    primary_dnf: bool = False
    secondary_dnf: bool = False
    description: str = ""


TRACK_LOCATIONS = [
    "Turn 1", "Turn 2", "Turn 3", "the chicane", "the hairpin",
    "the main straight", "the back straight", "the final corner",
    "the braking zone", "the pit entry", "sector 1", "sector 2", "sector 3"
]

SPIN_REASONS = [
    "pushed too hard", "lost the rear end", "ran wide", "locked up",
    "hit a kerb", "made a mistake", "got caught out by the wind"
]

COLLISION_REASONS = [
    "went for a gap that wasn't there", "misjudged the braking point",
    "squeezed too aggressively", "left no room", "made contact",
    "sent it down the inside", "tried an ambitious move"
]


class IncidentSystem:
    def __init__(self):
        self.incidents: List[RaceIncident] = []
        self.safety_car_active: bool = False
        self.safety_car_laps_remaining: int = 0
        self.red_flag_active: bool = False
        self.red_flag_restart_lap: int = 0

    def reset(self) -> None:
        """Reset for a new race."""
        self.incidents = []
        self.safety_car_active = False
        self.safety_car_laps_remaining = 0
        self.red_flag_active = False
        self.red_flag_restart_lap = 0

    def check_for_incident(
        self,
        entries: List['RaceEntry'],
        current_lap: int,
        total_laps: int,
        weather: str,
        overtaking_difficulty: int
    ) -> Optional[RaceIncident]:
        """
        Check if an incident occurs this lap.
        Returns incident if one occurs, None otherwise.
        """
        if self.red_flag_active:
            return None

        # Base incident chance (per lap, per driver effectively)
        # About 2-3 incidents per race average
        base_chance = 0.008  # 0.8% per lap

        # Weather increases incident chance significantly
        if weather == "Light Rain":
            base_chance *= 2.0
        elif weather == "Heavy Rain":
            base_chance *= 3.5

        # First lap has higher incident rate
        if current_lap == 1:
            base_chance *= 3.0
        elif current_lap <= 3:
            base_chance *= 1.5

        # Restart laps after SC are dangerous
        if self.safety_car_laps_remaining == 0 and hasattr(self, '_just_restarted') and self._just_restarted:
            base_chance *= 2.0
            self._just_restarted = False

        # Tight tracks (high overtaking difficulty) have more incidents
        if overtaking_difficulty >= 8:
            base_chance *= 1.3

        # Check if incident occurs
        if random.random() > base_chance:
            return None

        # An incident is happening - determine type and severity
        active_entries = [e for e in entries if not e.dnf]
        if not active_entries:
            return None

        # Select incident type
        incident_type = self._select_incident_type(current_lap, weather)

        # Select involved drivers
        primary, secondary = self._select_involved_drivers(
            active_entries, incident_type, current_lap
        )

        if not primary:
            return None

        # Determine severity
        severity = self._determine_severity(incident_type, weather, current_lap)

        # Generate incident details
        incident = self._create_incident(
            current_lap, incident_type, severity, primary, secondary
        )

        # Determine consequences
        self._apply_consequences(incident, primary, secondary, current_lap, total_laps)

        self.incidents.append(incident)
        return incident

    def _select_incident_type(self, current_lap: int, weather: str) -> IncidentType:
        """Select type of incident based on conditions."""
        if current_lap == 1:
            # First lap more likely to have collisions
            weights = {
                IncidentType.COLLISION: 50,
                IncidentType.SPIN: 25,
                IncidentType.CRASH: 15,
                IncidentType.BARRIER_CONTACT: 10,
            }
        elif weather in ["Light Rain", "Heavy Rain"]:
            # Wet conditions favor spins and crashes
            weights = {
                IncidentType.SPIN: 40,
                IncidentType.CRASH: 30,
                IncidentType.COLLISION: 15,
                IncidentType.BARRIER_CONTACT: 15,
            }
        else:
            weights = {
                IncidentType.SPIN: 30,
                IncidentType.COLLISION: 25,
                IncidentType.MECHANICAL: 20,
                IncidentType.CRASH: 15,
                IncidentType.PUNCTURE: 10,
            }

        types = list(weights.keys())
        probs = [weights[t] for t in types]
        return random.choices(types, weights=probs, k=1)[0]

    def _select_involved_drivers(
        self,
        entries: List['RaceEntry'],
        incident_type: IncidentType,
        current_lap: int
    ) -> Tuple[Optional['RaceEntry'], Optional['RaceEntry']]:
        """Select which drivers are involved in the incident."""
        if not entries:
            return None, None

        # Weight selection by various factors
        weights = []
        for entry in entries:
            weight = 10  # Base weight

            # Lower consistency = more likely to be involved
            weight += (100 - entry.driver.stats.consistency) * 0.3

            # Worn tires increase incident risk
            if entry.tire.wear > 60:
                weight += (entry.tire.wear - 60) * 0.2

            # Mechanical issues increase risk
            if entry.mechanical_issue:
                weight += 15

            # Midfield battles are more incident-prone
            if 5 <= entry.position <= 15:
                weight += 5

            # Aggressive drivers (high overtaking) more involved
            weight += entry.driver.stats.overtaking * 0.1

            weights.append(max(1, weight))

        # Select primary driver
        primary = random.choices(entries, weights=weights, k=1)[0]

        # For collisions, select a secondary driver nearby
        secondary = None
        if incident_type == IncidentType.COLLISION:
            # Find drivers close in position
            nearby = [
                e for e in entries
                if e != primary and abs(e.position - primary.position) <= 2
            ]
            if nearby:
                secondary = random.choice(nearby)

        return primary, secondary

    def _determine_severity(
        self,
        incident_type: IncidentType,
        weather: str,
        current_lap: int
    ) -> IncidentSeverity:
        """Determine how severe the incident is."""
        # Base severity weights by type
        if incident_type == IncidentType.SPIN:
            weights = {
                IncidentSeverity.MINOR: 60,
                IncidentSeverity.MODERATE: 30,
                IncidentSeverity.MAJOR: 10,
            }
        elif incident_type == IncidentType.COLLISION:
            weights = {
                IncidentSeverity.MINOR: 30,
                IncidentSeverity.MODERATE: 40,
                IncidentSeverity.MAJOR: 25,
                IncidentSeverity.CRITICAL: 5,
            }
        elif incident_type == IncidentType.CRASH:
            weights = {
                IncidentSeverity.MODERATE: 30,
                IncidentSeverity.MAJOR: 50,
                IncidentSeverity.CRITICAL: 20,
            }
        elif incident_type == IncidentType.BARRIER_CONTACT:
            weights = {
                IncidentSeverity.MINOR: 20,
                IncidentSeverity.MODERATE: 35,
                IncidentSeverity.MAJOR: 35,
                IncidentSeverity.CRITICAL: 10,
            }
        else:  # Mechanical, Puncture
            weights = {
                IncidentSeverity.MINOR: 40,
                IncidentSeverity.MODERATE: 40,
                IncidentSeverity.MAJOR: 20,
            }

        # Weather increases severity chance
        if weather == "Heavy Rain":
            if IncidentSeverity.MAJOR in weights:
                weights[IncidentSeverity.MAJOR] = weights.get(IncidentSeverity.MAJOR, 0) + 20
            if IncidentSeverity.CRITICAL in weights:
                weights[IncidentSeverity.CRITICAL] = weights.get(IncidentSeverity.CRITICAL, 0) + 10

        severities = list(weights.keys())
        probs = [weights[s] for s in severities]
        return random.choices(severities, weights=probs, k=1)[0]

    def _create_incident(
        self,
        lap: int,
        incident_type: IncidentType,
        severity: IncidentSeverity,
        primary: 'RaceEntry',
        secondary: Optional['RaceEntry']
    ) -> RaceIncident:
        """Create incident with description."""
        location = random.choice(TRACK_LOCATIONS)

        # Generate description
        if incident_type == IncidentType.SPIN:
            reason = random.choice(SPIN_REASONS)
            description = f"{primary.driver.name} {reason} at {location}!"
        elif incident_type == IncidentType.COLLISION:
            if secondary:
                reason = random.choice(COLLISION_REASONS)
                description = f"{primary.driver.name} and {secondary.driver.name} make contact at {location}! {primary.driver.name} {reason}."
            else:
                description = f"{primary.driver.name} has contact with another car at {location}!"
        elif incident_type == IncidentType.CRASH:
            description = f"{primary.driver.name} has crashed at {location}!"
        elif incident_type == IncidentType.BARRIER_CONTACT:
            description = f"{primary.driver.name} has hit the barrier at {location}!"
        elif incident_type == IncidentType.MECHANICAL:
            failures = ["engine", "gearbox", "brakes", "hydraulics", "suspension"]
            failure = random.choice(failures)
            description = f"{primary.driver.name} suffers {failure} failure!"
        elif incident_type == IncidentType.PUNCTURE:
            description = f"{primary.driver.name} has a puncture! Slow lap back to the pits."
        else:
            description = f"Incident involving {primary.driver.name} at {location}!"

        return RaceIncident(
            lap=lap,
            incident_type=incident_type,
            severity=severity,
            primary_driver=primary.driver.name,
            primary_team=primary.team.name,
            secondary_driver=secondary.driver.name if secondary else None,
            secondary_team=secondary.team.name if secondary else None,
            location=location,
            description=description
        )

    def _apply_consequences(
        self,
        incident: RaceIncident,
        primary: 'RaceEntry',
        secondary: Optional['RaceEntry'],
        current_lap: int,
        total_laps: int
    ) -> None:
        """Apply consequences based on severity."""
        # DNF chances by severity
        dnf_chances = {
            IncidentSeverity.MINOR: 0.0,
            IncidentSeverity.MODERATE: 0.15,
            IncidentSeverity.MAJOR: 0.7,
            IncidentSeverity.CRITICAL: 0.95,
        }

        # Safety car chances
        sc_chances = {
            IncidentSeverity.MINOR: 0.02,
            IncidentSeverity.MODERATE: 0.15,
            IncidentSeverity.MAJOR: 0.6,
            IncidentSeverity.CRITICAL: 0.85,
        }

        # Red flag chances (only for critical, and not near end of race)
        rf_chances = {
            IncidentSeverity.MINOR: 0.0,
            IncidentSeverity.MODERATE: 0.0,
            IncidentSeverity.MAJOR: 0.05,
            IncidentSeverity.CRITICAL: 0.3,
        }

        # Apply primary driver consequences
        if random.random() < dnf_chances[incident.severity]:
            incident.primary_dnf = True
            primary.dnf = True
            primary.dnf_reason = incident.description
        else:
            # Time loss instead of DNF
            time_loss = {
                IncidentSeverity.MINOR: random.uniform(2, 8),
                IncidentSeverity.MODERATE: random.uniform(5, 15),
                IncidentSeverity.MAJOR: random.uniform(10, 30),
                IncidentSeverity.CRITICAL: random.uniform(20, 60),
            }
            primary.total_time += time_loss[incident.severity]

        # Apply secondary driver consequences (collisions)
        if secondary:
            # Secondary has lower chance of DNF (wasn't at fault usually)
            if random.random() < dnf_chances[incident.severity] * 0.6:
                incident.secondary_dnf = True
                secondary.dnf = True
                secondary.dnf_reason = f"Collision damage from contact with {primary.driver.name}"
            else:
                # Time loss
                secondary.total_time += random.uniform(2, 15)

        # Determine if this causes SC or Red Flag
        # Don't deploy SC/Red in final 5 laps usually
        laps_remaining = total_laps - current_lap

        if laps_remaining > 2 and random.random() < rf_chances[incident.severity]:
            incident.causes_red_flag = True
            self.red_flag_active = True
            self.red_flag_restart_lap = current_lap + random.randint(3, 5)
        elif laps_remaining > 3 and random.random() < sc_chances[incident.severity]:
            if not self.safety_car_active:
                incident.causes_safety_car = True
                self.safety_car_active = True
                self.safety_car_laps_remaining = random.randint(2, 4)

    def update_safety_car(self) -> Tuple[bool, Optional[str]]:
        """
        Update safety car status each lap.
        Returns (still_active, message)
        """
        if not self.safety_car_active:
            return False, None

        self.safety_car_laps_remaining -= 1

        if self.safety_car_laps_remaining <= 0:
            self.safety_car_active = False
            self._just_restarted = True
            return False, "SAFETY CAR IN - RACING RESUMES!"

        return True, None

    def update_red_flag(self, current_lap: int) -> Tuple[bool, Optional[str]]:
        """
        Update red flag status.
        Returns (still_active, message)
        """
        if not self.red_flag_active:
            return False, None

        if current_lap >= self.red_flag_restart_lap:
            self.red_flag_active = False
            return False, "RED FLAG LIFTED - RACE RESTART!"

        return True, f"Race suspended. Restart expected in {self.red_flag_restart_lap - current_lap} lap(s)."

    def get_incident_summary(self) -> str:
        """Get summary of all incidents in the race."""
        if not self.incidents:
            return "No major incidents during the race."

        lines = ["RACE INCIDENTS:"]
        for incident in self.incidents:
            flag_info = ""
            if incident.causes_red_flag:
                flag_info = " [RED FLAG]"
            elif incident.causes_safety_car:
                flag_info = " [SAFETY CAR]"

            dnf_info = ""
            if incident.primary_dnf:
                dnf_info = f" - {incident.primary_driver} OUT"
            if incident.secondary_dnf and incident.secondary_driver:
                dnf_info += f", {incident.secondary_driver} OUT"

            lines.append(f"  Lap {incident.lap}: {incident.description}{flag_info}{dnf_info}")

        return "\n".join(lines)
