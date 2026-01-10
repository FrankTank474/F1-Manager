"""Weekly Email/Inbox System - Messages between races"""

import random
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import List, Dict, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Driver, Team


class MessageType(Enum):
    DRIVER_COMPLAINT = "Driver"
    SPONSOR_WARNING = "Sponsor"
    RIVAL_NEWS = "Rival Team"
    TRANSFER_RUMOR = "Transfer"
    TEAM_UPDATE = "Team"
    MEDIA = "Media"
    FIA = "FIA"
    CONTRACT = "Contract"


class MessagePriority(Enum):
    URGENT = "URGENT"
    IMPORTANT = "Important"
    NORMAL = "Normal"
    INFO = "Info"


@dataclass
class InboxMessage:
    """A single message in the inbox."""
    message_type: MessageType
    priority: MessagePriority
    sender: str
    subject: str
    body: str
    race_number: int
    is_read: bool = False
    requires_action: bool = False
    action_type: Optional[str] = None  # Type of action needed
    action_data: Optional[Dict] = None  # Data for the action

    def mark_read(self) -> None:
        self.is_read = True


class InboxManager:
    """Manages the team inbox with messages between races."""

    def __init__(self):
        self.messages: List[InboxMessage] = []
        self.current_race: int = 0
        self.current_season: int = 1

    def get_unread_count(self) -> int:
        """Get number of unread messages."""
        return sum(1 for m in self.messages if not m.is_read)

    def get_urgent_count(self) -> int:
        """Get number of urgent unread messages."""
        return sum(1 for m in self.messages
                   if not m.is_read and m.priority == MessagePriority.URGENT)

    def add_message(self, message: InboxMessage) -> None:
        """Add a message to the inbox."""
        self.messages.insert(0, message)  # New messages at top
        # Keep inbox manageable
        if len(self.messages) > 50:
            self.messages = self.messages[:50]

    def generate_race_messages(
        self,
        player_team: 'Team',
        all_teams: List['Team'],
        race_results: List[Tuple],
        driver_morale: Dict[str, int],
        sponsor_objectives_met: int,
        sponsor_objectives_total: int,
        expiring_contracts: List[str],
        active_rivalries: List[Tuple[str, str, int]]
    ) -> List[InboxMessage]:
        """
        Generate messages after a race.
        Returns list of new messages.
        """
        new_messages = []

        # === DRIVER COMPLAINTS ===
        for driver in player_team.drivers:
            morale = driver_morale.get(driver.name, 70)

            # Low morale complaint
            if morale < 40 and random.random() < 0.6:
                complaints = [
                    ("Feeling undervalued", f"I've been feeling like my contributions aren't being recognized. My results haven't been where I want them, and I'm starting to question if this is the right environment for me."),
                    ("Need more support", f"The car just isn't giving me what I need to compete. I need the team to prioritize upgrades that suit my driving style."),
                    ("Frustrated with results", f"These results are not acceptable. I came here to win, and right now that's not happening. Something needs to change."),
                ]
                subject, body = random.choice(complaints)
                new_messages.append(InboxMessage(
                    message_type=MessageType.DRIVER_COMPLAINT,
                    priority=MessagePriority.IMPORTANT,
                    sender=driver.name,
                    subject=subject,
                    body=body,
                    race_number=self.current_race
                ))

            # Beaten by teammate complaint
            if hasattr(driver, 'times_beaten_by_teammate') and driver.times_beaten_by_teammate >= 3:
                if random.random() < 0.4:
                    new_messages.append(InboxMessage(
                        message_type=MessageType.DRIVER_COMPLAINT,
                        priority=MessagePriority.NORMAL,
                        sender=driver.name,
                        subject="Teammate comparison",
                        body=f"I've noticed I've been consistently behind my teammate. I want to assure you that I'm working hard to turn this around, but I could use some additional support from the engineering side.",
                        race_number=self.current_race
                    ))

        # === SPONSOR WARNINGS ===
        if sponsor_objectives_total > 0:
            success_rate = sponsor_objectives_met / sponsor_objectives_total
            if success_rate < 0.5 and random.random() < 0.7:
                severity = "very disappointed" if success_rate < 0.3 else "concerned"
                new_messages.append(InboxMessage(
                    message_type=MessageType.SPONSOR_WARNING,
                    priority=MessagePriority.URGENT if success_rate < 0.3 else MessagePriority.IMPORTANT,
                    sender="Sponsor Relations",
                    subject="Sponsor performance review",
                    body=f"Our title sponsor has expressed that they are {severity} with recent results. We've only met {int(success_rate * 100)}% of our objectives. If this continues, they may reconsider their commitment for next season.",
                    race_number=self.current_race,
                    requires_action=success_rate < 0.3
                ))

        # === RIVAL TEAM NEWS ===
        if random.random() < 0.4:
            rival_team = random.choice([t for t in all_teams if t != player_team])
            news_types = [
                (f"{rival_team.name} announces major upgrade package",
                 f"Sources indicate that {rival_team.name} will bring significant aerodynamic updates to the next race. This could shake up the competitive order."),
                (f"Internal tensions at {rival_team.name}",
                 f"Reports suggest there may be disagreements within {rival_team.name} about development direction. This could work in our favor."),
                (f"{rival_team.name} signs new technical director",
                 f"{rival_team.name} has brought in a new technical director from outside F1. Early indications suggest aggressive development plans."),
                (f"Budget concerns at {rival_team.name}",
                 f"Industry sources suggest {rival_team.name} may be facing budget constraints that could limit their development for the rest of the season."),
            ]
            subject, body = random.choice(news_types)
            new_messages.append(InboxMessage(
                message_type=MessageType.RIVAL_NEWS,
                priority=MessagePriority.INFO,
                sender="Intel Report",
                subject=subject,
                body=body,
                race_number=self.current_race
            ))

        # === TRANSFER RUMORS ===
        if random.random() < 0.3:
            # Rumor about a driver being available
            other_drivers = []
            for team in all_teams:
                if team != player_team:
                    for d in team.drivers:
                        other_drivers.append((d, team))

            if other_drivers:
                rumor_driver, rumor_team = random.choice(other_drivers)
                rumor_types = [
                    (f"{rumor_driver.name} linked with move",
                     f"Sources close to {rumor_driver.name} suggest the driver may be considering a move away from {rumor_team.name}. Could be an opportunity if we have the budget."),
                    (f"{rumor_driver.name} contract talks stall",
                     f"Negotiations between {rumor_driver.name} and {rumor_team.name} have reportedly hit a roadblock. The driver may become available."),
                    (f"{rumor_team.name} considering driver change",
                     f"Paddock rumors suggest {rumor_team.name} is evaluating their driver lineup. {rumor_driver.name}'s position may not be secure."),
                ]
                subject, body = random.choice(rumor_types)
                new_messages.append(InboxMessage(
                    message_type=MessageType.TRANSFER_RUMOR,
                    priority=MessagePriority.NORMAL,
                    sender="Paddock Insider",
                    subject=subject,
                    body=body,
                    race_number=self.current_race
                ))

        # === TEAM UPDATES ===
        if random.random() < 0.5:
            updates = [
                ("Development progress report",
                 f"The factory is making good progress on upcoming upgrades. We expect to have new components ready within the next few races."),
                ("Wind tunnel session results",
                 f"Latest wind tunnel data shows promising gains. The engineers are optimistic about our development direction."),
                ("Budget update",
                 f"Finance has completed their mid-season review. We remain within budget and have flexibility for strategic investments."),
                ("Facility upgrade complete",
                 f"Our new simulator upgrade is now operational. The drivers will benefit from improved preparation for upcoming circuits."),
            ]
            subject, body = random.choice(updates)
            new_messages.append(InboxMessage(
                message_type=MessageType.TEAM_UPDATE,
                priority=MessagePriority.INFO,
                sender="Team Operations",
                subject=subject,
                body=body,
                race_number=self.current_race
            ))

        # === CONTRACT ALERTS ===
        for driver_name in expiring_contracts:
            new_messages.append(InboxMessage(
                message_type=MessageType.CONTRACT,
                priority=MessagePriority.URGENT,
                sender="HR Department",
                subject=f"{driver_name} contract expires soon",
                body=f"{driver_name}'s contract expires at the end of this season. We need to begin negotiations soon or risk losing the driver to a competitor.",
                race_number=self.current_race,
                requires_action=True,
                action_type="negotiate_contract",
                action_data={"driver_name": driver_name}
            ))

        # === RIVALRY DRAMA ===
        for d1, d2, intensity in active_rivalries:
            if intensity >= 60 and random.random() < 0.5:
                # Check if either driver is on player team
                player_driver_names = [d.name for d in player_team.drivers]
                if d1 in player_driver_names or d2 in player_driver_names:
                    player_driver = d1 if d1 in player_driver_names else d2
                    rival_driver = d2 if d1 in player_driver_names else d1

                    new_messages.append(InboxMessage(
                        message_type=MessageType.MEDIA,
                        priority=MessagePriority.NORMAL,
                        sender="Media Relations",
                        subject=f"Media questions about {player_driver}/{rival_driver} rivalry",
                        body=f"Journalists are asking about the ongoing tension between {player_driver} and {rival_driver}. The intense battles have caught media attention. We may want to address this in the next press conference.",
                        race_number=self.current_race
                    ))

        # === MEDIA INQUIRIES ===
        if random.random() < 0.25:
            media_topics = [
                ("Press conference request",
                 "Several major outlets have requested an exclusive interview with our team principal to discuss the season so far."),
                ("Documentary opportunity",
                 "A streaming platform has expressed interest in featuring our team in an upcoming F1 documentary series."),
                ("Social media milestone",
                 "Our team's social media following has grown significantly this season. Marketing suggests capitalizing on this with more content."),
            ]
            subject, body = random.choice(media_topics)
            new_messages.append(InboxMessage(
                message_type=MessageType.MEDIA,
                priority=MessagePriority.INFO,
                sender="Media Relations",
                subject=subject,
                body=body,
                race_number=self.current_race
            ))

        # Add all new messages to inbox
        for msg in new_messages:
            self.add_message(msg)

        return new_messages

    def generate_season_end_messages(
        self,
        player_team: 'Team',
        final_position: int,
        prize_money: int
    ) -> List[InboxMessage]:
        """Generate end of season messages."""
        new_messages = []

        # Season summary
        if final_position <= 3:
            subject = "Congratulations on an outstanding season!"
            body = f"What an incredible season! Finishing P{final_position} in the championship exceeded all expectations. The board is extremely pleased with our progress."
            priority = MessagePriority.IMPORTANT
        elif final_position <= 6:
            subject = "Solid season performance"
            body = f"A respectable P{final_position} finish in the championship. The board acknowledges the team's hard work and looks forward to building on this next year."
            priority = MessagePriority.NORMAL
        else:
            subject = "Season review"
            body = f"The season has concluded with a P{final_position} finish. While there's room for improvement, the board remains committed to the team's long-term development."
            priority = MessagePriority.NORMAL

        new_messages.append(InboxMessage(
            message_type=MessageType.TEAM_UPDATE,
            priority=priority,
            sender="Board of Directors",
            subject=subject,
            body=body,
            race_number=self.current_race
        ))

        # Prize money notification
        new_messages.append(InboxMessage(
            message_type=MessageType.TEAM_UPDATE,
            priority=MessagePriority.IMPORTANT,
            sender="Finance Department",
            subject=f"Season prize money: ${prize_money}M",
            body=f"The FIA has confirmed our championship prize money of ${prize_money}M based on our P{final_position} finish. These funds have been added to our operating budget for next season.",
            race_number=self.current_race
        ))

        for msg in new_messages:
            self.add_message(msg)

        return new_messages

    def advance_race(self) -> None:
        """Called after each race."""
        self.current_race += 1

    def clear_old_messages(self) -> None:
        """Clear messages from previous season."""
        self.messages = [m for m in self.messages if m.race_number >= self.current_race - 10]

    def new_season(self) -> None:
        """Start new season."""
        self.current_season += 1
        self.current_race = 0
        self.clear_old_messages()

    def display_inbox(self) -> str:
        """Display the inbox."""
        unread = self.get_unread_count()
        urgent = self.get_urgent_count()

        lines = [
            "\n" + "=" * 70,
            f"  INBOX ({unread} unread" + (f", {urgent} urgent" if urgent > 0 else "") + ")",
            "=" * 70,
        ]

        if not self.messages:
            lines.append("  No messages.")
        else:
            lines.append(f"  {'#':<3} {'!':<3} {'From':<18} {'Subject':<35}")
            lines.append("-" * 70)

            for i, msg in enumerate(self.messages[:15], 1):  # Show last 15
                read_marker = " " if msg.is_read else "*"
                priority_marker = "!" if msg.priority in [MessagePriority.URGENT, MessagePriority.IMPORTANT] else " "

                sender = msg.sender[:16] if len(msg.sender) > 16 else msg.sender
                subject = msg.subject[:33] if len(msg.subject) > 33 else msg.subject

                if msg.priority == MessagePriority.URGENT:
                    lines.append(f"  {i:<3} {read_marker}{priority_marker} {sender:<18} {subject:<35}")
                else:
                    lines.append(f"  {i:<3} {read_marker}{priority_marker} {sender:<18} {subject:<35}")

        lines.append("=" * 70)
        lines.append("  * = Unread  ! = Important/Urgent")
        return "\n".join(lines)

    def display_message(self, index: int) -> Optional[str]:
        """Display a specific message."""
        if index < 0 or index >= len(self.messages):
            return None

        msg = self.messages[index]
        msg.mark_read()

        priority_str = f"[{msg.priority.value}]" if msg.priority != MessagePriority.NORMAL else ""

        lines = [
            "\n" + "=" * 60,
            f"  {msg.message_type.value}: {msg.subject} {priority_str}",
            "=" * 60,
            f"  From: {msg.sender}",
            f"  Race: {msg.race_number}",
            "-" * 60,
            "",
        ]

        # Word wrap the body
        words = msg.body.split()
        current_line = "  "
        for word in words:
            if len(current_line) + len(word) + 1 > 58:
                lines.append(current_line)
                current_line = "  " + word
            else:
                current_line += " " + word if current_line != "  " else word

        if current_line.strip():
            lines.append(current_line)

        lines.append("")
        lines.append("=" * 60)

        if msg.requires_action:
            lines.append(f"  [This message requires your attention]")

        return "\n".join(lines)

    def get_notification_summary(self) -> Optional[str]:
        """Get a brief notification if there are urgent messages."""
        urgent = self.get_urgent_count()
        unread = self.get_unread_count()

        if urgent > 0:
            return f"INBOX: {urgent} urgent message(s) require attention!"
        elif unread > 0:
            return f"INBOX: {unread} unread message(s)"
        return None
