"""Car Development Tree System - Branching upgrade paths with strategic trade-offs"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Car, Team


class DevelopmentBranch(Enum):
    # Aero branches
    HIGH_DOWNFORCE = "High Downforce"
    LOW_DRAG = "Low Drag"
    BALANCED_AERO = "Balanced Aero"

    # Power Unit branches
    RAW_POWER = "Raw Power"
    EFFICIENCY = "Efficiency"
    RELIABILITY_FOCUS = "Reliability Focus"

    # Chassis branches
    MECHANICAL_GRIP = "Mechanical Grip"
    AERO_BALANCE = "Aero Balance"

    # Tire branches
    AGGRESSIVE_COOLING = "Aggressive Cooling"
    CONSERVATIVE_COOLING = "Conservative Cooling"


class DevelopmentCategory(Enum):
    AERODYNAMICS = "Aerodynamics"
    POWER_UNIT = "Power Unit"
    CHASSIS = "Chassis"
    TIRES = "Tire Management"


@dataclass
class DevelopmentNode:
    """A single node in the development tree."""
    name: str
    description: str
    category: DevelopmentCategory
    branch: Optional[DevelopmentBranch]
    cost: int  # Base cost in millions
    development_time: int  # Races to complete
    stat_changes: Dict[str, int]  # stat_name -> change amount
    trade_offs: Dict[str, int] = field(default_factory=dict)  # Negative effects
    prerequisites: List[str] = field(default_factory=list)  # Required node names
    exclusive_with: List[str] = field(default_factory=list)  # Can't have both
    unlocks: List[str] = field(default_factory=list)  # Nodes this enables
    is_completed: bool = False
    is_in_progress: bool = False
    progress: int = 0  # Races spent developing


@dataclass
class ActiveDevelopment:
    """A development currently in progress."""
    node_name: str
    races_remaining: int
    total_races: int


class DevelopmentTree:
    """Manages the car development tree."""

    def __init__(self):
        self.nodes: Dict[str, DevelopmentNode] = {}
        self.active_developments: List[ActiveDevelopment] = []
        self.completed_nodes: List[str] = []
        self.chosen_branches: Dict[DevelopmentCategory, DevelopmentBranch] = {}
        self.max_concurrent_developments: int = 2
        self._initialize_tree()

    def _initialize_tree(self) -> None:
        """Initialize all development nodes."""

        # ============ AERODYNAMICS TREE ============

        # Base aero upgrade (required before specializing)
        self.nodes["aero_base"] = DevelopmentNode(
            name="aero_base",
            description="Baseline Aerodynamic Package",
            category=DevelopmentCategory.AERODYNAMICS,
            branch=None,
            cost=8,
            development_time=2,
            stat_changes={"downforce": 2, "aero_efficiency": 1},
            unlocks=["high_downforce_1", "low_drag_1", "balanced_aero_1"]
        )

        # HIGH DOWNFORCE BRANCH
        self.nodes["high_downforce_1"] = DevelopmentNode(
            name="high_downforce_1",
            description="Enhanced Front Wing - Maximum grip in corners",
            category=DevelopmentCategory.AERODYNAMICS,
            branch=DevelopmentBranch.HIGH_DOWNFORCE,
            cost=12,
            development_time=3,
            stat_changes={"downforce": 4},
            trade_offs={"aero_efficiency": -1},
            prerequisites=["aero_base"],
            exclusive_with=["low_drag_1", "balanced_aero_1"],
            unlocks=["high_downforce_2"]
        )

        self.nodes["high_downforce_2"] = DevelopmentNode(
            name="high_downforce_2",
            description="Aggressive Rear Wing - Dominant in slow corners",
            category=DevelopmentCategory.AERODYNAMICS,
            branch=DevelopmentBranch.HIGH_DOWNFORCE,
            cost=18,
            development_time=4,
            stat_changes={"downforce": 5},
            trade_offs={"aero_efficiency": -2},
            prerequisites=["high_downforce_1"],
            unlocks=["high_downforce_3"]
        )

        self.nodes["high_downforce_3"] = DevelopmentNode(
            name="high_downforce_3",
            description="Maximum Downforce Package - Best in class cornering",
            category=DevelopmentCategory.AERODYNAMICS,
            branch=DevelopmentBranch.HIGH_DOWNFORCE,
            cost=25,
            development_time=5,
            stat_changes={"downforce": 6, "chassis": 2},
            trade_offs={"aero_efficiency": -3},
            prerequisites=["high_downforce_2"]
        )

        # LOW DRAG BRANCH
        self.nodes["low_drag_1"] = DevelopmentNode(
            name="low_drag_1",
            description="Slippery Bodywork - Improved straight-line speed",
            category=DevelopmentCategory.AERODYNAMICS,
            branch=DevelopmentBranch.LOW_DRAG,
            cost=12,
            development_time=3,
            stat_changes={"aero_efficiency": 4},
            trade_offs={"downforce": -1},
            prerequisites=["aero_base"],
            exclusive_with=["high_downforce_1", "balanced_aero_1"],
            unlocks=["low_drag_2"]
        )

        self.nodes["low_drag_2"] = DevelopmentNode(
            name="low_drag_2",
            description="DRS Optimization - Enhanced overtaking ability",
            category=DevelopmentCategory.AERODYNAMICS,
            branch=DevelopmentBranch.LOW_DRAG,
            cost=18,
            development_time=4,
            stat_changes={"aero_efficiency": 5},
            trade_offs={"downforce": -2},
            prerequisites=["low_drag_1"],
            unlocks=["low_drag_3"]
        )

        self.nodes["low_drag_3"] = DevelopmentNode(
            name="low_drag_3",
            description="Monza Special - Ultimate top speed",
            category=DevelopmentCategory.AERODYNAMICS,
            branch=DevelopmentBranch.LOW_DRAG,
            cost=25,
            development_time=5,
            stat_changes={"aero_efficiency": 6, "power_unit": 2},
            trade_offs={"downforce": -3},
            prerequisites=["low_drag_2"]
        )

        # BALANCED AERO BRANCH
        self.nodes["balanced_aero_1"] = DevelopmentNode(
            name="balanced_aero_1",
            description="Versatile Aero Package - Good all-around performance",
            category=DevelopmentCategory.AERODYNAMICS,
            branch=DevelopmentBranch.BALANCED_AERO,
            cost=14,
            development_time=3,
            stat_changes={"downforce": 2, "aero_efficiency": 2},
            prerequisites=["aero_base"],
            exclusive_with=["high_downforce_1", "low_drag_1"],
            unlocks=["balanced_aero_2"]
        )

        self.nodes["balanced_aero_2"] = DevelopmentNode(
            name="balanced_aero_2",
            description="Adaptive Wing Elements - Flexible setup options",
            category=DevelopmentCategory.AERODYNAMICS,
            branch=DevelopmentBranch.BALANCED_AERO,
            cost=20,
            development_time=4,
            stat_changes={"downforce": 3, "aero_efficiency": 3},
            prerequisites=["balanced_aero_1"]
        )

        # ============ POWER UNIT TREE ============

        self.nodes["pu_base"] = DevelopmentNode(
            name="pu_base",
            description="Power Unit Optimization",
            category=DevelopmentCategory.POWER_UNIT,
            branch=None,
            cost=10,
            development_time=2,
            stat_changes={"power_unit": 2},
            unlocks=["raw_power_1", "efficiency_1", "reliability_focus_1"]
        )

        # RAW POWER BRANCH
        self.nodes["raw_power_1"] = DevelopmentNode(
            name="raw_power_1",
            description="Aggressive Engine Mapping - More horsepower",
            category=DevelopmentCategory.POWER_UNIT,
            branch=DevelopmentBranch.RAW_POWER,
            cost=15,
            development_time=3,
            stat_changes={"power_unit": 5},
            trade_offs={"reliability": -2},
            prerequisites=["pu_base"],
            exclusive_with=["efficiency_1", "reliability_focus_1"],
            unlocks=["raw_power_2"]
        )

        self.nodes["raw_power_2"] = DevelopmentNode(
            name="raw_power_2",
            description="Maximum Power Mode - Qualifying beast",
            category=DevelopmentCategory.POWER_UNIT,
            branch=DevelopmentBranch.RAW_POWER,
            cost=22,
            development_time=4,
            stat_changes={"power_unit": 6},
            trade_offs={"reliability": -3},
            prerequisites=["raw_power_1"]
        )

        # EFFICIENCY BRANCH
        self.nodes["efficiency_1"] = DevelopmentNode(
            name="efficiency_1",
            description="Energy Recovery Upgrade - Better fuel efficiency",
            category=DevelopmentCategory.POWER_UNIT,
            branch=DevelopmentBranch.EFFICIENCY,
            cost=14,
            development_time=3,
            stat_changes={"power_unit": 3, "aero_efficiency": 2},
            prerequisites=["pu_base"],
            exclusive_with=["raw_power_1", "reliability_focus_1"],
            unlocks=["efficiency_2"]
        )

        self.nodes["efficiency_2"] = DevelopmentNode(
            name="efficiency_2",
            description="Advanced Hybrid System - Optimal power delivery",
            category=DevelopmentCategory.POWER_UNIT,
            branch=DevelopmentBranch.EFFICIENCY,
            cost=20,
            development_time=4,
            stat_changes={"power_unit": 4, "aero_efficiency": 2, "reliability": 1},
            prerequisites=["efficiency_1"]
        )

        # RELIABILITY FOCUS BRANCH
        self.nodes["reliability_focus_1"] = DevelopmentNode(
            name="reliability_focus_1",
            description="Bulletproof Components - Never break down",
            category=DevelopmentCategory.POWER_UNIT,
            branch=DevelopmentBranch.RELIABILITY_FOCUS,
            cost=12,
            development_time=3,
            stat_changes={"reliability": 5, "power_unit": 1},
            prerequisites=["pu_base"],
            exclusive_with=["raw_power_1", "efficiency_1"],
            unlocks=["reliability_focus_2"]
        )

        self.nodes["reliability_focus_2"] = DevelopmentNode(
            name="reliability_focus_2",
            description="Race-Hardened Engine - Consistent performer",
            category=DevelopmentCategory.POWER_UNIT,
            branch=DevelopmentBranch.RELIABILITY_FOCUS,
            cost=18,
            development_time=4,
            stat_changes={"reliability": 6, "power_unit": 2},
            prerequisites=["reliability_focus_1"]
        )

        # ============ CHASSIS TREE ============

        self.nodes["chassis_base"] = DevelopmentNode(
            name="chassis_base",
            description="Chassis Rigidity Improvement",
            category=DevelopmentCategory.CHASSIS,
            branch=None,
            cost=8,
            development_time=2,
            stat_changes={"chassis": 2},
            unlocks=["mechanical_grip_1", "aero_balance_1"]
        )

        # MECHANICAL GRIP BRANCH
        self.nodes["mechanical_grip_1"] = DevelopmentNode(
            name="mechanical_grip_1",
            description="Suspension Geometry Update - Better tire contact",
            category=DevelopmentCategory.CHASSIS,
            branch=DevelopmentBranch.MECHANICAL_GRIP,
            cost=12,
            development_time=3,
            stat_changes={"chassis": 4, "tire_cooling": 2},
            prerequisites=["chassis_base"],
            exclusive_with=["aero_balance_1"],
            unlocks=["mechanical_grip_2"]
        )

        self.nodes["mechanical_grip_2"] = DevelopmentNode(
            name="mechanical_grip_2",
            description="Advanced Dampers - Superior low-speed handling",
            category=DevelopmentCategory.CHASSIS,
            branch=DevelopmentBranch.MECHANICAL_GRIP,
            cost=18,
            development_time=4,
            stat_changes={"chassis": 5, "tire_cooling": 3},
            prerequisites=["mechanical_grip_1"]
        )

        # AERO BALANCE BRANCH
        self.nodes["aero_balance_1"] = DevelopmentNode(
            name="aero_balance_1",
            description="Active Aero Integration - Chassis works with aero",
            category=DevelopmentCategory.CHASSIS,
            branch=DevelopmentBranch.AERO_BALANCE,
            cost=14,
            development_time=3,
            stat_changes={"chassis": 3, "downforce": 2},
            prerequisites=["chassis_base"],
            exclusive_with=["mechanical_grip_1"],
            unlocks=["aero_balance_2"]
        )

        self.nodes["aero_balance_2"] = DevelopmentNode(
            name="aero_balance_2",
            description="Ground Effect Optimization - Maximum floor performance",
            category=DevelopmentCategory.CHASSIS,
            branch=DevelopmentBranch.AERO_BALANCE,
            cost=20,
            development_time=4,
            stat_changes={"chassis": 4, "downforce": 3, "aero_efficiency": 1},
            prerequisites=["aero_balance_1"]
        )

        # ============ TIRE MANAGEMENT TREE ============

        self.nodes["tire_base"] = DevelopmentNode(
            name="tire_base",
            description="Basic Cooling Improvements",
            category=DevelopmentCategory.TIRES,
            branch=None,
            cost=6,
            development_time=2,
            stat_changes={"tire_cooling": 3},
            unlocks=["aggressive_cooling_1", "conservative_cooling_1"]
        )

        # AGGRESSIVE COOLING BRANCH
        self.nodes["aggressive_cooling_1"] = DevelopmentNode(
            name="aggressive_cooling_1",
            description="Brake Duct Redesign - Quick tire warm-up",
            category=DevelopmentCategory.TIRES,
            branch=DevelopmentBranch.AGGRESSIVE_COOLING,
            cost=10,
            development_time=3,
            stat_changes={"tire_cooling": 4},
            trade_offs={"aero_efficiency": -1},
            prerequisites=["tire_base"],
            exclusive_with=["conservative_cooling_1"],
            unlocks=["aggressive_cooling_2"]
        )

        self.nodes["aggressive_cooling_2"] = DevelopmentNode(
            name="aggressive_cooling_2",
            description="Advanced Thermal Management - Optimal operating window",
            category=DevelopmentCategory.TIRES,
            branch=DevelopmentBranch.AGGRESSIVE_COOLING,
            cost=15,
            development_time=4,
            stat_changes={"tire_cooling": 5, "chassis": 1},
            trade_offs={"aero_efficiency": -1},
            prerequisites=["aggressive_cooling_1"]
        )

        # CONSERVATIVE COOLING BRANCH
        self.nodes["conservative_cooling_1"] = DevelopmentNode(
            name="conservative_cooling_1",
            description="Endurance Setup - Make tires last longer",
            category=DevelopmentCategory.TIRES,
            branch=DevelopmentBranch.CONSERVATIVE_COOLING,
            cost=10,
            development_time=3,
            stat_changes={"tire_cooling": 3, "reliability": 2},
            prerequisites=["tire_base"],
            exclusive_with=["aggressive_cooling_1"],
            unlocks=["conservative_cooling_2"]
        )

        self.nodes["conservative_cooling_2"] = DevelopmentNode(
            name="conservative_cooling_2",
            description="One-Stop Special - Ultimate tire preservation",
            category=DevelopmentCategory.TIRES,
            branch=DevelopmentBranch.CONSERVATIVE_COOLING,
            cost=14,
            development_time=4,
            stat_changes={"tire_cooling": 5, "reliability": 2},
            prerequisites=["conservative_cooling_1"]
        )

    def get_available_nodes(self) -> List[DevelopmentNode]:
        """Get nodes that can currently be developed."""
        available = []

        for name, node in self.nodes.items():
            if node.is_completed or node.is_in_progress:
                continue

            # Check prerequisites
            prereqs_met = all(
                self.nodes[prereq].is_completed
                for prereq in node.prerequisites
            )
            if not prereqs_met:
                continue

            # Check exclusivity
            excluded = any(
                self.nodes[excl].is_completed or self.nodes[excl].is_in_progress
                for excl in node.exclusive_with
                if excl in self.nodes
            )
            if excluded:
                continue

            available.append(node)

        return available

    def get_scaling_cost(self, node: DevelopmentNode, car: 'Car') -> int:
        """Get cost with scaling based on current stats."""
        # Higher stats = more expensive to develop
        relevant_stat = 0
        for stat_name in node.stat_changes.keys():
            if hasattr(car, stat_name):
                relevant_stat = max(relevant_stat, getattr(car, stat_name))

        # Scale cost based on current level
        if relevant_stat >= 85:
            multiplier = 2.0
        elif relevant_stat >= 75:
            multiplier = 1.5
        elif relevant_stat >= 65:
            multiplier = 1.2
        else:
            multiplier = 1.0

        return int(node.cost * multiplier)

    def start_development(self, node_name: str, car: 'Car', budget: float) -> Tuple[bool, str]:
        """
        Start developing a node.
        Returns (success, message).
        """
        if node_name not in self.nodes:
            return False, "Unknown development node."

        node = self.nodes[node_name]

        if node.is_completed:
            return False, "This development is already completed."

        if node.is_in_progress:
            return False, "This development is already in progress."

        if len(self.active_developments) >= self.max_concurrent_developments:
            return False, f"Maximum {self.max_concurrent_developments} concurrent developments allowed."

        cost = self.get_scaling_cost(node, car)
        if budget < cost:
            return False, f"Insufficient budget. Need ${cost}M, have ${budget:.1f}M."

        # Check prerequisites
        for prereq in node.prerequisites:
            if not self.nodes[prereq].is_completed:
                return False, f"Prerequisite '{self.nodes[prereq].description}' not completed."

        # Check exclusivity
        for excl in node.exclusive_with:
            if self.nodes[excl].is_completed or self.nodes[excl].is_in_progress:
                return False, f"Cannot develop - incompatible with '{self.nodes[excl].description}'."

        # Start development
        node.is_in_progress = True
        self.active_developments.append(ActiveDevelopment(
            node_name=node_name,
            races_remaining=node.development_time,
            total_races=node.development_time
        ))

        # Track branch choice
        if node.branch and node.category not in self.chosen_branches:
            self.chosen_branches[node.category] = node.branch

        return True, f"Started development: {node.description} (${cost}M, {node.development_time} races)"

    def advance_race(self, car: 'Car') -> List[str]:
        """
        Progress all active developments.
        Returns list of completion messages.
        """
        messages = []
        completed = []

        for dev in self.active_developments:
            dev.races_remaining -= 1

            if dev.races_remaining <= 0:
                node = self.nodes[dev.node_name]
                node.is_completed = True
                node.is_in_progress = False
                self.completed_nodes.append(dev.node_name)
                completed.append(dev)

                # Apply stat changes
                for stat_name, change in node.stat_changes.items():
                    if hasattr(car, stat_name):
                        current = getattr(car, stat_name)
                        new_val = min(99, max(0, current + change))
                        setattr(car, stat_name, new_val)

                # Apply trade-offs
                for stat_name, change in node.trade_offs.items():
                    if hasattr(car, stat_name):
                        current = getattr(car, stat_name)
                        new_val = min(99, max(0, current + change))
                        setattr(car, stat_name, new_val)

                messages.append(f"DEVELOPMENT COMPLETE: {node.description}")

                # Detail the changes
                for stat_name, change in node.stat_changes.items():
                    sign = "+" if change > 0 else ""
                    messages.append(f"  {stat_name.replace('_', ' ').title()}: {sign}{change}")
                for stat_name, change in node.trade_offs.items():
                    sign = "+" if change > 0 else ""
                    messages.append(f"  {stat_name.replace('_', ' ').title()}: {sign}{change} (trade-off)")

        # Remove completed developments
        for dev in completed:
            self.active_developments.remove(dev)

        return messages

    def get_progress_display(self) -> str:
        """Display current development progress."""
        lines = [
            "\n" + "=" * 60,
            "  ACTIVE DEVELOPMENTS",
            "=" * 60,
        ]

        if not self.active_developments:
            lines.append("  No active developments.")
        else:
            for dev in self.active_developments:
                node = self.nodes[dev.node_name]
                progress = dev.total_races - dev.races_remaining
                bar_filled = int((progress / dev.total_races) * 20)
                bar_empty = 20 - bar_filled
                bar = "[" + "=" * bar_filled + " " * bar_empty + "]"

                lines.append(f"  {node.description}")
                lines.append(f"    Progress: {bar} {dev.races_remaining} races remaining")

        lines.append("=" * 60)
        return "\n".join(lines)

    def display_development_tree(self, car: 'Car', budget: float) -> str:
        """Display the full development tree."""
        lines = [
            "\n" + "=" * 70,
            "  CAR DEVELOPMENT TREE",
            "=" * 70,
            f"  Budget: ${budget:.1f}M  |  Active: {len(self.active_developments)}/{self.max_concurrent_developments}",
            "=" * 70,
        ]

        # Group by category
        for category in DevelopmentCategory:
            lines.append(f"\n  {category.value.upper()}")
            lines.append("-" * 60)

            # Show chosen branch if any
            if category in self.chosen_branches:
                lines.append(f"  Chosen Path: {self.chosen_branches[category].value}")

            category_nodes = [n for n in self.nodes.values() if n.category == category]

            for node in category_nodes:
                cost = self.get_scaling_cost(node, car)

                if node.is_completed:
                    status = "[DONE]"
                elif node.is_in_progress:
                    dev = next((d for d in self.active_developments if d.node_name == node.name), None)
                    if dev:
                        status = f"[{dev.races_remaining} races left]"
                    else:
                        status = "[IN PROGRESS]"
                elif node in self.get_available_nodes():
                    if budget >= cost:
                        status = f"[${cost}M]"
                    else:
                        status = f"[${cost}M] X"
                else:
                    status = "[LOCKED]"

                # Indent based on prerequisites
                indent = "  " * (len(node.prerequisites) + 1)
                branch_str = f" ({node.branch.value})" if node.branch else ""

                lines.append(f"{indent}{node.description}{branch_str}")
                lines.append(f"{indent}  {status}")

                # Show effects for available nodes
                if node in self.get_available_nodes() and not node.is_completed:
                    effects = []
                    for stat, val in node.stat_changes.items():
                        effects.append(f"{stat.replace('_', ' ').title()} +{val}")
                    for stat, val in node.trade_offs.items():
                        effects.append(f"{stat.replace('_', ' ').title()} {val}")
                    if effects:
                        lines.append(f"{indent}  Effects: {', '.join(effects)}")

        lines.append("\n" + "=" * 70)
        lines.append("  X = Cannot afford  |  LOCKED = Prerequisites not met")
        return "\n".join(lines)

    def display_available_developments(self, car: 'Car', budget: float) -> str:
        """Display only available developments for easier selection."""
        available = self.get_available_nodes()

        lines = [
            "\n" + "=" * 70,
            "  AVAILABLE DEVELOPMENTS",
            "=" * 70,
            f"  Budget: ${budget:.1f}M  |  Slots: {len(self.active_developments)}/{self.max_concurrent_developments}",
            "-" * 70,
        ]

        if not available:
            lines.append("  No developments currently available.")
            lines.append("  Complete current developments to unlock more options.")
        else:
            for i, node in enumerate(available, 1):
                cost = self.get_scaling_cost(node, car)
                affordable = "  " if budget >= cost else "X "
                branch_str = f" [{node.branch.value}]" if node.branch else ""

                lines.append(f"  {affordable}[{i}] {node.description}{branch_str}")
                lines.append(f"       Cost: ${cost}M  |  Time: {node.development_time} races")

                # Show effects
                effects = []
                for stat, val in node.stat_changes.items():
                    effects.append(f"{stat.replace('_', ' ').title()} +{val}")
                for stat, val in node.trade_offs.items():
                    effects.append(f"{stat.replace('_', ' ').title()} {val}")
                lines.append(f"       Effects: {', '.join(effects)}")
                lines.append("")

        lines.append("=" * 70)
        lines.append("  X = Cannot afford")
        return "\n".join(lines)

    def reset_for_new_season(self) -> None:
        """Optionally reset some developments for new season (regulations)."""
        # For now, keep all developments - could add regulation changes later
        pass
