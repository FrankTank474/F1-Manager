"""Driver Rivalry System - Track interactions and create on-track drama"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional


class InteractionType(Enum):
    COLLISION = "Collision"           # Crash or contact
    AGGRESSIVE_MOVE = "Aggressive Move"  # Divebomb, squeeze, etc.
    OVERTAKE_BATTLE = "Overtake Battle"  # Extended wheel-to-wheel
    TEAM_ORDERS = "Team Orders"       # Being told to let teammate pass
    CHAMPIONSHIP_TENSION = "Championship Tension"  # Close in standings


@dataclass
class Interaction:
    """A single interaction between two drivers."""
    driver1: str
    driver2: str
    interaction_type: InteractionType
    lap: int
    race: str
    aggressor: Optional[str] = None  # Who was at fault/aggressive
    description: str = ""


@dataclass
class Rivalry:
    """A rivalry between two drivers."""
    driver1: str
    driver2: str
    intensity: int = 0  # 0-100, higher = more intense rivalry
    interactions: List[Interaction] = field(default_factory=list)
    last_interaction_race: int = 0  # Track when last interaction was

    def add_interaction(self, interaction: Interaction, race_number: int) -> None:
        """Add an interaction and increase intensity."""
        self.interactions.append(interaction)
        self.last_interaction_race = race_number

        # Increase intensity based on interaction type
        intensity_gain = {
            InteractionType.COLLISION: 25,
            InteractionType.AGGRESSIVE_MOVE: 15,
            InteractionType.OVERTAKE_BATTLE: 8,
            InteractionType.TEAM_ORDERS: 12,
            InteractionType.CHAMPIONSHIP_TENSION: 5,
        }
        self.intensity = min(100, self.intensity + intensity_gain[interaction.interaction_type])

    def decay_intensity(self, current_race: int) -> None:
        """Reduce intensity over time if no interactions."""
        races_since = current_race - self.last_interaction_race
        if races_since > 0:
            # Decay 5 points per race without interaction
            self.intensity = max(0, self.intensity - (races_since * 5))

    @property
    def level(self) -> str:
        """Get rivalry level description."""
        if self.intensity >= 80:
            return "FIERCE"
        elif self.intensity >= 60:
            return "HEATED"
        elif self.intensity >= 40:
            return "TENSE"
        elif self.intensity >= 20:
            return "BREWING"
        else:
            return "NEUTRAL"


class RivalryManager:
    def __init__(self):
        self.rivalries: Dict[Tuple[str, str], Rivalry] = {}
        self.current_race_number: int = 0

    def _get_rivalry_key(self, driver1: str, driver2: str) -> Tuple[str, str]:
        """Get consistent key for driver pair."""
        return tuple(sorted([driver1, driver2]))

    def get_rivalry(self, driver1: str, driver2: str) -> Rivalry:
        """Get or create rivalry between two drivers."""
        key = self._get_rivalry_key(driver1, driver2)
        if key not in self.rivalries:
            self.rivalries[key] = Rivalry(driver1=key[0], driver2=key[1])
        return self.rivalries[key]

    def get_rivalry_intensity(self, driver1: str, driver2: str) -> int:
        """Get intensity of rivalry between two drivers."""
        key = self._get_rivalry_key(driver1, driver2)
        if key in self.rivalries:
            return self.rivalries[key].intensity
        return 0

    def record_collision(
        self,
        driver1: str,
        driver2: str,
        race_name: str,
        lap: int,
        aggressor: Optional[str] = None
    ) -> str:
        """Record a collision between drivers."""
        rivalry = self.get_rivalry(driver1, driver2)

        descriptions = [
            f"{driver1} and {driver2} came together",
            f"Contact between {driver1} and {driver2}",
            f"{driver1} and {driver2} collided",
            f"A clash between {driver1} and {driver2}",
        ]

        interaction = Interaction(
            driver1=driver1,
            driver2=driver2,
            interaction_type=InteractionType.COLLISION,
            lap=lap,
            race=race_name,
            aggressor=aggressor,
            description=random.choice(descriptions)
        )

        rivalry.add_interaction(interaction, self.current_race_number)

        return self._get_rivalry_message(rivalry)

    def record_aggressive_move(
        self,
        aggressor: str,
        defender: str,
        race_name: str,
        lap: int
    ) -> Optional[str]:
        """Record an aggressive overtake attempt."""
        rivalry = self.get_rivalry(aggressor, defender)

        descriptions = [
            f"{aggressor} made an aggressive move on {defender}",
            f"{aggressor} sent it on {defender}",
            f"Divebomb by {aggressor} on {defender}",
            f"{aggressor} squeezed {defender} off track",
        ]

        interaction = Interaction(
            driver1=aggressor,
            driver2=defender,
            interaction_type=InteractionType.AGGRESSIVE_MOVE,
            lap=lap,
            race=race_name,
            aggressor=aggressor,
            description=random.choice(descriptions)
        )

        rivalry.add_interaction(interaction, self.current_race_number)

        # Only return message if rivalry is notable
        if rivalry.intensity >= 30:
            return self._get_rivalry_message(rivalry)
        return None

    def record_battle(
        self,
        driver1: str,
        driver2: str,
        race_name: str,
        lap: int,
        laps_battling: int = 1
    ) -> Optional[str]:
        """Record an extended wheel-to-wheel battle."""
        if laps_battling < 3:
            return None  # Only track significant battles

        rivalry = self.get_rivalry(driver1, driver2)

        descriptions = [
            f"{driver1} and {driver2} had an epic {laps_battling}-lap battle",
            f"Wheel-to-wheel racing between {driver1} and {driver2}",
            f"{driver1} and {driver2} fought hard for position",
        ]

        interaction = Interaction(
            driver1=driver1,
            driver2=driver2,
            interaction_type=InteractionType.OVERTAKE_BATTLE,
            lap=lap,
            race=race_name,
            description=random.choice(descriptions)
        )

        rivalry.add_interaction(interaction, self.current_race_number)

        if rivalry.intensity >= 30:
            return self._get_rivalry_message(rivalry)
        return None

    def check_championship_rivalry(
        self,
        driver1: str,
        driver1_points: int,
        driver2: str,
        driver2_points: int
    ) -> Optional[str]:
        """Check for championship-based rivalry."""
        points_gap = abs(driver1_points - driver2_points)

        # Only create tension if very close in championship
        if points_gap > 30:
            return None

        rivalry = self.get_rivalry(driver1, driver2)

        # Add championship tension
        if rivalry.intensity < 50:  # Don't stack too much
            interaction = Interaction(
                driver1=driver1,
                driver2=driver2,
                interaction_type=InteractionType.CHAMPIONSHIP_TENSION,
                lap=0,
                race="Championship",
                description=f"Championship battle brewing - only {points_gap} points separate them"
            )
            rivalry.add_interaction(interaction, self.current_race_number)

        if rivalry.intensity >= 40 and points_gap <= 15:
            return f"CHAMPIONSHIP BATTLE: {driver1} and {driver2} are separated by just {points_gap} points!"

        return None

    def _get_rivalry_message(self, rivalry: Rivalry) -> str:
        """Generate a message about the rivalry state."""
        level = rivalry.level
        if level == "FIERCE":
            messages = [
                f"FIERCE RIVALRY! {rivalry.driver1} vs {rivalry.driver2} - this is getting personal!",
                f"Bad blood between {rivalry.driver1} and {rivalry.driver2}!",
                f"The {rivalry.driver1}/{rivalry.driver2} rivalry reaches boiling point!",
            ]
        elif level == "HEATED":
            messages = [
                f"HEATED: Tensions rising between {rivalry.driver1} and {rivalry.driver2}",
                f"{rivalry.driver1} and {rivalry.driver2} - this rivalry is heating up!",
            ]
        elif level == "TENSE":
            messages = [
                f"TENSE: {rivalry.driver1} and {rivalry.driver2} are developing a rivalry",
                f"Watch out - {rivalry.driver1} vs {rivalry.driver2} is becoming a storyline",
            ]
        elif level == "BREWING":
            messages = [
                f"A rivalry may be brewing between {rivalry.driver1} and {rivalry.driver2}",
            ]
        else:
            return ""

        return random.choice(messages)

    def get_battle_intensity_modifier(self, driver1: str, driver2: str) -> float:
        """
        Get modifier for overtake attempts based on rivalry.
        Rivals are more aggressive but also more likely to crash.
        """
        intensity = self.get_rivalry_intensity(driver1, driver2)

        # Higher intensity = more aggressive battles
        # Returns a modifier for overtake probability
        return 1.0 + (intensity / 200)  # Up to 1.5x at max rivalry

    def get_crash_risk_modifier(self, driver1: str, driver2: str) -> float:
        """
        Get modifier for crash risk when rivals are battling.
        """
        intensity = self.get_rivalry_intensity(driver1, driver2)

        # Higher intensity = more likely to crash when battling
        return 1.0 + (intensity / 100)  # Up to 2x at max rivalry

    def advance_race(self) -> None:
        """Called at end of each race to decay rivalries."""
        self.current_race_number += 1

        for rivalry in self.rivalries.values():
            rivalry.decay_intensity(self.current_race_number)

    def get_active_rivalries(self, min_intensity: int = 30) -> List[Rivalry]:
        """Get all rivalries above a certain intensity."""
        return [
            r for r in self.rivalries.values()
            if r.intensity >= min_intensity
        ]

    def display_rivalries(self) -> str:
        """Display current active rivalries."""
        active = self.get_active_rivalries(20)

        if not active:
            return "No notable driver rivalries currently."

        # Sort by intensity
        active.sort(key=lambda r: r.intensity, reverse=True)

        lines = [
            "\n" + "=" * 60,
            "  DRIVER RIVALRIES",
            "=" * 60,
        ]

        for rivalry in active:
            level_colors = {
                "FIERCE": "***",
                "HEATED": "** ",
                "TENSE": "*  ",
                "BREWING": "   ",
            }
            indicator = level_colors.get(rivalry.level, "   ")
            lines.append(
                f"  {indicator} {rivalry.driver1} vs {rivalry.driver2} [{rivalry.level}] "
                f"({len(rivalry.interactions)} incidents)"
            )

        lines.append("=" * 60)
        lines.append("  *** = Fierce  ** = Heated  * = Tense")

        return "\n".join(lines)

    def get_race_drama_potential(self, drivers: List[str]) -> List[Tuple[str, str, int]]:
        """
        Get pairs of drivers with high rivalry who are racing today.
        Useful for pre-race drama predictions.
        """
        drama = []

        for i, d1 in enumerate(drivers):
            for d2 in drivers[i+1:]:
                intensity = self.get_rivalry_intensity(d1, d2)
                if intensity >= 30:
                    drama.append((d1, d2, intensity))

        drama.sort(key=lambda x: x[2], reverse=True)
        return drama[:5]  # Top 5 potential battles
