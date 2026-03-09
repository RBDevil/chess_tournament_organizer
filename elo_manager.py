# elo_manager.py

"""
Elo Manager for live Swiss tournaments.

- Stores Elo ratings for players in a JSON file.
- Updates Elo based on completed games.
- Can run live during a tournament.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List


# ----------------------------
# Constants
# ----------------------------

DEFAULT_ELO = 1200
K_FACTOR = 32  # Typical value for club level Elo
DB_PATH = Path("saves/elo_db.json")


# ----------------------------
# Classes
# ----------------------------

class EloManager:
    """Manages Elo ratings for players."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.elos: Dict[str, float] = {}  # player_id -> elo
        self._load_db()

    # ------------------------
    # Database
    # ------------------------

    def _load_db(self) -> None:
        """Load Elo values from JSON DB."""
        if self.db_path.exists():
            with open(self.db_path, "r", encoding="utf-8") as f:
                self.elos = json.load(f)
        else:
            self.elos = {}

    def save_db(self) -> None:
        """Save Elo values to JSON DB."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.elos, f, indent=2)

    # ------------------------
    # Elo Calculation
    # ------------------------

    def update_elos(self, games) -> None:
        """
        Update Elo ratings based on a list of completed games.

        Args:
            games: List of Game objects with .white, .black, and .result
        """
        for game in games:
            if game.result is None:
                continue  # Skip unfinished games

            white_id = game.white
            black_id = game.black

            # Ensure players exist in DB
            if white_id not in self.elos:
                self.elos[white_id] = DEFAULT_ELO
            if black_id not in self.elos:
                self.elos[black_id] = DEFAULT_ELO

            Rw = self.elos[white_id]
            Rb = self.elos[black_id]

            # Expected scores
            Ew = 1 / (1 + 10 ** ((Rb - Rw) / 400))
            Eb = 1 / (1 + 10 ** ((Rw - Rb) / 400))

            # Actual scores
            if game.result == "1-0":
                Sw, Sb = 1, 0
            elif game.result in ["0.5-0.5", "½-½"]:
                Sw, Sb = 0.5, 0.5
            elif game.result == "0-1":
                Sw, Sb = 0, 1
            else:
                continue  # Unknown format

            # Update Elo
            self.elos[white_id] = Rw + K_FACTOR * (Sw - Ew)
            self.elos[black_id] = Rb + K_FACTOR * (Sb - Eb)

        # Save DB after updates
        self.save_db()

    # ------------------------
    # Utilities
    # ------------------------

    def get_elo(self, player_id: str) -> float:
        """Get current Elo for a player (default if missing)."""
        return self.elos.get(player_id, DEFAULT_ELO)

    def get_all_elos(self) -> Dict[str, float]:
        """Return a copy of the Elo dictionary."""
        return dict(self.elos)

if __name__ == '__main__':
    from storage import TournamentStorage

    path = '/home/ad.adasworks.com/boldizsar.verseghi-n/chess_software/autosaves/final_20260306_103438.json'
    tournament = TournamentStorage.load_tournament(path)
    elo = EloManager()
    elo.update_elos(tournament.history)
    print(elo.elos)