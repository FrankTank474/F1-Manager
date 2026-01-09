"""Car Upgrade System"""

from typing import List, Tuple
from ..models import Car, Team


class UpgradeSystem:
    STAT_DISPLAY_NAMES = {
        'downforce': 'Downforce',
        'aero_efficiency': 'Aero Efficiency',
        'chassis': 'Chassis',
        'power_unit': 'Power Unit',
        'reliability': 'Reliability',
        'tire_cooling': 'Tire Cooling'
    }

    def __init__(self, player_team: Team):
        self.player_team = player_team

    def get_upgrade_options(self) -> List[Tuple[str, str, int, int, int]]:
        """
        Get available upgrade options.
        Returns: List of (stat_name, display_name, current_value, upgrade_cost, new_value)
        """
        car = self.player_team.car
        options = []

        for stat_name in Car.get_stat_names():
            current = getattr(car, stat_name)
            if current >= 100:
                continue

            cost = car.get_upgrade_cost(stat_name, 1)
            display_name = self.STAT_DISPLAY_NAMES[stat_name]
            options.append((stat_name, display_name, current, cost, current + 1))

        return options

    def can_afford_upgrade(self, stat_name: str, points: int = 1) -> bool:
        """Check if player can afford the upgrade."""
        cost = self.player_team.car.get_upgrade_cost(stat_name, points)
        return self.player_team.can_afford(cost)

    def purchase_upgrade(self, stat_name: str, points: int = 1) -> Tuple[bool, str]:
        """Purchase an upgrade for the car."""
        car = self.player_team.car
        current = getattr(car, stat_name)

        if current >= 100:
            return False, "Stat is already maxed out at 100."

        cost = car.get_upgrade_cost(stat_name, points)

        if not self.player_team.can_afford(cost):
            return False, f"Insufficient budget. Need ${cost}M, have ${self.player_team.budget}M."

        self.player_team.spend(cost)
        car.upgrade_stat(stat_name, points)

        display_name = self.STAT_DISPLAY_NAMES[stat_name]
        return True, f"{display_name} upgraded to {current + points} for ${cost}M!"

    def display_upgrade_menu(self) -> str:
        """Return formatted upgrade menu."""
        car = self.player_team.car
        budget = self.player_team.budget

        lines = [
            "\n" + "=" * 60,
            "  CAR UPGRADES",
            "=" * 60,
            f"  Budget: ${budget}M",
            "-" * 60,
            "  Current Car Stats:",
            car.get_stats_display(),
            "-" * 60,
            f"  {'#':<3} {'Component':<20} {'Current':>8} {'Cost':>10} {'New':>8}",
            "-" * 60
        ]

        options = self.get_upgrade_options()
        for i, (stat_name, display_name, current, cost, new_value) in enumerate(options, 1):
            affordable = "  " if budget >= cost else "X "
            lines.append(
                f"  {affordable}{i:<2} {display_name:<20} {current:>8} ${cost:>8}M {new_value:>8}"
            )

        if not options:
            lines.append("  All stats are maxed out!")

        lines.append("=" * 60)
        lines.append("  X = Cannot afford")
        lines.append("")
        lines.append("  Upgrade costs increase as stats get higher:")
        lines.append("  50-54: $2M | 55-59: $3M | 60-64: $5M | 65-69: $7M | 70-74: $10M")
        lines.append("  75-79: $14M | 80-84: $18M | 85-89: $24M | 90-94: $32M | 95-99: $45M")
        return "\n".join(lines)
