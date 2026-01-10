from dataclasses import dataclass, field
from typing import List, Optional
from .car import Car
from .driver import Driver


@dataclass
class Team:
    name: str
    budget: float  # In millions
    car: Car
    drivers: List[Driver] = field(default_factory=list)
    is_player_team: bool = False
    player_number: int = 0  # 0 = AI, 1 = Player 1, 2 = Player 2
    season_points: int = 0
    race_wins: int = 0
    total_finishes: int = 0  # Number of race finishes (for avg position calc)
    total_positions: int = 0  # Sum of finishing positions (for avg position calc)

    def __str__(self) -> str:
        return self.name

    def get_driver_names(self) -> str:
        if not self.drivers:
            return "No drivers signed"
        return " & ".join(d.name for d in self.drivers)

    def can_afford(self, amount: float) -> bool:
        return self.budget >= amount

    def spend(self, amount: float) -> bool:
        if self.can_afford(amount):
            self.budget -= amount
            return True
        return False

    def add_income(self, amount: float) -> None:
        self.budget += amount

    def sign_driver(self, driver: Driver, fee: int) -> bool:
        """Sign a driver for the specified fee."""
        if len(self.drivers) >= 2:
            return False
        if not self.can_afford(fee):
            return False

        self.spend(fee)
        driver.sign_with_team(self.name)
        self.drivers.append(driver)
        return True

    def release_driver(self, driver: Driver) -> bool:
        """Release a driver from the team."""
        if driver in self.drivers:
            driver.release_from_team()
            self.drivers.remove(driver)
            return True
        return False

    def reset_season_stats(self) -> None:
        self.season_points = 0
        self.race_wins = 0
        self.total_finishes = 0
        self.total_positions = 0
        for driver in self.drivers:
            driver.reset_season_stats()

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

    def get_season_prize_money(self, position: int) -> int:
        """Calculate prize money based on constructor championship position."""
        prize_table = {
            1: 80, 2: 70, 3: 62, 4: 55, 5: 48,
            6: 42, 7: 38, 8: 35, 9: 32, 10: 30, 11: 28
        }
        return prize_table.get(position, 25)

    def get_info_display(self) -> str:
        return (
            f"Team: {self.name}\n"
            f"Budget: ${self.budget}M\n"
            f"Drivers: {self.get_driver_names()}\n"
            f"Season Points: {self.season_points}\n"
            f"Car Performance: {self.car.overall}"
        )
