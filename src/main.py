#!/usr/bin/env python3
"""F1 Manager 2026 - Entry Point"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.game import Game


def main():
    """Main entry point for F1 Manager 2026."""
    try:
        game = Game()
        game.run()
    except KeyboardInterrupt:
        print("\n\n  Game interrupted. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
