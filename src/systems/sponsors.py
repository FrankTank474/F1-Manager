"""Sponsor System for F1 Manager"""

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum


class SponsorObjectiveType(Enum):
    FINISH_POSITION = "finish_position"  # Finish in position X or better
    POINTS_FINISH = "points_finish"  # Finish in points (top 10)
    PODIUM = "podium"  # Finish on podium (top 3)
    WIN = "win"  # Win a race
    CONSTRUCTOR_POSITION = "constructor_position"  # End season in X position or better


@dataclass
class SponsorObjective:
    objective_type: SponsorObjectiveType
    target: int  # e.g., 15 for "finish 15th or better"
    description: str


@dataclass
class Sponsor:
    name: str
    tier: str  # "bronze", "silver", "gold", "platinum"
    base_payment: float  # Payment per race when objective met (in millions)
    bonus_payment: float  # End of season bonus if all objectives met
    objective: SponsorObjective

    def get_display(self) -> str:
        tier_display = self.tier.upper()
        return (
            f"  {self.name} ({tier_display})\n"
            f"  Objective: {self.objective.description}\n"
            f"  Per-Race Payment: ${self.base_payment:.2f}M (when objective met)\n"
            f"  Season Bonus: ${self.bonus_payment:.1f}M (if 80%+ objectives met)"
        )


# Sponsor templates for generating offers
SPONSOR_TEMPLATES = [
    # Bronze tier - easy objectives, low pay
    {
        "names": ["QuickFuel", "SpeedyParts", "RacerEnergy", "TrackSide Motors", "GridStart Oil"],
        "tier": "bronze",
        "base_payment": (0.3, 0.5),
        "bonus_payment": (3, 5),
        "objectives": [
            (SponsorObjectiveType.FINISH_POSITION, 20, "Finish the race (complete the race)"),
            (SponsorObjectiveType.FINISH_POSITION, 18, "Finish 18th or better"),
            (SponsorObjectiveType.FINISH_POSITION, 16, "Finish 16th or better"),
        ]
    },
    # Silver tier - moderate objectives, decent pay
    {
        "names": ["Apex Dynamics", "VelocityTech", "PitLane Pro", "Turbo Systems", "AeroFlow"],
        "tier": "silver",
        "base_payment": (0.6, 0.9),
        "bonus_payment": (6, 10),
        "objectives": [
            (SponsorObjectiveType.FINISH_POSITION, 15, "Finish 15th or better"),
            (SponsorObjectiveType.FINISH_POSITION, 12, "Finish 12th or better"),
            (SponsorObjectiveType.POINTS_FINISH, 10, "Finish in the points (Top 10)"),
        ]
    },
    # Gold tier - harder objectives, good pay
    {
        "names": ["PrimeSpeed", "EliteRacing Co.", "ChampionTech", "Podium Partners", "WinnerCircle"],
        "tier": "gold",
        "base_payment": (1.0, 1.5),
        "bonus_payment": (12, 18),
        "objectives": [
            (SponsorObjectiveType.FINISH_POSITION, 8, "Finish 8th or better"),
            (SponsorObjectiveType.FINISH_POSITION, 6, "Finish 6th or better"),
            (SponsorObjectiveType.PODIUM, 3, "Finish on the podium (Top 3)"),
        ]
    },
    # Platinum tier - elite objectives, high pay
    {
        "names": ["GlobalTech Industries", "Apex Champions", "Victory Corp", "F1 Elite Partners", "PolePosition Inc."],
        "tier": "platinum",
        "base_payment": (2.0, 3.0),
        "bonus_payment": (25, 40),
        "objectives": [
            (SponsorObjectiveType.PODIUM, 3, "Finish on the podium (Top 3)"),
            (SponsorObjectiveType.WIN, 1, "Win the race"),
            (SponsorObjectiveType.FINISH_POSITION, 5, "Finish 5th or better"),
        ]
    },
]


class SponsorManager:
    def __init__(self):
        self.current_sponsor: Optional[Sponsor] = None
        self.races_completed: int = 0
        self.objectives_met: int = 0
        self.total_earnings: float = 0.0

    def generate_sponsor_offers(self, team_reputation: int = 50) -> List[Sponsor]:
        """
        Generate 5 sponsor offers for the player to choose from.
        team_reputation affects which tiers of sponsors are available.
        """
        offers = []

        # Determine available tiers based on reputation
        # Low rep teams get mostly bronze/silver, high rep get gold/platinum
        if team_reputation < 30:
            tier_weights = [0.5, 0.4, 0.1, 0.0]  # Mostly bronze
        elif team_reputation < 50:
            tier_weights = [0.3, 0.4, 0.25, 0.05]  # Bronze/Silver heavy
        elif team_reputation < 70:
            tier_weights = [0.15, 0.35, 0.35, 0.15]  # Balanced
        else:
            tier_weights = [0.05, 0.2, 0.4, 0.35]  # Gold/Platinum heavy

        used_names = set()

        for _ in range(5):
            # Select tier based on weights
            tier_idx = random.choices(range(4), weights=tier_weights, k=1)[0]
            template = SPONSOR_TEMPLATES[tier_idx]

            # Pick a name not already used
            available_names = [n for n in template["names"] if n not in used_names]
            if not available_names:
                available_names = template["names"]
            name = random.choice(available_names)
            used_names.add(name)

            # Random payment within range
            base_pay = random.uniform(*template["base_payment"])
            bonus_pay = random.uniform(*template["bonus_payment"])

            # Pick random objective from tier
            obj_type, target, desc = random.choice(template["objectives"])
            objective = SponsorObjective(obj_type, target, desc)

            sponsor = Sponsor(
                name=name,
                tier=template["tier"],
                base_payment=round(base_pay, 2),
                bonus_payment=round(bonus_pay, 1),
                objective=objective
            )
            offers.append(sponsor)

        return offers

    def select_sponsor(self, sponsor: Sponsor) -> None:
        """Select a sponsor for the season."""
        self.current_sponsor = sponsor
        self.races_completed = 0
        self.objectives_met = 0
        self.total_earnings = 0.0

    def check_race_objective(self, best_finish: int) -> Tuple[bool, float]:
        """
        Check if race objective was met and return payment.
        best_finish: Best finishing position of either driver (0 = DNF for both)
        Returns: (objective_met, payment)
        """
        if not self.current_sponsor:
            return False, 0.0

        self.races_completed += 1
        objective = self.current_sponsor.objective
        met = False

        if best_finish <= 0:
            # Both drivers DNF'd
            met = False
        elif objective.objective_type == SponsorObjectiveType.FINISH_POSITION:
            met = best_finish <= objective.target
        elif objective.objective_type == SponsorObjectiveType.POINTS_FINISH:
            met = best_finish <= 10
        elif objective.objective_type == SponsorObjectiveType.PODIUM:
            met = best_finish <= 3
        elif objective.objective_type == SponsorObjectiveType.WIN:
            met = best_finish == 1

        payment = 0.0
        if met:
            self.objectives_met += 1
            payment = self.current_sponsor.base_payment
            self.total_earnings += payment

        return met, payment

    def get_season_bonus(self) -> float:
        """Calculate end of season bonus if 80%+ objectives met."""
        if not self.current_sponsor or self.races_completed == 0:
            return 0.0

        success_rate = self.objectives_met / self.races_completed
        if success_rate >= 0.8:
            return self.current_sponsor.bonus_payment
        return 0.0

    def get_status_display(self) -> str:
        """Return current sponsor status."""
        if not self.current_sponsor:
            return "  No sponsor selected for this season."

        success_rate = 0
        if self.races_completed > 0:
            success_rate = (self.objectives_met / self.races_completed) * 100

        bonus_status = "ON TRACK" if success_rate >= 80 else "AT RISK"

        return (
            f"\n{'=' * 60}\n"
            f"  CURRENT SPONSOR: {self.current_sponsor.name}\n"
            f"{'=' * 60}\n"
            f"  Tier: {self.current_sponsor.tier.upper()}\n"
            f"  Objective: {self.current_sponsor.objective.description}\n"
            f"  Per-Race Payment: ${self.current_sponsor.base_payment:.2f}M\n"
            f"  Season Bonus: ${self.current_sponsor.bonus_payment:.1f}M\n"
            f"{'-' * 60}\n"
            f"  SEASON PROGRESS:\n"
            f"  Races Completed: {self.races_completed}\n"
            f"  Objectives Met: {self.objectives_met}/{self.races_completed} ({success_rate:.0f}%)\n"
            f"  Total Earnings: ${self.total_earnings:.2f}M\n"
            f"  Bonus Status: {bonus_status} (need 80% for bonus)\n"
            f"{'=' * 60}"
        )

    def display_sponsor_selection(self, offers: List[Sponsor]) -> str:
        """Return formatted sponsor selection menu."""
        lines = [
            "\n" + "=" * 70,
            "  SPONSOR OFFERS FOR THE SEASON",
            "=" * 70,
            "  Choose one sponsor to partner with for the entire season.",
            "  Meet their objective each race to earn payments!",
            "-" * 70,
        ]

        for i, sponsor in enumerate(offers, 1):
            lines.append(f"\n  [{i}] {sponsor.name} ({sponsor.tier.upper()})")
            lines.append(f"      Objective: {sponsor.objective.description}")
            lines.append(f"      Per-Race: ${sponsor.base_payment:.2f}M  |  Season Bonus: ${sponsor.bonus_payment:.1f}M")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def reset_for_new_season(self) -> None:
        """Reset sponsor data for new season."""
        self.current_sponsor = None
        self.races_completed = 0
        self.objectives_met = 0
        self.total_earnings = 0.0
