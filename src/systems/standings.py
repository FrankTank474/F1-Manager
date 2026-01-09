"""Championship Standings Management"""

from typing import List, Tuple, Optional
from ..models import Driver, Team
from ..ui.colors import get_team_color, Colors


# F1 Points System (2026)
POINTS_SYSTEM = {
    1: 25, 2: 18, 3: 15, 4: 12, 5: 10,
    6: 8, 7: 6, 8: 4, 9: 2, 10: 1
}

# Race Prize Money (in millions) - awarded per driver finishing position
RACE_PRIZE_MONEY = {
    1: 4.5,      # $4.5M for a win
    2: 3.5,
    3: 3.0,
    4: 2.5,
    5: 2.2,
    6: 2.0,
    7: 1.8,
    8: 1.6,
    9: 1.4,
    10: 1.3,
    11: 1.2,
    12: 1.1,
    13: 1.0,
    14: 0.95,
    15: 0.9,
    16: 0.85,
    17: 0.8,
    18: 0.75,
    19: 0.7,
    20: 0.65,
    21: 0.6,
    22: 0.55,
}


class StandingsManager:
    def __init__(self, teams: List[Team], drivers: List[Driver], player_team: Optional[Team] = None):
        self.teams = teams
        self.drivers = drivers
        self.player_team = player_team

    def get_driver_standings(self) -> List[Tuple[int, Driver, str]]:
        """Return sorted driver standings: (position, driver, team_name)"""
        # Get all drivers with their teams
        driver_data = []
        for team in self.teams:
            for driver in team.drivers:
                driver_data.append((driver, team.name))

        # Sort by:
        # 1. Points (descending)
        # 2. Race wins (descending)
        # 3. For 0-point drivers: average finishing position (ascending - lower is better)
        def driver_sort_key(x):
            driver = x[0]
            if driver.season_points > 0:
                # Drivers with points: sort by points, then wins
                # Use negative avg_pos so it doesn't affect sorting for point-scorers
                return (driver.season_points, driver.race_wins, 0)
            else:
                # Drivers with 0 points: sort by average position (lower is better)
                # Use negative average so lower average = higher ranking
                return (0, 0, -driver.get_average_position())

        driver_data.sort(key=driver_sort_key, reverse=True)

        return [(i + 1, d, t) for i, (d, t) in enumerate(driver_data)]

    def get_constructor_standings(self) -> List[Tuple[int, Team]]:
        """Return sorted constructor standings: (position, team)"""
        # Sort by:
        # 1. Points (descending)
        # 2. Race wins (descending)
        # 3. For 0-point teams: average finishing position (ascending - lower is better)
        def team_sort_key(team):
            if team.season_points > 0:
                return (team.season_points, team.race_wins, 0)
            else:
                # Use negative average so lower average = higher ranking
                return (0, 0, -team.get_average_position())

        sorted_teams = sorted(self.teams, key=team_sort_key, reverse=True)
        return [(i + 1, t) for i, t in enumerate(sorted_teams)]

    def update_race_results(self, race_results: List[Tuple[Driver, Team, int]]) -> None:
        """
        Update standings based on race results.
        race_results: List of (driver, team, position) - position 0 means DNF
        """
        for driver, team, position in race_results:
            if position > 0:
                points = POINTS_SYSTEM.get(position, 0)
                driver.season_points += points
                team.season_points += points

                # Record finish for average position calculation
                driver.record_finish(position)
                team.record_finish(position)

                if position == 1:
                    driver.race_wins += 1
                    team.race_wins += 1
                if position <= 3:
                    driver.podiums += 1
            else:
                driver.dnfs += 1

    def calculate_race_prize_money(self, race_results: List[Tuple[Driver, Team, int]]) -> Tuple[float, List[Tuple[str, int, float]]]:
        """
        Calculate prize money earned by player team in a race.
        Returns: (total_prize, [(driver_name, position, prize), ...])
        """
        if not self.player_team:
            return 0.0, []

        total_prize = 0.0
        driver_prizes = []

        for driver, team, position in race_results:
            if team == self.player_team and position > 0:
                prize = RACE_PRIZE_MONEY.get(position, 0.25)
                total_prize += prize
                driver_prizes.append((driver.name, position, prize))

        return total_prize, driver_prizes

    def display_driver_standings(self) -> str:
        """Return formatted driver standings string with team colors."""
        standings = self.get_driver_standings()
        lines = [
            "\n" + "=" * 65,
            "  DRIVER CHAMPIONSHIP STANDINGS",
            "=" * 65,
            f"  {'Pos':<4} {'Driver':<25} {'Team':<20} {'Points':>6}",
            "-" * 65
        ]

        for pos, driver, team_name in standings:
            color = get_team_color(team_name)
            is_player = self.player_team and team_name == self.player_team.name
            marker = " *" if is_player else "  "
            lines.append(
                f"{marker}{pos:<3} "
                f"{color}{driver.name:<25}{Colors.RESET} "
                f"{color}{team_name:<20}{Colors.RESET} "
                f"{driver.season_points:>6}"
            )

        lines.append("=" * 65)
        lines.append("  * = Your team")
        return "\n".join(lines)

    def display_constructor_standings(self) -> str:
        """Return formatted constructor standings string with team colors."""
        standings = self.get_constructor_standings()
        lines = [
            "\n" + "=" * 55,
            "  CONSTRUCTOR CHAMPIONSHIP STANDINGS",
            "=" * 55,
            f"  {'Pos':<4} {'Team':<30} {'Points':>8} {'Wins':>6}",
            "-" * 55
        ]

        for pos, team in standings:
            color = get_team_color(team.name)
            is_player = self.player_team and team == self.player_team
            marker = " *" if is_player else "  "
            lines.append(
                f"{marker}{pos:<3} "
                f"{color}{team.name:<30}{Colors.RESET} "
                f"{team.season_points:>8} {team.race_wins:>6}"
            )

        lines.append("=" * 55)
        lines.append("  * = Your team")
        return "\n".join(lines)

    def get_season_prize_distribution(self) -> List[Tuple[Team, int]]:
        """Calculate end-of-season prize money for all teams."""
        standings = self.get_constructor_standings()
        distribution = []

        for pos, team in standings:
            prize = team.get_season_prize_money(pos)
            distribution.append((team, prize))

        return distribution
