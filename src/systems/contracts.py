"""Driver Contract & Negotiation System"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Driver, Team


class ContractStatus(Enum):
    ACTIVE = "Active"
    EXPIRING = "Expiring"  # Last season of contract
    EXPIRED = "Expired"
    NEGOTIATING = "In Negotiation"


class DemandType(Enum):
    SALARY_INCREASE = "Salary Increase"
    NUMBER_ONE_STATUS = "#1 Driver Status"
    LONGER_CONTRACT = "Longer Contract"
    RELEASE_CLAUSE = "Release Clause"
    PERFORMANCE_BONUS = "Performance Bonus"


@dataclass
class ContractDemand:
    """A demand from a driver during negotiations."""
    demand_type: DemandType
    description: str
    importance: int  # 1-10, how much they care
    value: Optional[int] = None  # For salary demands

    def get_rejection_morale_impact(self) -> int:
        """Get morale impact if this demand is rejected."""
        return -self.importance * 2


@dataclass
class DriverContract:
    """Contract details for a driver."""
    driver_name: str
    team_name: str
    salary: int  # Per season in millions
    years_remaining: int = 2  # Seasons left on contract
    is_number_one: bool = False
    has_release_clause: bool = False
    release_clause_value: int = 0
    performance_bonus: int = 0  # Bonus per win

    # Negotiation state
    is_negotiating: bool = False
    demands: List[ContractDemand] = field(default_factory=list)
    negotiation_deadline: int = 0  # Race number when they'll leave if not resolved
    has_rival_offer: bool = False
    rival_team_name: Optional[str] = None
    rival_offer_salary: int = 0

    @property
    def status(self) -> ContractStatus:
        if self.is_negotiating:
            return ContractStatus.NEGOTIATING
        elif self.years_remaining <= 0:
            return ContractStatus.EXPIRED
        elif self.years_remaining == 1:
            return ContractStatus.EXPIRING
        else:
            return ContractStatus.ACTIVE

    def end_season(self) -> None:
        """Process end of season for contract."""
        if self.years_remaining > 0:
            self.years_remaining -= 1


@dataclass
class NegotiationResult:
    """Result of a contract negotiation."""
    success: bool
    new_contract: Optional[DriverContract] = None
    driver_left: bool = False
    destination_team: Optional[str] = None
    messages: List[str] = field(default_factory=list)


class ContractManager:
    """Manages all driver contracts and negotiations."""

    def __init__(self):
        self.contracts: Dict[str, DriverContract] = {}
        self.pending_negotiations: List[str] = []  # Driver names needing negotiation
        self.current_race: int = 0
        self.current_season: int = 1

    def create_contract(
        self,
        driver_name: str,
        team_name: str,
        salary: int,
        years: int = 2
    ) -> DriverContract:
        """Create a new contract for a driver."""
        contract = DriverContract(
            driver_name=driver_name,
            team_name=team_name,
            salary=salary,
            years_remaining=years
        )
        self.contracts[driver_name] = contract
        return contract

    def get_contract(self, driver_name: str) -> Optional[DriverContract]:
        """Get a driver's contract."""
        return self.contracts.get(driver_name)

    def check_expiring_contracts(self, player_team_name: str) -> List[str]:
        """
        Check for expiring contracts that need negotiation.
        Returns list of messages about contracts.
        """
        messages = []

        for driver_name, contract in self.contracts.items():
            if contract.team_name != player_team_name:
                continue

            if contract.years_remaining == 1 and not contract.is_negotiating:
                # Contract expires at end of season - trigger negotiation
                contract.is_negotiating = True
                self._generate_demands(contract)
                self.pending_negotiations.append(driver_name)
                messages.append(f"CONTRACT ALERT: {driver_name}'s contract expires at end of season!")

        return messages

    def _generate_demands(self, contract: DriverContract) -> None:
        """Generate negotiation demands based on driver performance and situation."""
        contract.demands = []

        # Almost always want salary increase
        current_salary = contract.salary
        desired_increase = random.randint(2, 5)  # $2-5M increase
        contract.demands.append(ContractDemand(
            demand_type=DemandType.SALARY_INCREASE,
            description=f"Wants salary increased from ${current_salary}M to ${current_salary + desired_increase}M",
            importance=random.randint(6, 9),
            value=current_salary + desired_increase
        ))

        # If not #1, might demand it
        if not contract.is_number_one and random.random() < 0.5:
            contract.demands.append(ContractDemand(
                demand_type=DemandType.NUMBER_ONE_STATUS,
                description="Wants to be designated as #1 driver",
                importance=random.randint(5, 8)
            ))

        # Might want longer contract for security
        if random.random() < 0.4:
            contract.demands.append(ContractDemand(
                demand_type=DemandType.LONGER_CONTRACT,
                description="Wants a 3-year contract for job security",
                importance=random.randint(4, 7)
            ))

        # Top drivers might want release clause
        if random.random() < 0.3:
            release_value = current_salary * 3
            contract.demands.append(ContractDemand(
                demand_type=DemandType.RELEASE_CLAUSE,
                description=f"Wants a release clause of ${release_value}M",
                importance=random.randint(3, 6),
                value=release_value
            ))

        # Set negotiation deadline
        contract.negotiation_deadline = self.current_race + random.randint(3, 6)

        # Chance of having a rival offer
        if random.random() < 0.4:
            contract.has_rival_offer = True
            rival_teams = ["Ferrari", "McLaren", "Mercedes", "Red Bull", "Aston Martin", "Alpine", "Williams"]
            contract.rival_team_name = random.choice(rival_teams)
            contract.rival_offer_salary = current_salary + random.randint(3, 8)

    def get_negotiation_status(self, driver_name: str) -> Optional[str]:
        """Get formatted negotiation status."""
        contract = self.get_contract(driver_name)
        if not contract or not contract.is_negotiating:
            return None

        lines = [
            f"\n" + "=" * 60,
            f"  CONTRACT NEGOTIATION: {driver_name}",
            "=" * 60,
            f"  Current Salary: ${contract.salary}M/season",
            f"  Years Remaining: {contract.years_remaining}",
            f"  #1 Status: {'Yes' if contract.is_number_one else 'No'}",
            "-" * 60,
            "  DRIVER DEMANDS:",
        ]

        for i, demand in enumerate(contract.demands, 1):
            importance_stars = "*" * demand.importance
            lines.append(f"  [{i}] {demand.description}")
            lines.append(f"      Importance: {importance_stars} ({demand.importance}/10)")

        if contract.has_rival_offer:
            lines.append("")
            lines.append(f"  WARNING: {driver_name} has an offer from {contract.rival_team_name}!")
            lines.append(f"           Rival offer: ${contract.rival_offer_salary}M/season")

        races_left = contract.negotiation_deadline - self.current_race
        lines.append("")
        lines.append(f"  Deadline: {races_left} races to reach agreement")
        lines.append("=" * 60)

        return "\n".join(lines)

    def make_offer(
        self,
        driver_name: str,
        new_salary: int,
        years: int,
        grant_number_one: bool,
        include_release_clause: bool,
        release_clause_value: int = 0
    ) -> NegotiationResult:
        """
        Make a contract offer to a driver.
        Returns negotiation result.
        """
        contract = self.get_contract(driver_name)
        if not contract or not contract.is_negotiating:
            return NegotiationResult(
                success=False,
                messages=["No active negotiation with this driver."]
            )

        messages = []
        satisfaction = 0
        total_importance = sum(d.importance for d in contract.demands)

        # Evaluate each demand
        for demand in contract.demands:
            if demand.demand_type == DemandType.SALARY_INCREASE:
                if new_salary >= demand.value:
                    satisfaction += demand.importance
                    messages.append(f"  Satisfied with salary of ${new_salary}M")
                elif new_salary >= demand.value - 2:
                    satisfaction += demand.importance * 0.5
                    messages.append(f"  Acceptable salary of ${new_salary}M")
                else:
                    messages.append(f"  Disappointed with salary offer of ${new_salary}M")

            elif demand.demand_type == DemandType.NUMBER_ONE_STATUS:
                if grant_number_one:
                    satisfaction += demand.importance
                    messages.append("  Happy with #1 driver status")
                else:
                    messages.append("  Unhappy about not getting #1 status")

            elif demand.demand_type == DemandType.LONGER_CONTRACT:
                if years >= 3:
                    satisfaction += demand.importance
                    messages.append("  Pleased with contract length")
                elif years >= 2:
                    satisfaction += demand.importance * 0.5
                    messages.append("  Would prefer longer contract")

            elif demand.demand_type == DemandType.RELEASE_CLAUSE:
                if include_release_clause:
                    satisfaction += demand.importance
                    messages.append("  Happy with release clause")
                else:
                    messages.append("  Wanted a release clause")

        # Calculate acceptance probability
        satisfaction_ratio = satisfaction / total_importance if total_importance > 0 else 0.5

        # Rival offer affects decision
        if contract.has_rival_offer:
            if new_salary >= contract.rival_offer_salary:
                satisfaction_ratio += 0.2
                messages.append(f"  Your offer beats {contract.rival_team_name}'s")
            else:
                satisfaction_ratio -= 0.2
                messages.append(f"  {contract.rival_team_name}'s offer is more attractive")

        # Random factor
        acceptance_chance = satisfaction_ratio + random.uniform(-0.15, 0.15)

        if acceptance_chance >= 0.6:
            # Accept offer
            new_contract = DriverContract(
                driver_name=driver_name,
                team_name=contract.team_name,
                salary=new_salary,
                years_remaining=years,
                is_number_one=grant_number_one,
                has_release_clause=include_release_clause,
                release_clause_value=release_clause_value if include_release_clause else 0
            )
            self.contracts[driver_name] = new_contract
            if driver_name in self.pending_negotiations:
                self.pending_negotiations.remove(driver_name)

            messages.insert(0, f"SUCCESS! {driver_name} has signed a new {years}-year contract!")
            return NegotiationResult(
                success=True,
                new_contract=new_contract,
                messages=messages
            )
        else:
            # Reject offer
            messages.insert(0, f"{driver_name} has REJECTED your offer!")
            messages.append("Consider improving your offer before the deadline.")
            return NegotiationResult(
                success=False,
                messages=messages
            )

    def check_negotiation_deadlines(self, player_team_name: str) -> List[str]:
        """Check if any negotiations have passed deadline."""
        messages = []

        for driver_name in self.pending_negotiations[:]:
            contract = self.get_contract(driver_name)
            if not contract:
                continue

            if self.current_race >= contract.negotiation_deadline:
                # Deadline passed - driver leaves
                if contract.has_rival_offer:
                    dest = contract.rival_team_name
                else:
                    dest = "another team"

                messages.append(f"BREAKING: {driver_name} has left {player_team_name} to join {dest}!")
                messages.append(f"  Failed negotiations have cost you a driver.")

                # Mark contract as expired
                contract.years_remaining = 0
                contract.is_negotiating = False
                self.pending_negotiations.remove(driver_name)

        return messages

    def process_season_end(self) -> Dict[str, List[str]]:
        """
        Process end of season contract changes.
        Returns dict of team_name -> list of messages.
        """
        messages = {}

        for driver_name, contract in self.contracts.items():
            contract.end_season()

            if contract.team_name not in messages:
                messages[contract.team_name] = []

            if contract.years_remaining == 0:
                messages[contract.team_name].append(
                    f"{driver_name}'s contract has expired"
                )

        self.current_season += 1
        return messages

    def advance_race(self) -> None:
        """Called after each race."""
        self.current_race += 1

    def get_contract_summary(self, driver_names: List[str]) -> str:
        """Get summary of contracts for team's drivers."""
        lines = [
            "\n" + "=" * 60,
            "  DRIVER CONTRACTS",
            "=" * 60,
        ]

        for name in driver_names:
            contract = self.get_contract(name)
            if contract:
                status_str = contract.status.value
                num_one = " [#1]" if contract.is_number_one else ""

                lines.append(f"  {name}{num_one}")
                lines.append(f"    Salary: ${contract.salary}M/season")
                lines.append(f"    Years Remaining: {contract.years_remaining}")
                lines.append(f"    Status: {status_str}")

                if contract.is_negotiating:
                    races_left = contract.negotiation_deadline - self.current_race
                    lines.append(f"    ! NEEDS ATTENTION - {races_left} races to negotiate")
                lines.append("")
            else:
                lines.append(f"  {name}")
                lines.append("    No contract on file")
                lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def display_negotiation_offer_screen(self, driver_name: str, team_budget: float) -> str:
        """Display the offer screen for negotiations."""
        contract = self.get_contract(driver_name)
        if not contract:
            return "No contract found."

        lines = [
            f"\n" + "=" * 60,
            f"  MAKE OFFER TO {driver_name.upper()}",
            "=" * 60,
            f"  Your Budget: ${team_budget:.1f}M",
            f"  Current Salary: ${contract.salary}M",
            "-" * 60,
            "  What they want:",
        ]

        for demand in contract.demands:
            lines.append(f"    - {demand.description}")

        if contract.has_rival_offer:
            lines.append("")
            lines.append(f"  Rival Offer: ${contract.rival_offer_salary}M from {contract.rival_team_name}")

        lines.append("=" * 60)
        return "\n".join(lines)
