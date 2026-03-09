from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from elo_manager import EloManager


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------


@dataclass
class Player:
    name: str
    score: float = 0.0
    games_played: int = 0
    opponents: Set[str] = field(default_factory=set)
    white_games: int = 0
    black_games: int = 0


@dataclass
class Game:
    """Represents a single game."""

    white: str
    black: str
    round_number: int
    table: int
    result: Optional[str] = None  # "1-0", "0-1", "0.5-0.5"


# -----------------------------------------------------------------------------
# Tournament Logic
# -----------------------------------------------------------------------------


class Tournament:
    """Swiss tournament state and logic with board limits and balanced games."""

    def __init__(self) -> None:
        self.players: Dict[str, Player] = {}
        self.round_number: int = 0

        self.max_boards: int = 3

        self.elo_manager = EloManager(db_path=Path('saves/elo_db.json'))

        # Pairings waiting to be played in this round
        self.pairing_queue: List[Tuple[str, str]] = []

        # Currently active games
        self.active_games: List[Game] = []

        # Track free/occupied tables
        self.free_tables: List[int] = []

        # All finished games
        self.history: List[Game] = []

        self.started: bool = False
        self.ended: bool = False

    # ----------------------------
    # Player Management
    # ----------------------------

    def add_player(self, name: str) -> None:
        if self.started:
            raise ValueError("Cannot add players after tournament start")

        if name in self.players:
            raise ValueError("Player already exists")

        self.players[name] = Player(name=name)


    def remove_player(self, name: str) -> None:
        if name not in self.players:
            raise ValueError(f"Player '{name}' not found")

        player = self.players.pop(name)

        # Remove from pairing queue
        self.pairing_queue = [
            (w, b) for w, b in self.pairing_queue if w != name and b != name
        ]

        # Active games check is handled by UI
        # Remove any remaining active games just in case
        self.active_games = [
            g for g in self.active_games if g.white != name and g.black != name
        ]

        # History is untouched for integrity of past rounds

    # ----------------------------
    # Tournament Flow
    # ----------------------------

    def set_board_limit(self, boards: int) -> None:
        if self.started:
            raise ValueError("Cannot change boards after start")

        if boards < 1:
            raise ValueError("At least one board required")

        self.max_boards = boards

    def start(self) -> None:
        if len(self.players) < 2:
            raise ValueError("At least 2 players required")

        self.started = True
        self.round_number = 0

        # Initialize free tables
        self.free_tables = list(range(1, self.max_boards + 1))

        self.start_next_round()

    def end(self) -> None:
        self.ended = True
        self.active_games.clear()
        self.pairing_queue.clear()
        self.free_tables.clear()

    def start_next_round(self) -> None:
        if not self.started or self.ended:
            return

        if self.active_games or self.pairing_queue:
            raise ValueError("Current round not finished")

        previous_round_games = [g for g in self.history if g.round_number == self.round_number]
        self.elo_manager.update_elos(previous_round_games)
        self.elo_manager.save_db()

        self.round_number += 1

        # Reset tables for new round
        self.free_tables = list(range(1, self.max_boards + 1))

        self.pairing_queue = self._generate_balanced_pairings()
        self._fill_active_games()

    def _fill_active_games(self) -> None:
        """Move games from queue to free boards."""

        self.free_tables.sort()

        while self.free_tables and self.pairing_queue:
            white, black = self.pairing_queue.pop(0)

            table_number: int = self.free_tables.pop(0)

            game = Game(
                white=white,
                black=black,
                round_number=self.round_number,
                table=table_number,
            )

            self.active_games.append(game)


    # ----------------------------
    # Results
    # ----------------------------

    def submit_result(self, game_index: int, result: str) -> None:
        game: Game = self.active_games[game_index]

        if game.result is not None:
            raise ValueError("Result already entered")

        if result not in {"1-0", "0-1", "0.5-0.5"}:
            raise ValueError("Invalid result")

        game.result = result

        white: Player = self.players[game.white]
        black: Player = self.players[game.black]

        white.games_played += 1
        black.games_played += 1

        white.opponents.add(black.name)
        black.opponents.add(white.name)
        white.white_games += 1
        black.black_games += 1

        if result == "1-0":
            white.score += 1.0
        elif result == "0-1":
            black.score += 1.0
        else:
            white.score += 0.5
            black.score += 0.5

        # Free the table
        self.free_tables.append(game.table)

        # Move to history
        self.history.append(game)
        self.active_games.pop(game_index)

        # Refill boards
        self._fill_active_games()

    def is_round_finished(self) -> bool:
        return not self.active_games and not self.pairing_queue

    # ----------------------------
    # Pairing Logic
    # ----------------------------

    def _generate_balanced_pairings(self) -> List[Tuple[str, str]]:
        """
        Generate pairings prioritizing fairness and Swiss-like constraints.

        Priority order:
        1. Fewest games played
        2. Avoid repeat opponents
        3. Closest score
        4. Color balancing
        """

        sorted_players: List[Player] = sorted(
            self.players.values(),
            key=lambda p: (p.games_played, -p.score, p.name.lower()),
        )

        unpaired: List[Player] = sorted_players.copy()
        pairings: List[Tuple[str, str]] = []

        while len(unpaired) >= 2:
            player_a: Player = unpaired.pop(0)

            best_index: Optional[int] = None
            best_score: Optional[Tuple[int, float, int]] = None

            for index, candidate in enumerate(unpaired):

                repeat_penalty: int = 1 if candidate.name in player_a.opponents else 0
                score_difference: float = abs(player_a.score - candidate.score)

                color_balance_penalty: int = abs(
                    (player_a.white_games - player_a.black_games)
                    + (candidate.white_games - candidate.black_games)
                )

                candidate_score: Tuple[int, float, int] = (
                    repeat_penalty,
                    score_difference,
                    color_balance_penalty,
                )

                if best_score is None or candidate_score < best_score:
                    best_score = candidate_score
                    best_index = index

            if best_index is None:
                best_index = 0

            player_b: Player = unpaired.pop(best_index)

            a_color_bias: int = player_a.white_games - player_a.black_games
            b_color_bias: int = player_b.white_games - player_b.black_games

            if a_color_bias > b_color_bias:
                pairings.append((player_b.name, player_a.name))
            else:
                pairings.append((player_a.name, player_b.name))

        return pairings

    # ----------------------------
    # Queries
    # ----------------------------

    def standings(self) -> List[Player]:
        return sorted(
            self.players.values(),
            key=lambda p: (-p.score, p.games_played, p.name.lower()),
        )