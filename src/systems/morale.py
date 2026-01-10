"""Driver Morale & Confidence System"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Driver, Team


class MoraleLevel(Enum):
    ECSTATIC = "Ecstatic"      # 90-100
    HAPPY = "Happy"            # 75-89
    CONTENT = "Content"        # 60-74
    NEUTRAL = "Neutral"        # 45-59
    UNSETTLED = "Unsettled"    # 30-44
    UNHAPPY = "Unhappy"        # 15-29
    FURIOUS = "Furious"        # 0-14


@dataclass
class MoraleEvent:
    """An event that affects morale."""
    description: str
    morale_change: int
    race_number: int


@dataclass
class DriverMorale:
    """Tracks morale for a single driver."""
    driver_name: str
    morale: int = 70  # 0-100, starts at content
    confidence: int = 70  # 0-100, affects race performance
    recent_events: List[MoraleEvent] = field(default_factory=list)

    # Streak tracking
    win_streak: int = 0
    podium_streak: int = 0
    points_streak: int = 0
    no_points_streak: int = 0
    dnf_streak: int = 0
    beaten_by_teammate_streak: int = 0

    # Season stats for morale
    times_beaten_by_teammate: int = 0
    teammate_comparison_points: int = 0  # Positive = ahead, negative = behind

    @property
    def level(self) -> MoraleLevel:
        """Get current morale level."""
        if self.morale >= 90:
            return MoraleLevel.ECSTATIC
        elif self.morale >= 75:
            return MoraleLevel.HAPPY
        elif self.morale >= 60:
            return MoraleLevel.CONTENT
        elif self.morale >= 45:
            return MoraleLevel.NEUTRAL
        elif self.morale >= 30:
            return MoraleLevel.UNSETTLED
        elif self.morale >= 15:
            return MoraleLevel.UNHAPPY
        else:
            return MoraleLevel.FURIOUS

    @property
    def performance_modifier(self) -> float:
        """
        Get performance modifier based on morale and confidence.
        Returns a multiplier (0.95 to 1.05) that affects lap times.
        High morale = faster, low morale = slower.
        """
        # Morale effect (subtle but meaningful)
        morale_effect = (self.morale - 50) / 500  # -0.1 to +0.1

        # Confidence effect (affects consistency more)
        confidence_effect = (self.confidence - 50) / 1000  # -0.05 to +0.05

        # Combined: ranges from about 0.95 to 1.05
        return 1.0 + morale_effect + confidence_effect

    @property
    def consistency_modifier(self) -> float:
        """
        Get consistency modifier based on confidence.
        Low confidence = more random variance in performance.
        """
        # At 100 confidence, variance is reduced by 30%
        # At 0 confidence, variance is increased by 30%
        return 1.0 - ((self.confidence - 50) / 166.67)  # 0.7 to 1.3

    def add_event(self, description: str, change: int, race_number: int) -> None:
        """Add a morale event."""
        self.morale = max(0, min(100, self.morale + change))
        self.recent_events.append(MoraleEvent(description, change, race_number))
        # Keep only last 10 events
        if len(self.recent_events) > 10:
            self.recent_events = self.recent_events[-10:]

    def update_confidence(self) -> None:
        """Update confidence based on morale and streaks."""
        # Confidence trends toward morale over time
        if self.confidence < self.morale:
            self.confidence = min(self.confidence + 2, self.morale)
        elif self.confidence > self.morale:
            self.confidence = max(self.confidence - 2, self.morale)

        # Streaks affect confidence more directly
        if self.win_streak >= 2:
            self.confidence = min(100, self.confidence + self.win_streak * 2)
        if self.dnf_streak >= 2:
            self.confidence = max(0, self.confidence - self.dnf_streak * 3)
        if self.beaten_by_teammate_streak >= 3:
            self.confidence = max(0, self.confidence - 5)

    def reset_season(self) -> None:
        """Reset seasonal tracking."""
        self.times_beaten_by_teammate = 0
        self.teammate_comparison_points = 0
        # Don't reset morale/confidence - carries over


class MoraleManager:
    """Manages morale for all drivers."""

    def __init__(self):
        self.driver_morale: Dict[str, DriverMorale] = {}
        self.current_race: int = 0

    def get_morale(self, driver_name: str) -> DriverMorale:
        """Get or create morale tracker for a driver."""
        if driver_name not in self.driver_morale:
            self.driver_morale[driver_name] = DriverMorale(driver_name=driver_name)
        return self.driver_morale[driver_name]

    def process_race_result(
        self,
        driver: 'Driver',
        team: 'Team',
        position: int,
        teammate_position: int,
        was_dnf: bool = False
    ) -> List[str]:
        """
        Process race result and update morale.
        Returns list of morale change messages.
        """
        messages = []
        morale = self.get_morale(driver.name)

        # === HANDLE DNF ===
        if was_dnf or position <= 0:
            morale.dnf_streak += 1
            morale.win_streak = 0
            morale.podium_streak = 0
            morale.points_streak = 0

            change = -8
            if morale.dnf_streak >= 2:
                change -= morale.dnf_streak * 2
                messages.append(f"{driver.name} is frustrated after {morale.dnf_streak} consecutive DNFs")

            morale.add_event("DNF", change, self.current_race)
            morale.no_points_streak += 1
            morale.update_confidence()
            return messages

        # Reset DNF streak on finish
        morale.dnf_streak = 0

        # === WIN ===
        if position == 1:
            morale.win_streak += 1
            morale.podium_streak += 1
            morale.points_streak += 1
            morale.no_points_streak = 0

            base_change = 15
            if morale.win_streak >= 2:
                base_change += morale.win_streak * 3
                messages.append(f"{driver.name} is on fire with {morale.win_streak} consecutive wins!")

            morale.add_event("Race win!", base_change, self.current_race)

        # === PODIUM ===
        elif position <= 3:
            morale.win_streak = 0
            morale.podium_streak += 1
            morale.points_streak += 1
            morale.no_points_streak = 0

            change = 8 + (4 - position) * 2  # P2=12, P3=10
            if morale.podium_streak >= 3:
                change += 3
                messages.append(f"{driver.name} is in great form with {morale.podium_streak} consecutive podiums")

            morale.add_event(f"P{position} podium", change, self.current_race)

        # === POINTS FINISH ===
        elif position <= 10:
            morale.win_streak = 0
            morale.podium_streak = 0
            morale.points_streak += 1
            morale.no_points_streak = 0

            change = 4 + (10 - position)  # P4=10, P10=4
            morale.add_event(f"P{position} points finish", change, self.current_race)

        # === NO POINTS ===
        else:
            morale.win_streak = 0
            morale.podium_streak = 0
            morale.points_streak = 0
            morale.no_points_streak += 1

            change = -3
            if morale.no_points_streak >= 3:
                change -= morale.no_points_streak
                messages.append(f"{driver.name} is struggling after {morale.no_points_streak} races without points")

            morale.add_event(f"P{position} no points", change, self.current_race)

        # === TEAMMATE COMPARISON ===
        if teammate_position > 0:  # Teammate finished
            if position < teammate_position:
                # Beat teammate
                morale.beaten_by_teammate_streak = 0
                morale.add_event("Beat teammate", 3, self.current_race)
            elif position > teammate_position:
                # Beaten by teammate
                morale.beaten_by_teammate_streak += 1
                morale.times_beaten_by_teammate += 1

                change = -4
                if morale.beaten_by_teammate_streak >= 3:
                    change -= morale.beaten_by_teammate_streak
                    messages.append(f"{driver.name} is frustrated after being beaten by teammate {morale.beaten_by_teammate_streak} times in a row")

                morale.add_event("Beaten by teammate", change, self.current_race)

        # Update confidence
        morale.update_confidence()

        return messages

    def process_contract_event(
        self,
        driver_name: str,
        event_type: str,
        positive: bool
    ) -> None:
        """Process contract-related morale changes."""
        morale = self.get_morale(driver_name)

        if event_type == "new_contract":
            if positive:
                morale.add_event("Signed new contract", 15, self.current_race)
            else:
                morale.add_event("Contract demands rejected", -20, self.current_race)
        elif event_type == "number_one_status":
            if positive:
                morale.add_event("Given #1 driver status", 10, self.current_race)
            else:
                morale.add_event("Denied #1 status", -10, self.current_race)
        elif event_type == "salary_increase":
            if positive:
                morale.add_event("Received salary increase", 8, self.current_race)
            else:
                morale.add_event("Salary increase rejected", -12, self.current_race)
        elif event_type == "teammate_favored":
            morale.add_event("Feels teammate is favored", -8, self.current_race)

        morale.update_confidence()

    def apply_team_success(self, driver_name: str, constructor_position: int) -> None:
        """Apply morale bonus/penalty based on team success."""
        morale = self.get_morale(driver_name)

        if constructor_position == 1:
            morale.add_event("Team won constructor championship!", 20, self.current_race)
        elif constructor_position <= 3:
            morale.add_event("Team finished top 3 in championship", 10, self.current_race)
        elif constructor_position >= 9:
            morale.add_event("Disappointed with team's season", -5, self.current_race)

        morale.update_confidence()

    def natural_decay(self) -> None:
        """Apply natural morale drift toward neutral (50)."""
        for morale in self.driver_morale.values():
            if morale.morale > 55:
                morale.morale -= 1
            elif morale.morale < 45:
                morale.morale += 1
            morale.update_confidence()

    def advance_race(self) -> None:
        """Called at end of each race."""
        self.current_race += 1
        self.natural_decay()

    def reset_season(self) -> None:
        """Reset seasonal stats for all drivers."""
        for morale in self.driver_morale.values():
            morale.reset_season()

    def display_driver_morale(self, driver_name: str) -> str:
        """Display morale info for a driver."""
        morale = self.get_morale(driver_name)

        # Morale bar visualization
        bar_filled = int(morale.morale / 5)
        bar_empty = 20 - bar_filled
        morale_bar = "[" + "=" * bar_filled + " " * bar_empty + "]"

        # Confidence bar
        conf_filled = int(morale.confidence / 5)
        conf_empty = 20 - conf_filled
        conf_bar = "[" + "=" * conf_filled + " " * conf_empty + "]"

        lines = [
            f"\n  {driver_name} - Mental State",
            "-" * 50,
            f"  Morale:     {morale_bar} {morale.morale}/100 ({morale.level.value})",
            f"  Confidence: {conf_bar} {morale.confidence}/100",
            "",
            f"  Performance Impact: {(morale.performance_modifier - 1) * 100:+.1f}%",
            "",
            "  STREAKS:",
        ]

        if morale.win_streak > 0:
            lines.append(f"    Win streak: {morale.win_streak}")
        if morale.podium_streak > 0:
            lines.append(f"    Podium streak: {morale.podium_streak}")
        if morale.points_streak > 0:
            lines.append(f"    Points streak: {morale.points_streak}")
        if morale.no_points_streak > 0:
            lines.append(f"    Races without points: {morale.no_points_streak}")
        if morale.dnf_streak > 0:
            lines.append(f"    DNF streak: {morale.dnf_streak}")
        if morale.beaten_by_teammate_streak > 0:
            lines.append(f"    Beaten by teammate: {morale.beaten_by_teammate_streak} in a row")

        if morale.recent_events:
            lines.append("")
            lines.append("  RECENT EVENTS:")
            for event in morale.recent_events[-5:]:
                sign = "+" if event.morale_change >= 0 else ""
                lines.append(f"    Race {event.race_number}: {event.description} ({sign}{event.morale_change})")

        return "\n".join(lines)

    def get_team_morale_summary(self, driver_names: List[str]) -> str:
        """Get summary of team morale."""
        lines = [
            "\n" + "=" * 50,
            "  TEAM MORALE",
            "=" * 50,
        ]

        for name in driver_names:
            morale = self.get_morale(name)

            # Status indicator
            if morale.morale >= 75:
                status = "[HAPPY]"
            elif morale.morale >= 45:
                status = "[OK]"
            elif morale.morale >= 25:
                status = "[UNHAPPY]"
            else:
                status = "[CRITICAL]"

            lines.append(f"  {name}: {morale.morale}/100 {status}")

            # Warning flags
            if morale.beaten_by_teammate_streak >= 3:
                lines.append(f"    ! Frustrated with teammate comparison")
            if morale.no_points_streak >= 4:
                lines.append(f"    ! Struggling for results")
            if morale.morale < 30:
                lines.append(f"    ! At risk of demanding team changes")

        lines.append("=" * 50)
        return "\n".join(lines)
