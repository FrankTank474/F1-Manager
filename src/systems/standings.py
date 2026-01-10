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
    def __init__(self, teams: List[Team], drivers: List[Driver], player_teams = None):
        self.teams = teams
        self.drivers = drivers
        # Support both single team (backward compat) and list of teams
        if player_teams is None:
            self.player_teams = []
        elif isinstance(player_teams, list):
            self.player_teams = player_teams
        else:
            self.player_teams = [player_teams]

    @property
    def player_team(self) -> Optional[Team]:
        """Backward compatibility - returns first player team."""
        return self.player_teams[0] if self.player_teams else None

    def is_player_team(self, team: Team) -> bool:
        """Check if team belongs to any player."""
        return team in self.player_teams

    def get_player_marker(self, team: Team) -> str:
        """Get player marker (P1, P2) for a team."""
        try:
            idx = self.player_teams.index(team)
            return f"P{idx + 1}"
        except ValueError:
            return ""

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

    def calculate_race_prize_money(self, race_results: List[Tuple[Driver, Team, int]], for_team: Team = None) -> Tuple[float, List[Tuple[str, int, float]]]:
        """
        Calculate prize money earned by a player team in a race.
        Args:
            race_results: List of (driver, team, position)
            for_team: Specific team to calculate for (default: first player team)
        Returns: (total_prize, [(driver_name, position, prize), ...])
        """
        target_team = for_team or self.player_team
        if not target_team:
            return 0.0, []

        total_prize = 0.0
        driver_prizes = []

        for driver, team, position in race_results:
            if team == target_team and position > 0:
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
            # Check which player (if any) owns this team
            marker = "  "
            for i, pt in enumerate(self.player_teams):
                if team_name == pt.name:
                    marker = f"P{i+1}"
                    break
            lines.append(
                f"{marker}{pos:<3} "
                f"{color}{driver.name:<25}{Colors.RESET} "
                f"{color}{team_name:<20}{Colors.RESET} "
                f"{driver.season_points:>6}"
            )

        lines.append("=" * 65)
        if len(self.player_teams) > 1:
            lines.append("  P1/P2 = Player teams")
        elif self.player_teams:
            lines.append("  P1 = Your team")
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
            # Check which player (if any) owns this team
            marker = "  "
            for i, pt in enumerate(self.player_teams):
                if team == pt:
                    marker = f"P{i+1}"
                    break
            lines.append(
                f"{marker}{pos:<3} "
                f"{color}{team.name:<30}{Colors.RESET} "
                f"{team.season_points:>8} {team.race_wins:>6}"
            )

        lines.append("=" * 55)
        if len(self.player_teams) > 1:
            lines.append("  P1/P2 = Player teams")
        elif self.player_teams:
            lines.append("  P1 = Your team")
        return "\n".join(lines)

    def get_season_prize_distribution(self) -> List[Tuple[Team, int]]:
        """Calculate end-of-season prize money for all teams."""
        standings = self.get_constructor_standings()
        distribution = []

        for pos, team in standings:
            prize = team.get_season_prize_money(pos)
            distribution.append((team, prize))

        return distribution
