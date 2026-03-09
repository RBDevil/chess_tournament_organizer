from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from core import Game, Player, Tournament


class TournamentStorage:
    """Handles saving, loading, and exporting tournament data."""

    SAVE_VERSION: str = "1.0"

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    @staticmethod
    def save_tournament(
        tournament: Tournament,
        filepath: str,
    ) -> None:
        """Save full tournament state to JSON.

        Args:
            tournament: Tournament instance
            filepath: Output file path (.json)
        """

        data: Dict = {
            "version": TournamentStorage.SAVE_VERSION,
            "timestamp": datetime.utcnow().isoformat(),
            "round": tournament.round_number,
            "max_boards": tournament.max_boards,
            "players": {
                name: {
                    "score": p.score,
                    "games_played": p.games_played,
                    "opponents": list(p.opponents),
                }
                for name, p in tournament.players.items()
            },
            "history": [
                {
                    "white": g.white,
                    "black": g.black,
                    "round": g.round_number,
                    "table": g.table,
                    "result": g.result,
                }
                for g in tournament.history
            ],
        }

        path: Path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_tournament(filepath: str) -> Tournament:
        """Load tournament from JSON.

        Args:
            filepath: Path to save file

        Returns:
            Restored Tournament object
        """

        path: Path = Path(filepath)

        with path.open("r", encoding="utf-8") as f:
            data: Dict = json.load(f)

        tournament: Tournament = Tournament()

        tournament.round_number = data["round"]
        tournament.max_boards = data["max_boards"]
        tournament.started = True

        # Restore players
        for name, pdata in data["players"].items():
            player: Player = Player(
                name=name,
                score=pdata["score"],
                games_played=pdata["games_played"],
            )

            player.opponents = set(pdata["opponents"])
            tournament.players[name] = player

        # Restore history
        for g in data["history"]:
            game: Game = Game(
                white=g["white"],
                black=g["black"],
                round_number=g["round"],
                table=g["table"],
                result=g["result"],
            )

            tournament.history.append(game)

        return tournament

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    @staticmethod
    def export_games_csv(
        tournament: Tournament,
        filepath: str,
    ) -> None:
        """Export all games to CSV for analysis / Elo processing.

        Args:
            tournament: Tournament instance
            filepath: Output CSV file
        """

        path: Path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            writer.writerow(
                [
                    "round",
                    "table",
                    "white",
                    "black",
                    "result",
                ]
            )

            for game in tournament.history:
                writer.writerow(
                    [
                        game.round_number,
                        game.table,
                        game.white,
                        game.black,
                        game.result,
                    ]
                )