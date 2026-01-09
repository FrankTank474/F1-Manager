from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import random


@dataclass
class DriverStats:
    pace: int  # Raw speed (1-100)
    overtaking: int  # Ability to pass other cars (1-100)
    defending: int  # Ability to hold position (1-100)
    consistency: int  # Reduces random errors (1-100)
    tire_management: int  # How well they preserve tires (1-100)
    wet_skill: int  # Performance in rain (1-100)

    @property
    def overall(self) -> int:
        return int(
            (self.pace * 0.25)
            + (self.overtaking * 0.15)
            + (self.defending * 0.15)
            + (self.consistency * 0.20)
            + (self.tire_management * 0.15)
            + (self.wet_skill * 0.10)
        )

    def get_stat_names(self) -> List[str]:
        return ['pace', 'overtaking', 'defending', 'consistency', 'tire_management', 'wet_skill']

    def upgrade_stat(self, stat_name: str, amount: int) -> None:
        """Upgrade a specific stat by amount, capped at 99."""
        current = getattr(self, stat_name)
        setattr(self, stat_name, min(99, current + amount))

    def degrade_stat(self, stat_name: str, amount: int) -> None:
        """Degrade a specific stat by amount, minimum 50."""
        current = getattr(self, stat_name)
        setattr(self, stat_name, max(50, current - amount))


@dataclass
class Driver:
    name: str
    age: int
    nationality: str
    stats: DriverStats
    salary: int  # Per season in millions
    market_value: int  # Transfer fee in millions
    potential: int = 0  # Potential rating (what they could become) - 0 means auto-calculate
    team_name: Optional[str] = None
    season_points: int = 0
    race_wins: int = 0
    podiums: int = 0
    dnfs: int = 0
    total_finishes: int = 0  # Number of races finished (for avg position calc)
    total_positions: int = 0  # Sum of finishing positions (for avg position calc)
    rising_star_races: int = 0  # Races remaining with rising star bonus growth
    season_best_finish: int = 99  # Best finish this season (for rising star tracking)

    def __str__(self) -> str:
        return f"{self.name} ({self.nationality}, {self.age})"

    def get_stats_display(self) -> str:
        s = self.stats
        potential_display = self.get_potential()
        rising_star = " [RISING STAR]" if self.rising_star_races > 0 else ""
        return (
            f"  Pace: {s.pace}  |  Overtaking: {s.overtaking}  |  Defending: {s.defending}\n"
            f"  Consistency: {s.consistency}  |  Tire Mgmt: {s.tire_management}  |  Wet: {s.wet_skill}\n"
            f"  Overall: {s.overall}  |  Potential: {potential_display}{rising_star}"
        )

    def get_potential(self) -> int:
        """Get driver's potential rating. Auto-calculated and cached if not set."""
        if self.potential > 0:
            return self.potential
        # Auto-calculate potential based on current stats and age, then cache it
        current = self.stats.overall
        if self.age < 23:
            # Young drivers have high potential ceiling
            self.potential = min(99, current + random.randint(8, 15))
        elif self.age <= 26:
            self.potential = min(99, current + random.randint(4, 10))
        elif self.age <= 30:
            self.potential = min(99, current + random.randint(1, 5))
        else:
            # Older drivers are close to their peak already
            self.potential = min(99, current + random.randint(0, 2))
        return self.potential

    def reset_season_stats(self) -> None:
        self.season_points = 0
        self.race_wins = 0
        self.podiums = 0
        self.dnfs = 0
        self.total_finishes = 0
        self.total_positions = 0
        self.season_best_finish = 99
        # Don't reset rising_star_races - it carries over

    def get_average_position(self) -> float:
        """Get average finishing position. Lower is better. Returns 99 if no finishes."""
        if self.total_finishes == 0:
            return 99.0
        return self.total_positions / self.total_finishes

    def record_finish(self, position: int) -> None:
        """Record a race finish for average position calculation."""
        if position > 0:
            self.total_finishes += 1
            self.total_positions += position
            # Track best finish for rising star
            if position < self.season_best_finish:
                self.season_best_finish = position

    def check_rising_star(self, position: int, car_rating: int) -> bool:
        """
        Check if this finish qualifies for rising star status.
        Young drivers (under 27) who outperform their car get rising star boost.
        Returns True if rising star status was activated.
        """
        if self.age >= 27:
            return False  # Only young drivers can be rising stars

        # Calculate expected position based on car rating
        # Top car (90+) expected P1-5, mid car (70-80) expected P8-15, backmarker P15-20
        if car_rating >= 85:
            expected_position = 5
        elif car_rating >= 75:
            expected_position = 10
        elif car_rating >= 65:
            expected_position = 14
        else:
            expected_position = 17

        # Outperforming by 3+ positions triggers rising star
        if position > 0 and position <= expected_position - 3:
            self.rising_star_races = 5  # 5 races of bonus growth
            return True

        # Podium always triggers rising star for young driver in non-top car
        if position <= 3 and car_rating < 85:
            self.rising_star_races = 5
            return True

        # Win always triggers rising star for young driver
        if position == 1:
            self.rising_star_races = 5
            return True

        return False

    def tick_rising_star(self) -> None:
        """Decrement rising star counter after a race."""
        if self.rising_star_races > 0:
            self.rising_star_races -= 1

    def is_free_agent(self) -> bool:
        return self.team_name is None

    def sign_with_team(self, team_name: str) -> None:
        self.team_name = team_name

    def release_from_team(self) -> None:
        self.team_name = None

    def age_up(self) -> None:
        """Increase driver age by 1 year."""
        self.age += 1

    def develop_stats(self, had_good_season: bool = False) -> List[Tuple[str, int, int]]:
        """
        Develop driver stats based on age and performance.
        Returns list of (stat_name, old_value, new_value).

        Age brackets:
        - Under 23: High growth potential (1-3 points per stat, 60% chance each)
        - 23-26: Good growth (1-2 points per stat, 50% chance each)
        - 27-30: Stable/slight growth (0-1 points, 30% chance each)
        - 31-34: Stable/slight decline (0-1 decline, 25% chance each)
        - 35+: Decline phase (1-2 decline, 40% chance each, but experience stats stay)

        had_good_season: If True and under 27, extra growth bonus
        """
        changes = []
        stats = self.stats
        stat_names = stats.get_stat_names()

        # Experience-based stats that don't decline as much with age
        experience_stats = ['defending', 'tire_management', 'consistency']

        # Calculate performance bonus for young drivers
        performance_bonus = 0
        if self.age < 27 and had_good_season:
            performance_bonus = 0.15  # 15% extra chance for each stat

        for stat_name in stat_names:
            old_value = getattr(stats, stat_name)
            new_value = old_value

            if self.age < 23:
                # Young talent - high growth
                if random.random() < 0.60 + performance_bonus:
                    growth = random.randint(1, 3)
                    if had_good_season:
                        growth += 1  # Extra point for good performance
                    new_value = min(99, old_value + growth)
            elif self.age <= 26:
                # Prime development years
                if random.random() < 0.50 + performance_bonus:
                    growth = random.randint(1, 2)
                    if had_good_season:
                        growth += 1  # Extra point for good performance
                    new_value = min(99, old_value + growth)
            elif self.age <= 30:
                # Peak years - stable with slight growth
                if random.random() < 0.30:
                    growth = random.randint(0, 1)
                    new_value = min(99, old_value + growth)
            elif self.age <= 34:
                # Late career - slight decline possible
                if stat_name not in experience_stats:
                    if random.random() < 0.25:
                        decline = random.randint(0, 1)
                        new_value = max(50, old_value - decline)
                # Experience stats can still grow slightly
                elif random.random() < 0.20:
                    new_value = min(99, old_value + 1)
            else:
                # Veteran decline - physical stats drop, experience helps
                if stat_name in experience_stats:
                    # Experience stats stable or slight decline
                    if random.random() < 0.15:
                        new_value = max(60, old_value - 1)
                else:
                    # Physical stats decline more
                    if random.random() < 0.40:
                        decline = random.randint(1, 2)
                        new_value = max(50, old_value - decline)

            if new_value != old_value:
                setattr(stats, stat_name, new_value)
                changes.append((stat_name, old_value, new_value))

        # Update market value based on overall change and age
        self._update_market_value()

        return changes

    def apply_rising_star_growth(self) -> List[Tuple[str, int, int]]:
        """
        Apply immediate stat growth for rising star status.
        Called after a race where rising star was active.
        Returns list of changes made.
        """
        if self.rising_star_races <= 0 or self.age >= 27:
            return []

        changes = []
        stats = self.stats
        stat_names = stats.get_stat_names()

        # Rising stars get a chance to grow 1 random stat immediately
        if random.random() < 0.4:  # 40% chance per race
            stat_name = random.choice(stat_names)
            old_value = getattr(stats, stat_name)
            if old_value < 99:
                new_value = min(99, old_value + 1)
                setattr(stats, stat_name, new_value)
                changes.append((stat_name, old_value, new_value))
                self._update_market_value()

        return changes

    def _update_market_value(self) -> None:
        """Update market value based on stats and age."""
        base_value = self.stats.overall * 0.8  # Base from overall rating

        # Age modifier
        if self.age < 23:
            age_mod = 1.3  # Young talent premium
        elif self.age <= 26:
            age_mod = 1.2  # Prime years
        elif self.age <= 30:
            age_mod = 1.0  # Standard
        elif self.age <= 34:
            age_mod = 0.7  # Late career discount
        else:
            age_mod = 0.4  # Veteran discount

        self.market_value = max(1, int(base_value * age_mod))
