"""
Swiss Tournament Manager with PyQt5.
"""

from __future__ import annotations
from datetime import datetime
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from storage import TournamentStorage
from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QTabWidget,
)
from core import Game, Player, Tournament
from PyQt5.QtWidgets import QFileDialog
from storage import TournamentStorage

# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()

        self.tournament: Tournament = Tournament()

        self.setWindowTitle("Swiss Tournament Manager")
        self.setMinimumSize(1100, 700)

        self._init_ui()
        self._set_running_layout()

    # ----------------------------
    # UI Setup
    # ----------------------------

    def _init_ui(self) -> None:
        self.main_widget: QWidget = QWidget()
        self.setCentralWidget(self.main_widget)

        self.main_layout: QGridLayout = QGridLayout()
        self.main_widget.setLayout(self.main_layout)

        # Player box
        self.player_box: QGroupBox = QGroupBox("Players")
        self._init_player_box()

        # Control box
        self.control_box: QGroupBox = QGroupBox("Tournament Control")
        self._init_control_box()

        # Current games
        self.games_box: QGroupBox = QGroupBox("Current Games")
        self._init_games_box()

        # Upcoming games
        self.upcoming_box: QGroupBox = QGroupBox("Upcoming Games (This Round)")
        self._init_upcoming_box()

        # Standings
        self.standings_box: QGroupBox = QGroupBox("Standings")
        self._init_standings_box()

    def _set_running_layout(self) -> None:
        self._clear_layout()

        # TL: Standings (tall) + Upcoming (normal) stacked
        self.main_layout.addWidget(self.standings_box, 0, 0, 2, 1)  # Row 0-1, Col 0, spans 2 rows
        self.main_layout.addWidget(self.upcoming_box, 2, 0)          # Row 2, Col 0

        # TR: Current Games
        self.main_layout.addWidget(self.games_box, 0, 1)

        # BR: Tournament Control
        self.main_layout.addWidget(self.control_box, 1, 1)

        # Bottom-right: Players
        self.main_layout.addWidget(self.player_box, 2, 1)

    def _clear_layout(self) -> None:
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def _init_player_box(self) -> None:
        layout: QVBoxLayout = QVBoxLayout()

        self.player_input: QLineEdit = QLineEdit()
        self.player_input.setPlaceholderText("Player name")

        self.add_player_button: QPushButton = QPushButton("Add Player")
        self.add_player_button.clicked.connect(self._add_player)

        self.player_list: QListWidget = QListWidget()

        self.remove_player_button: QPushButton = QPushButton("Remove Player")
        self.remove_player_button.clicked.connect(self._remove_player)
        self.remove_player_button.setEnabled(False)  # Initially disabled
        layout.addWidget(self.remove_player_button)

        # Enable button only when a player is selected
        self.player_list.itemSelectionChanged.connect(self._update_remove_button_state)

        layout.addWidget(self.player_input)
        layout.addWidget(self.add_player_button)
        layout.addWidget(self.player_list)

        self.player_box.setLayout(layout)

    def _init_control_box(self) -> None:
        layout: QVBoxLayout = QVBoxLayout()

        board_layout: QHBoxLayout = QHBoxLayout()

        board_label: QLabel = QLabel("Boards:")
        self.board_spin: QSpinBox = QSpinBox()
        self.board_spin.setRange(1, 20)
        self.board_spin.setValue(3)

        board_layout.addWidget(board_label)
        board_layout.addWidget(self.board_spin)

        self.load_button = QPushButton("Load Tournament (JSON)")
        self.load_button.clicked.connect(self._load_tournament)

        layout.addWidget(self.load_button)

        self.start_button: QPushButton = QPushButton("Start Tournament")
        self.start_button.clicked.connect(self._start_tournament)

        self.next_round_button: QPushButton = QPushButton("Next Round")
        self.next_round_button.clicked.connect(self._next_round)
        self.next_round_button.setEnabled(False)

        self.end_button: QPushButton = QPushButton("End Tournament")
        self.end_button.clicked.connect(self._end_tournament)
        self.end_button.setEnabled(False)

        self.round_label: QLabel = QLabel("Round: 0")

        layout.addLayout(board_layout)
        layout.addWidget(self.start_button)
        layout.addWidget(self.next_round_button)
        layout.addWidget(self.end_button)
        layout.addWidget(self.round_label)
        layout.addStretch()

        self.control_box.setLayout(layout)

    def _init_games_box(self) -> None:
        layout: QVBoxLayout = QVBoxLayout()

        self.games_table: QTableWidget = QTableWidget(0, 5)
        self.games_table.setHorizontalHeaderLabels(
            ["Table", "White", "Black", "Result", "Submit"]
        )
        self.games_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.games_table)
        self.games_box.setLayout(layout)

    def _init_upcoming_box(self) -> None:
        layout: QVBoxLayout = QVBoxLayout()

        self.upcoming_table: QTableWidget = QTableWidget(0, 3)
        self.upcoming_table.setHorizontalHeaderLabels(
            ["White", "Black", "Status"]
        )
        self.upcoming_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.upcoming_table)
        self.upcoming_box.setLayout(layout)

    def _init_standings_box(self) -> None:
        layout: QVBoxLayout = QVBoxLayout()

        self.tabs: QTabWidget = QTabWidget()

        # Standings tab
        self.standings_tab: QWidget = QWidget()
        standings_layout: QVBoxLayout = QVBoxLayout()

        self.standings_table: QTableWidget = QTableWidget(0, 3)
        self.standings_table.setHorizontalHeaderLabels(
            ["Name", "Score", "Games"]
        )
        self.standings_table.horizontalHeader().setStretchLastSection(True)

        standings_layout.addWidget(self.standings_table)
        self.standings_tab.setLayout(standings_layout)

        # History tab
        self.history_tab: QWidget = QWidget()
        history_layout: QVBoxLayout = QVBoxLayout()

        self.history_table: QTableWidget = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(
            ["Round", "Table", "White", "Black", "Result"]
        )
        self.history_table.horizontalHeader().setStretchLastSection(True)

        history_layout.addWidget(self.history_table)
        self.history_tab.setLayout(history_layout)

        # Add tabs
        self.tabs.addTab(self.standings_tab, "Standings")
        self.tabs.addTab(self.history_tab, "History")

        layout.addWidget(self.tabs)
        self.standings_box.setLayout(layout)

    # ----------------------------
    # Actions
    # ----------------------------

    def _remove_player(self) -> None:
        selected_items = self.player_list.selectedItems()
        if not selected_items:
            return

        # Elo is displayed with the name so split it.
        name = selected_items[0].text().split(' - ')[0]

        # Check if the player is in an active game
        active_games = [
            g for g in self.tournament.active_games
            if g.white == name or g.black == name
        ]
        if active_games:
            self._show_error(
                f"Cannot remove {name}: they are still playing in the current round."
            )
            return

        reply = QMessageBox.question(
            self,
            "Remove Player",
            f"Are you sure you want to remove '{name}' from the tournament?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self.tournament.remove_player(name)
        except ValueError as exc:
            self._show_error(str(exc))
            return

        # Remove from UI list
        row = self.player_list.row(selected_items[0])
        self.player_list.takeItem(row)

        # Refresh all tables
        self._refresh_all()

    def _update_remove_button_state(self) -> None:
        """Enable remove button only if selected player has no active game."""
        selected_items = self.player_list.selectedItems()
        if not selected_items:
            self.remove_player_button.setEnabled(False)
            return

        name = selected_items[0].text()
        active_games = [
            g for g in self.tournament.active_games
            if g.white == name or g.black == name
        ]

        self.remove_player_button.setEnabled(len(active_games) == 0)

    def _save_tournament(self) -> None:
        path: str = "saves/tournament.json"

        try:
            TournamentStorage.save_tournament(self.tournament, path)
            QMessageBox.information(self, "Saved", f"Saved to {path}")
        except Exception as exc:
            self._show_error(str(exc))

    def _load_tournament(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Tournament",
            "",
            "Tournament JSON (*.json)",
        )

        if not path:
            return

        try:
            self.tournament = TournamentStorage.load_tournament(path)
            self._set_running_layout()
            self.start_button.setEnabled(False)
            self.next_round_button.setEnabled(True)
            self.end_button.setEnabled(True)
            self.board_spin.setEnabled(False)
            self._refresh_all()

            QMessageBox.information(
                self,
                "Tournament Loaded",
                "Tournament successfully restored.",
            )

        except Exception as exc:
            self._show_error(f"Failed to load tournament:\n{exc}")

    def _export_csv(self) -> None:
        path: str = "exports/games.csv"

        try:
            TournamentStorage.export_games_csv(self.tournament, path)
            QMessageBox.information(self, "Exported", f"Exported to {path}")
        except Exception as exc:
            self._show_error(str(exc))

    def _add_player(self) -> None:
        name: str = self.player_input.text().strip()

        if not name:
            return

        try:
            self.tournament.add_player(name)
        except ValueError as exc:
            self._show_error(str(exc))
            return

        self.player_list.addItem(name)
        self.player_input.clear()
        self._refresh_player_list()

    def _start_tournament(self) -> None:
        try:
            self.tournament.set_board_limit(self.board_spin.value())
            self.tournament.start()
        except ValueError as exc:
            self._show_error(str(exc))
            return

        # switch UI layout
        self._set_running_layout()

        # disable setup controls
        self.load_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.board_spin.setEnabled(False)

        # enable tournament controls
        self.next_round_button.setEnabled(True)
        self.end_button.setEnabled(True)

        self._refresh_all()

    def _next_round(self) -> None:
        if not self.tournament.is_round_finished():
            self._show_error("Finish all games in this round first")
            return

        try:
            self.tournament.start_next_round()
        except ValueError as exc:
            self._show_error(str(exc))
            return

        self._refresh_all()

    def _submit_result(self, game_index: int, result: str) -> None:
        game: Game = self.tournament.active_games[game_index]

        message: str = (
            f"Confirm result?\n\n"
            f"Table {game.table}: {game.white} vs {game.black}\n"
            f"Result: {result}"
        )

        reply: QMessageBox.StandardButton = QMessageBox.question(
            self,
            "Confirm Result",
            message,
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self.tournament.submit_result(game_index, result)
        except ValueError as exc:
            self._show_error(str(exc))
            return

        self._refresh_all()

        if (
            not self.tournament.active_games
            and not self.tournament.pairing_queue
        ):
            timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
            round_number: int = self.tournament.round_number

            json_path: str = (
                f"autosaves/round_{round_number}_{timestamp}.json"
            )

            csv_path: str = (
                f"autosaves/round_{round_number}_{timestamp}.csv"
            )

            TournamentStorage.save_tournament(
                self.tournament,
                json_path,
            )

            TournamentStorage.export_games_csv(
                self.tournament,
                csv_path,
            )

    def _end_tournament(self) -> None:
        reply = QMessageBox.question(
            self,
            "End Tournament",
            "Are you sure you want to end the tournament?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        TournamentStorage.save_tournament(
            self.tournament,
            f"autosaves/final_{timestamp}.json",
        )

        TournamentStorage.export_games_csv(
            self.tournament,
            f"autosaves/final_{timestamp}.csv",
        )

        QMessageBox.information(self, "Tournament Ended", "Results saved.")

    # ----------------------------
    # Refresh
    # ----------------------------

    def _refresh_all(self) -> None:
        self._update_round_label()
        self._refresh_games()
        self._refresh_upcoming()
        self._refresh_standings()
        self._refresh_history()
        self._refresh_player_list()

    def _refresh_player_list(self) -> None:
        """Refresh the QListWidget of players from the tournament, showing Elo."""
        self.player_list.clear()
        for player in self.tournament.players.values():
            elo = int(self.tournament.elo_manager.get_elo(player.name))
            display_text = f"{player.name} - {elo}"
            self.player_list.addItem(display_text)

    def _refresh_history(self) -> None:
        history: List[Game] = self.tournament.history

        self.history_table.setRowCount(len(history))

        for row, game in enumerate(history):
            self.history_table.setItem(
                row, 0, QTableWidgetItem(str(game.round_number))
            )
            self.history_table.setItem(
                row, 1, QTableWidgetItem(str(game.table))
            )
            self.history_table.setItem(row, 2, QTableWidgetItem(game.white))
            self.history_table.setItem(row, 3, QTableWidgetItem(game.black))
            self.history_table.setItem(row, 4, QTableWidgetItem(game.result or ""))

        self.history_table.resizeColumnsToContents()

    def _refresh_games(self) -> None:
        games: List[Game] = self.tournament.active_games

        self.games_table.setRowCount(len(games))

        for row, game in enumerate(games):
            self.games_table.setItem(
                row, 0, QTableWidgetItem(str(game.table))
            )
            self.games_table.setItem(row, 1, QTableWidgetItem(game.white))
            self.games_table.setItem(row, 2, QTableWidgetItem(game.black))
            self.games_table.setItem(
                row, 3, QTableWidgetItem(game.result or "")
            )
            self.games_table.setCellWidget(
                row, 4, self._create_result_buttons(row)
            )

        self.games_table.resizeColumnsToContents()

    def _refresh_upcoming(self) -> None:
        queue = self.tournament.pairing_queue

        self.upcoming_table.setRowCount(len(queue))

        for row, (white, black) in enumerate(queue):
            self.upcoming_table.setItem(row, 0, QTableWidgetItem(white))
            self.upcoming_table.setItem(row, 1, QTableWidgetItem(black))
            self.upcoming_table.setItem(row, 2, QTableWidgetItem("Waiting"))

        self.upcoming_table.resizeColumnsToContents()

    def _refresh_standings(self) -> None:
        players: List[Player] = self.tournament.standings()

        self.standings_table.setRowCount(len(players))

        for row, player in enumerate(players):
            self.standings_table.setItem(row, 0, QTableWidgetItem(player.name))
            self.standings_table.setItem(
                row, 1, QTableWidgetItem(f"{player.score:.1f}")
            )
            self.standings_table.setItem(
                row, 2, QTableWidgetItem(str(player.games_played))
            )

        self.standings_table.resizeColumnsToContents()

    def _update_round_label(self) -> None:
        self.round_label.setText(f"Round: {self.tournament.round_number}")

    # ----------------------------
    # Helpers
    # ----------------------------

    def _create_result_buttons(self, game_index: int) -> QWidget:
        widget: QWidget = QWidget()
        layout: QHBoxLayout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        white_btn: QPushButton = QPushButton("1-0")
        draw_btn: QPushButton = QPushButton("½-½")
        black_btn: QPushButton = QPushButton("0-1")

        white_btn.clicked.connect(
            lambda: self._submit_result(game_index, "1-0")
        )
        draw_btn.clicked.connect(
            lambda: self._submit_result(game_index, "0.5-0.5")
        )
        black_btn.clicked.connect(
            lambda: self._submit_result(game_index, "0-1")
        )

        layout.addWidget(white_btn)
        layout.addWidget(draw_btn)
        layout.addWidget(black_btn)

        widget.setLayout(layout)
        return widget

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)


def main() -> None:
    app: QApplication = QApplication(sys.argv)

    window: MainWindow = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
