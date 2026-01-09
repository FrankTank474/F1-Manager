"""Driver Transfer Market System"""

import random
from typing import List, Optional, Tuple
from ..models import Driver, Team


class DriverMarket:
    def __init__(self, all_drivers: List[Driver], teams: List[Team]):
        self.all_drivers = all_drivers
        self.teams = teams

    def get_available_drivers(self) -> List[Driver]:
        """Get list of drivers available for signing (free agents or can be bought)."""
        return sorted(self.all_drivers, key=lambda d: d.market_value, reverse=True)

    def get_free_agents(self) -> List[Driver]:
        """Get list of free agent drivers."""
        return [d for d in self.all_drivers if d.is_free_agent()]

    def get_team_by_name(self, name: str) -> Optional[Team]:
        """Find team by name."""
        for team in self.teams:
            if team.name == name:
                return team
        return None

    def can_sign_driver(self, team: Team, driver: Driver) -> tuple[bool, str]:
        """Check if a team can sign a driver."""
        if len(team.drivers) >= 2:
            return False, "Team already has 2 drivers. Release a driver first."

        if driver.team_name == team.name:
            return False, "Driver is already on your team."

        # Free agents are free to sign - only pay salary at end of season
        # Contracted drivers require transfer fee
        if not driver.is_free_agent():
            if not team.can_afford(driver.market_value):
                return False, f"Insufficient budget. Need ${driver.market_value}M transfer fee, have ${team.budget}M."

        return True, "OK"

    def sign_driver(self, team: Team, driver: Driver) -> tuple[bool, str]:
        """Sign a driver to a team."""
        can_sign, message = self.can_sign_driver(team, driver)
        if not can_sign:
            return False, message

        is_free_agent = driver.is_free_agent()

        # If driver is on another team, release them and pay transfer fee
        if driver.team_name:
            current_team = self.get_team_by_name(driver.team_name)
            if current_team:
                current_team.release_driver(driver)

        # Determine signing cost
        if is_free_agent:
            # Free agents are free - salary paid at end of season
            signing_cost = 0
        else:
            # Transfer fee for contracted drivers
            signing_cost = driver.market_value

        # Sign to new team
        if signing_cost > 0:
            if not team.can_afford(signing_cost):
                return False, f"Insufficient budget for transfer fee."
            team.spend(signing_cost)

        driver.sign_with_team(team.name)
        team.drivers.append(driver)

        if is_free_agent:
            return True, f"{driver.name} signed as free agent! (Salary: ${driver.salary}M/season)"
        else:
            return True, f"{driver.name} signed for ${signing_cost}M transfer fee! (Salary: ${driver.salary}M/season)"

    def release_driver(self, team: Team, driver: Driver) -> tuple[bool, str]:
        """Release a driver from a team."""
        if driver not in team.drivers:
            return False, "Driver is not on this team."

        team.release_driver(driver)
        return True, f"{driver.name} has been released."

    def display_market(self, player_budget: int) -> str:
        """Return formatted market display."""
        drivers = self.get_available_drivers()

        lines = [
            "\n" + "=" * 105,
            "  DRIVER MARKET",
            "=" * 105,
            f"  Your Budget: ${player_budget}M",
            f"  Note: Free agents cost $0 to sign (salary paid at season end)",
            "-" * 105,
            f"  {'#':<3} {'Driver':<20} {'Age':<4} {'Team':<16} {'OVR':<5} {'POT':<5} {'Fee':>8} {'Salary':>7}",
            "-" * 105
        ]

        for i, driver in enumerate(drivers, 1):
            if driver.is_free_agent():
                team_str = "FREE AGENT"
                cost_str = "FREE"
                affordable = "  "  # Free agents are always affordable
            else:
                team_str = driver.team_name if len(driver.team_name) <= 16 else driver.team_name[:14] + ".."
                cost_str = f"${driver.market_value}M"
                affordable = "  " if player_budget >= driver.market_value else "X "

            potential = driver.get_potential()
            rising = "*" if driver.rising_star_races > 0 else ""

            lines.append(
                f"  {affordable}{i:<2} {driver.name:<20} {driver.age:<4} "
                f"{team_str:<16} {driver.stats.overall:<5} {potential:<4}{rising} {cost_str:>8} ${driver.salary:>5}M"
            )

        lines.append("=" * 105)
        lines.append("  X = Cannot afford  |  * = Rising Star  |  POT = Potential rating")
        return "\n".join(lines)

    def display_driver_details(self, driver: Driver) -> str:
        """Return detailed driver information."""
        if driver.is_free_agent():
            team_str = "Free Agent"
            cost_str = "FREE (No transfer fee)"
        else:
            team_str = driver.team_name
            cost_str = f"${driver.market_value}M"

        lines = [
            "\n" + "=" * 50,
            f"  {driver.name}",
            "=" * 50,
            f"  Age: {driver.age}  |  Nationality: {driver.nationality}",
            f"  Current Team: {team_str}",
            f"  Transfer Fee: {cost_str}",
            f"  Salary: ${driver.salary}M/season",
            "-" * 50,
            "  STATS:",
            driver.get_stats_display(),
            "=" * 50
        ]
        return "\n".join(lines)

    # ========== AI TEAM MANAGEMENT ==========

    def get_team_drivers(self, team: Team) -> List[Driver]:
        """Get all drivers for a team."""
        return [d for d in self.all_drivers if d.team_name == team.name]

    def ensure_all_teams_have_drivers(self, player_team: Team) -> List[str]:
        """
        Ensure all AI teams have exactly 2 drivers before season starts.
        Teams sign drivers appropriate to their tier.
        Returns list of transfer messages.
        """
        messages = []
        free_agents = self.get_free_agents()

        # Sort teams by car rating (top teams pick first)
        sorted_teams = sorted(
            [t for t in self.teams if t != player_team],
            key=lambda t: t.car.overall,
            reverse=True
        )

        for team in sorted_teams:
            team_drivers = self.get_team_drivers(team)
            car_rating = team.car.overall

            # Determine target driver rating based on team tier
            if car_rating >= 85:
                target_min = 80
                target_ideal = 88
            elif car_rating >= 75:
                target_min = 72
                target_ideal = 80
            elif car_rating >= 65:
                target_min = 68
                target_ideal = 75
            else:
                target_min = 62
                target_ideal = 70

            # Sign drivers until team has 2
            while len(team_drivers) < 2 and free_agents:
                # Free agents are FREE - no transfer fee needed
                # Filter by rating preference for team tier
                ideal_agents = [d for d in free_agents if d.stats.overall >= target_ideal]
                good_agents = [d for d in free_agents if target_min <= d.stats.overall < target_ideal]
                acceptable_agents = [d for d in free_agents if d.stats.overall >= target_min - 5]

                # Pick from best available pool
                if ideal_agents:
                    candidates = ideal_agents
                elif good_agents:
                    candidates = good_agents
                elif acceptable_agents:
                    candidates = acceptable_agents
                else:
                    candidates = free_agents  # Take anyone if desperate

                if candidates:
                    # Weight by overall rating (better drivers more likely to be picked)
                    weights = [max(1, d.stats.overall - 50) for d in candidates]
                    driver = random.choices(candidates, weights=weights, k=1)[0]

                    # Free agents are FREE to sign
                    driver.sign_with_team(team.name)
                    team.drivers.append(driver)

                    messages.append(f"{team.name} signed {driver.name} (free agent)")
                    free_agents.remove(driver)
                    team_drivers.append(driver)
                else:
                    break

        return messages

    def process_ai_transfers(self, player_team: Team) -> List[str]:
        """
        Process end-of-season AI transfers.
        AI teams release drivers based on realistic criteria:
        - Driver rating relative to team expectations
        - Age (only release old drivers if they're also underperforming)
        - Budget constraints
        Returns list of transfer messages.
        """
        messages = []

        for team in self.teams:
            if team == player_team:
                continue

            team_drivers = self.get_team_drivers(team)
            car_rating = team.car.overall

            # Determine team tier and expected driver rating
            if car_rating >= 85:
                tier = "top"
                min_expected_rating = 82  # Top teams expect 82+ drivers
            elif car_rating >= 75:
                tier = "upper_mid"
                min_expected_rating = 75  # Upper mid expect 75+ drivers
            elif car_rating >= 65:
                tier = "midfield"
                min_expected_rating = 70  # Midfield expect 70+ drivers
            else:
                tier = "backmarker"
                min_expected_rating = 65  # Backmarkers accept anyone decent

            # Evaluate each driver for potential release
            for driver in team_drivers[:]:  # Copy list to allow modification
                should_release = False
                reason = ""
                driver_rating = driver.stats.overall

                # Calculate how far below expectations the driver is
                rating_gap = min_expected_rating - driver_rating

                # TOP TIER TEAMS - Very selective, only release if significantly below standard
                if tier == "top":
                    # Only release if driver is 8+ points below expectation
                    if rating_gap >= 8 and random.random() < 0.6:
                        should_release = True
                        reason = "not meeting team expectations"
                    # Old drivers (38+) who are declining
                    elif driver.age >= 38 and driver_rating < 85 and random.random() < 0.4:
                        should_release = True
                        reason = "retirement"
                    # Very old drivers (40+) regardless
                    elif driver.age >= 40 and random.random() < 0.7:
                        should_release = True
                        reason = "retirement"

                # UPPER MIDFIELD - Release if notably below standard
                elif tier == "upper_mid":
                    if rating_gap >= 6 and random.random() < 0.5:
                        should_release = True
                        reason = "underperformance"
                    elif driver.age >= 37 and driver_rating < 78 and random.random() < 0.4:
                        should_release = True
                        reason = "retirement"

                # MIDFIELD - More flexible but still have standards
                elif tier == "midfield":
                    if rating_gap >= 5 and random.random() < 0.4:
                        should_release = True
                        reason = "looking for improvement"
                    elif driver.age >= 36 and driver_rating < 72 and random.random() < 0.35:
                        should_release = True
                        reason = "retirement"

                # BACKMARKERS - Only release truly poor performers or very old
                else:
                    if driver_rating < 62 and random.random() < 0.3:
                        should_release = True
                        reason = "seeking fresh talent"
                    elif driver.age >= 36 and driver_rating < 68 and random.random() < 0.3:
                        should_release = True
                        reason = "retirement"

                # Never release a driver if they're the only one (need at least 1)
                # And never release elite drivers (88+) from ANY team unless very old
                if driver_rating >= 88 and driver.age < 38:
                    should_release = False

                if should_release and len(team_drivers) > 1:
                    # Release the driver
                    team.release_driver(driver)
                    driver.release_from_team()
                    team_drivers.remove(driver)
                    messages.append(f"{team.name} released {driver.name} ({reason})")

        # Now have teams sign new drivers to fill gaps
        fill_messages = self.ensure_all_teams_have_drivers(player_team)
        messages.extend(fill_messages)

        return messages

    def ai_poach_driver(self, team: Team, target_driver: Driver, player_team: Team) -> Optional[str]:
        """
        AI team attempts to poach a driver from another team.
        Returns message if successful, None otherwise.
        """
        if team == player_team:
            return None

        if target_driver.team_name == team.name:
            return None

        # Check if team can afford and has space
        if len(team.drivers) >= 2:
            return None

        if not team.can_afford(target_driver.market_value):
            return None

        # Don't poach from player team
        if target_driver.team_name == player_team.name:
            return None

        # Get current team
        current_team = self.get_team_by_name(target_driver.team_name)
        if current_team and len(self.get_team_drivers(current_team)) <= 1:
            return None  # Don't leave a team with 0 drivers

        # Poach the driver
        if current_team:
            current_team.release_driver(target_driver)

        team.spend(target_driver.market_value)
        target_driver.sign_with_team(team.name)
        team.drivers.append(target_driver)

        return f"{team.name} signed {target_driver.name} from {current_team.name if current_team else 'Free Agency'} for ${target_driver.market_value}M"
