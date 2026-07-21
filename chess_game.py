import pygame
import sys
import chess
import math
import random
import time
import os
import json

pygame.init()

APP_SUPPORT_DIR = os.path.expanduser("~/Library/Application Support/AI Chess Elo")
RATINGS_FILE = os.path.join(APP_SUPPORT_DIR, "ratings.json")


def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def load_saved_ratings():
    if not os.path.exists(RATINGS_FILE):
        return None
    try:
        with open(RATINGS_FILE, "r") as f:
            data = json.load(f)
        return data["player_rating"], data["ai_rating"]
    except (OSError, json.JSONDecodeError, KeyError):
        return None


def save_ratings(player_rating, ai_rating):
    os.makedirs(APP_SUPPORT_DIR, exist_ok=True)
    with open(RATINGS_FILE, "w") as f:
        json.dump({"player_rating": player_rating, "ai_rating": ai_rating}, f)

BOARD_SIZE = 8
CELL_SIZE = 100
BOARD_PIXELS = BOARD_SIZE * CELL_SIZE
BOARD_MARGIN = 30
FILE_LABEL_H = 28
BOTTOM_PANEL = 150
WINDOW_WIDTH = BOARD_PIXELS + 2 * BOARD_MARGIN
WINDOW_HEIGHT = BOARD_MARGIN + BOARD_PIXELS + FILE_LABEL_H + BOTTOM_PANEL
BOARD_ORIGIN_X = BOARD_MARGIN
BOARD_ORIGIN_Y = BOARD_MARGIN

LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
SELECT_HIGHLIGHT = (246, 216, 90, 130)
LAST_MOVE_HIGHLIGHT = (186, 202, 68, 110)
MOVE_DOT_COLOR = (40, 90, 40, 160)
CAPTURE_RING_COLOR = (180, 50, 50, 170)
FRAME_COLOR = (54, 36, 24)
FRAME_EDGE = (88, 60, 38)
LABEL_COLOR = (222, 202, 172)
PANEL_BG = (30, 30, 34)
PANEL_ACCENT = (90, 66, 40)
INFO_TEXT = (232, 232, 236)
MUTED_TEXT = (165, 165, 172)
GREEN = (86, 170, 90)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

pygame.font.init()
info_font = pygame.font.SysFont("Arial", 28)
info_font_bold = pygame.font.SysFont("Arial", 28, bold=True)
label_font = pygame.font.SysFont("Arial", 16, bold=True)

PIECE_IMAGES = {}


def init_piece_images():
    mapping = {
        chess.KING: "K", chess.QUEEN: "Q", chess.ROOK: "R",
        chess.BISHOP: "B", chess.KNIGHT: "N", chess.PAWN: "P",
    }
    size = int(CELL_SIZE * 0.85)
    for piece_type, letter in mapping.items():
        for color, prefix in ((chess.WHITE, "w"), (chess.BLACK, "b")):
            path = resource_path("assets", "pieces", f"{prefix}{letter}.png")
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, (size, size))
            PIECE_IMAGES[(color, piece_type)] = img


def draw_chess_piece(screen, piece, rect):
    shadow_w = int(rect.width * 0.6)
    shadow_h = int(rect.height * 0.16)
    shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 70), shadow_surf.get_rect())
    shadow_rect = shadow_surf.get_rect(center=(rect.centerx, rect.bottom - int(rect.height * 0.09)))
    screen.blit(shadow_surf, shadow_rect.topleft)

    img = PIECE_IMAGES[(piece.color, piece.piece_type)]
    img_rect = img.get_rect(center=rect.center)
    screen.blit(img, img_rect)


def _alpha_fill(screen, rect, color):
    surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    surf.fill(color)
    screen.blit(surf, rect.topleft)


class ChessGame:
    def __init__(self, player_rating=1000, ai_rating=1000, calibration_mode=True):
        self.board = chess.Board()
        self.selected_square = None
        self.legal_moves = []
        self.player_move_count = 0
        self.calibration_mode = calibration_mode
        self.player_rating = player_rating
        self.ai_rating = ai_rating
        self.ai_depth = self.compute_ai_depth()
        self.last_move_time = time.time()
        self.game_over = False
        self.game_result = None
        self.animating_move = None
        self.animation_progress = 0
        self.move_history = []
        self.last_game_moves = []
        self.ratings_updated = False
        self.last_ai_piece = None
        self.last_move = None
        self.ai_move_history = []
        self.max_history = 4

    def compute_ai_depth(self):
        depth = int((self.player_rating - 200) / 400) + 1
        depth = max(1, min(5, depth))
        return depth

    def square_rect(self, square):
        file = chess.square_file(square)
        rank = 7 - chess.square_rank(square)
        return pygame.Rect(
            BOARD_ORIGIN_X + file * CELL_SIZE,
            BOARD_ORIGIN_Y + rank * CELL_SIZE,
            CELL_SIZE, CELL_SIZE,
        )

    def draw_board(self, screen):
        frame_rect = pygame.Rect(0, 0, WINDOW_WIDTH, BOARD_ORIGIN_Y + BOARD_PIXELS + FILE_LABEL_H)
        pygame.draw.rect(screen, FRAME_COLOR, frame_rect)
        pygame.draw.rect(
            screen, FRAME_EDGE,
            pygame.Rect(BOARD_ORIGIN_X - 3, BOARD_ORIGIN_Y - 3, BOARD_PIXELS + 6, BOARD_PIXELS + 6),
            3,
        )

        for rank in range(BOARD_SIZE):
            for file in range(BOARD_SIZE):
                color = LIGHT_SQUARE if (rank + file) % 2 == 0 else DARK_SQUARE
                rect = pygame.Rect(BOARD_ORIGIN_X + file * CELL_SIZE, BOARD_ORIGIN_Y + rank * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(screen, color, rect)

        if self.last_move is not None:
            _alpha_fill(screen, self.square_rect(self.last_move.from_square), LAST_MOVE_HIGHLIGHT)
            _alpha_fill(screen, self.square_rect(self.last_move.to_square), LAST_MOVE_HIGHLIGHT)

        if self.selected_square is not None:
            _alpha_fill(screen, self.square_rect(self.selected_square), SELECT_HIGHLIGHT)
            for move in self.legal_moves:
                dest_rect = self.square_rect(move.to_square)
                indicator = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                if self.board.is_capture(move):
                    pygame.draw.circle(
                        indicator, CAPTURE_RING_COLOR,
                        (CELL_SIZE // 2, CELL_SIZE // 2), CELL_SIZE // 2 - 6, 6,
                    )
                else:
                    pygame.draw.circle(
                        indicator, MOVE_DOT_COLOR,
                        (CELL_SIZE // 2, CELL_SIZE // 2), CELL_SIZE // 7,
                    )
                screen.blit(indicator, dest_rect.topleft)

        for square in chess.SQUARES:
            if self.animating_move is not None:
                anim_move, anim_piece, _, _ = self.animating_move
                if square == anim_move.to_square:
                    continue

            piece = self.board.piece_at(square)
            if piece:
                draw_chess_piece(screen, piece, self.square_rect(square))

        if self.animating_move is not None:
            move, piece, start_pos, end_pos = self.animating_move
            current_x = start_pos[0] + (end_pos[0] - start_pos[0]) * self.animation_progress
            current_y = start_pos[1] + (end_pos[1] - start_pos[1]) * self.animation_progress
            rect = pygame.Rect(0, 0, CELL_SIZE, CELL_SIZE)
            rect.center = (current_x, current_y)
            draw_chess_piece(screen, piece, rect)

        files = "abcdefgh"
        for file in range(BOARD_SIZE):
            label = label_font.render(files[file], True, LABEL_COLOR)
            x = BOARD_ORIGIN_X + file * CELL_SIZE + CELL_SIZE // 2
            y = BOARD_ORIGIN_Y + BOARD_PIXELS + FILE_LABEL_H // 2
            screen.blit(label, label.get_rect(center=(x, y)))
        for rank in range(BOARD_SIZE):
            label = label_font.render(str(8 - rank), True, LABEL_COLOR)
            x = BOARD_ORIGIN_X // 2
            y = BOARD_ORIGIN_Y + rank * CELL_SIZE + CELL_SIZE // 2
            screen.blit(label, label.get_rect(center=(x, y)))

        panel_top = BOARD_ORIGIN_Y + BOARD_PIXELS + FILE_LABEL_H
        panel_rect = pygame.Rect(0, panel_top, WINDOW_WIDTH, BOTTOM_PANEL)
        pygame.draw.rect(screen, PANEL_BG, panel_rect)
        pygame.draw.rect(screen, PANEL_ACCENT, pygame.Rect(0, panel_top, WINDOW_WIDTH, 3))

        turn_str = "Your Turn (White)" if self.board.turn == chess.WHITE else "AI Turn (Black)"
        turn_text = info_font_bold.render(turn_str, True, INFO_TEXT)
        screen.blit(turn_text, (24, panel_top + 14))

        rating_text = info_font.render(f"Player: {int(self.player_rating)}   AI: {int(self.ai_rating)}", True, MUTED_TEXT)
        screen.blit(rating_text, (24, panel_top + 48))

        ai_text = info_font.render(f"AI Depth: {self.ai_depth}", True, MUTED_TEXT)
        screen.blit(ai_text, (24, panel_top + 78))

        if self.game_over:
            result_text = info_font_bold.render(f"Game Over: {self.board.result()}  —  Press R to restart", True, INFO_TEXT)
            screen.blit(result_text, (24, panel_top + 112))

            self.replay_button_rect = pygame.Rect(WINDOW_WIDTH - 160, panel_top + (BOTTOM_PANEL - 44) // 2, 136, 44)
            pygame.draw.rect(screen, GREEN, self.replay_button_rect, border_radius=8)
            replay_text = info_font_bold.render("Replay", True, BLACK)
            text_rect = replay_text.get_rect(center=self.replay_button_rect.center)
            screen.blit(replay_text, text_rect)

    def get_square_from_pos(self, pos):
        x, y = pos
        bx = x - BOARD_ORIGIN_X
        by = y - BOARD_ORIGIN_Y
        if bx < 0 or bx >= BOARD_PIXELS or by < 0 or by >= BOARD_PIXELS:
            return None
        file = bx // CELL_SIZE
        rank = by // CELL_SIZE
        chess_rank = 7 - rank
        square = chess.square(file, chess_rank)
        return square

    def handle_click(self, pos, screen, clock):
        if self.game_over:
            return
        if self.board.turn != chess.WHITE:
            return

        square = self.get_square_from_pos(pos)
        if square is None:
            return

        piece = self.board.piece_at(square)
        if self.selected_square is None:
            if piece is not None and piece.color == chess.WHITE:
                self.selected_square = square
                self.legal_moves = [move for move in self.board.legal_moves if move.from_square == square]
        else:
            if square == self.selected_square:
                self.selected_square = None
                self.legal_moves = []
                return
            for move in self.legal_moves:
                if move.to_square == square:
                    self.animate_move(move, screen, clock)
                    self.player_move_count += 1
                    self.selected_square = None
                    self.legal_moves = []
                    if self.board.is_game_over():
                        self.game_over = True
                        self.game_result = self.board.result()
                        self.last_game_moves = self.move_history.copy()
                    pygame.display.update()
                    pygame.time.delay(200)
                    if not self.game_over:
                        self.ai_move(screen, clock)
                    return
            if piece is not None and piece.color == chess.WHITE:
                self.selected_square = square
                self.legal_moves = [move for move in self.board.legal_moves if move.from_square == square]
            else:
                self.selected_square = None
                self.legal_moves = []

    def animate_move(self, move, screen, clock):
        start_rect = self.square_rect(move.from_square)
        end_rect = self.square_rect(move.to_square)
        start_x, start_y = start_rect.center
        end_x, end_y = end_rect.center

        moving_piece = self.board.piece_at(move.from_square)
        self.board.push(move)
        self.move_history.append(move)
        self.last_move = move

        self.animating_move = (move, moving_piece, (start_x, start_y), (end_x, end_y))
        frames = 15
        for frame in range(frames + 1):
            self.animation_progress = frame / frames
            screen.fill(BLACK)
            self.draw_board(screen)
            pygame.display.update()
            clock.tick(60)
        self.animating_move = None
        self.animation_progress = 0

    def animate_move_replay(self, move, screen, clock):
        start_rect = self.square_rect(move.from_square)
        end_rect = self.square_rect(move.to_square)
        start_x, start_y = start_rect.center
        end_x, end_y = end_rect.center

        moving_piece = self.board.piece_at(move.from_square)
        self.board.push(move)
        self.last_move = move

        self.animating_move = (move, moving_piece, (start_x, start_y), (end_x, end_y))
        frames = 15
        for frame in range(frames + 1):
            self.animation_progress = frame / frames
            screen.fill(BLACK)
            self.draw_board(screen)
            pygame.display.update()
            clock.tick(60)
        self.animating_move = None
        self.animation_progress = 0

    def evaluate_board(self, board):
        if board.is_checkmate():
            return -99999 if board.turn == chess.WHITE else 99999
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        eval = 0
        piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20000
        }
        for piece_type, value in piece_values.items():
            eval += len(board.pieces(piece_type, chess.WHITE)) * value
            eval -= len(board.pieces(piece_type, chess.BLACK)) * value

        if board.is_check():
            if board.turn == chess.BLACK:
                eval += 30
            else:
                eval -= 30
        return eval

    def order_moves(self, board, moves):
        move_scores = []
        for move in moves:
            score = 0
            if board.is_capture(move):
                score += 100
            board.push(move)
            if board.is_check():
                score += 50
            board.pop()

            if len(self.ai_move_history) >= 2:
                if move.from_square == self.ai_move_history[-1].to_square and \
                   move.to_square == self.ai_move_history[-1].from_square:
                    score -= 300

                if move.from_square == self.ai_move_history[-1].to_square:
                    score -= 150

                if len(self.ai_move_history) >= 4:
                    if move.from_square == self.ai_move_history[-3].to_square and \
                       move.to_square == self.ai_move_history[-3].from_square:
                        score -= 400

            move_scores.append((score, move))
        move_scores.sort(key=lambda x: x[0], reverse=True)
        return [m for score, m in move_scores]

    def minimax(self, board, depth, alpha, beta, maximizing):
        if depth == 0 or board.is_game_over():
            return None, self.evaluate_board(board)
        best_move = None
        if maximizing:
            max_eval = -math.inf
            moves = self.order_moves(board, list(board.legal_moves))
            for move in moves:
                board.push(move)
                current_eval = self.minimax(board, depth - 1, alpha, beta, False)[1]
                board.pop()
                if current_eval > max_eval:
                    max_eval = current_eval
                    best_move = move
                alpha = max(alpha, current_eval)
                if beta <= alpha:
                    break
            return best_move, max_eval
        else:
            min_eval = math.inf
            moves = self.order_moves(board, list(board.legal_moves))
            for move in moves:
                board.push(move)
                current_eval = self.minimax(board, depth - 1, alpha, beta, True)[1]
                board.pop()
                if current_eval < min_eval:
                    min_eval = current_eval
                    best_move = move
                beta = min(beta, current_eval)
                if beta <= alpha:
                    break
            return best_move, min_eval

    def ai_move(self, screen, clock):
        if self.board.is_game_over():
            self.game_over = True
            self.game_result = self.board.result()
            self.last_game_moves = self.move_history.copy()
            return

        for move in list(self.board.legal_moves):
            self.board.push(move)
            if self.board.is_checkmate():
                self.board.pop()
                self.animate_move(move, screen, clock)
                if self.board.is_game_over():
                    self.game_over = True
                    self.game_result = self.board.result()
                    self.last_game_moves = self.move_history.copy()
                return
            self.board.pop()

        pygame.time.delay(500)
        move, eval_score = self.minimax(self.board, self.ai_depth, -math.inf, math.inf, self.board.turn == chess.WHITE)
        if move is None:
            self.game_over = True
            self.game_result = self.board.result()
            self.last_game_moves = self.move_history.copy()
            return
        self.animate_move(move, screen, clock)
        self.ai_move_history.append(move)
        if len(self.ai_move_history) > self.max_history:
            self.ai_move_history.pop(0)
        self.last_ai_piece = move.from_square
        if self.board.is_game_over():
            self.game_over = True
            self.game_result = self.board.result()
            self.last_game_moves = self.move_history.copy()

    def update_ratings(self):
        result = self.board.result()
        if result == "1-0":
            score = 1
        elif result == "0-1":
            score = 0
        else:
            score = 0.5

        moves_made = len(self.move_history)
        pieces_moved = len(set(move.from_square for move in self.move_history if move.from_square != move.to_square))

        if result == "0-1":
            if moves_made < 10:
                K = 400
                if pieces_moved < 3:
                    K = 600
                elif pieces_moved < 5:
                    K = 500
            elif moves_made < 15:
                K = 300
            else:
                K = 128
        else:
            if moves_made < 4:
                K = 256
            elif moves_made < 8:
                K = 128
            else:
                K = 64

        expected = 1 / (1 + 10 ** ((self.ai_rating - self.player_rating) / 400))
        new_player_rating = self.player_rating + K * (score - expected)

        self.player_rating = new_player_rating
        self.ai_rating = self.player_rating

        self.ai_depth = self.compute_ai_depth()
        self.calibration_mode = False

    def replay_game(self, screen, clock):
        if not self.last_game_moves:
            return
        self.board.reset()
        self.last_move = None
        screen.fill(BLACK)
        self.draw_board(screen)
        pygame.display.update()
        pygame.time.delay(1000)
        for move in self.last_game_moves:
            self.animate_move_replay(move, screen, clock)
        pygame.time.delay(1000)
        self.board.reset()
        self.move_history = []
        self.selected_square = None
        self.legal_moves = []
        self.game_over = False
        self.game_result = None
        self.ratings_updated = False
        self.ai_move_history = []
        self.last_move = None

    def reset_game(self):
        self.board.reset()
        self.selected_square = None
        self.legal_moves = []
        self.player_move_count = 0
        self.game_over = False
        self.game_result = None
        self.animating_move = None
        self.animation_progress = 0
        self.move_history = []
        self.ratings_updated = False
        if not self.calibration_mode:
            self.ai_rating = self.player_rating
        self.ai_move_history = []
        self.last_move = None

def choose_start_mode(screen, clock, saved):
    title_font = pygame.font.Font(None, 68)
    option_font = pygame.font.Font(None, 36)
    hint_font = pygame.font.Font(None, 24)

    continue_label = f"Continue (Rating: {int(saved[0])})" if saved else "Continue (Rating: 1000)"
    continue_rect = pygame.Rect(WINDOW_WIDTH // 2 - 220, 360, 440, 60)
    recalibrate_rect = pygame.Rect(WINDOW_WIDTH // 2 - 220, 450, 440, 60)

    while True:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if continue_rect.collidepoint(event.pos):
                    return "continue"
                if recalibrate_rect.collidepoint(event.pos):
                    return "recalibrate"

        screen.fill(FRAME_COLOR)
        title = title_font.render("AI Chess Elo", True, (216, 178, 122))
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 210)))

        for rect, label in ((continue_rect, continue_label), (recalibrate_rect, "Recalibrate (Fresh Baseline Game)")):
            pygame.draw.rect(screen, PANEL_BG, rect, border_radius=10)
            pygame.draw.rect(screen, PANEL_ACCENT, rect, 2, border_radius=10)
            text = option_font.render(label, True, WHITE)
            screen.blit(text, text.get_rect(center=rect.center))

        hint = hint_font.render(
            "Recalibrate resets your rating to 1000 and re-ranks you from this game.", True, MUTED_TEXT
        )
        screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, 525)))

        pygame.display.update()


def main():
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("AI Chess – Rated & Replay Mode")
    clock = pygame.time.Clock()
    init_piece_images()

    saved = load_saved_ratings()
    mode = choose_start_mode(screen, clock, saved)
    if mode == "continue" and saved:
        game = ChessGame(player_rating=saved[0], ai_rating=saved[1], calibration_mode=False)
    else:
        game = ChessGame(player_rating=1000, ai_rating=1000, calibration_mode=True)

    running = True
    while running:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if game.game_over and hasattr(game, "replay_button_rect"):
                    if game.replay_button_rect.collidepoint(pygame.mouse.get_pos()):
                        game.replay_game(screen, clock)
                        continue
                if game.board.turn == chess.WHITE and not game.game_over:
                    game.handle_click(pygame.mouse.get_pos(), screen, clock)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game.reset_game()

        if game.game_over and not game.ratings_updated:
            game.update_ratings()
            game.ratings_updated = True
            save_ratings(game.player_rating, game.ai_rating)

        screen.fill(BLACK)
        game.draw_board(screen)
        pygame.display.update()

    pygame.quit()
    sys.exit()

def simulate_series():
    def simulate_game_series(initial_rating, outcome, n_games):
        game = ChessGame()
        game.player_rating = initial_rating
        game.ai_rating = initial_rating
        for i in range(n_games):
            original_result = game.board.result
            game.board.result = lambda: outcome
            game.update_ratings()
            game.board.result = original_result
        return game.player_rating, game.ai_rating

    n_games = 10
    player_bad, ai_bad = simulate_game_series(500, "0-1", n_games)
    player_ok, ai_ok = simulate_game_series(500, "1/2-1/2", n_games)
    player_great, ai_great = simulate_game_series(500, "1-0", n_games)

    print("Simulation results over", n_games, "games each (modified system):")
    print(f"Bad game series (player loses all): Player rating: {player_bad:.2f}, AI rating: {ai_bad:.2f}")
    print(f"Ok game series (all draws):       Player rating: {player_ok:.2f}, AI rating: {ai_ok:.2f}")
    print(f"Great game series (player wins all): Player rating: {player_great:.2f}, AI rating: {ai_great:.2f}")
    print("\nNote: In this system, 500 is average and the AI always matches the player's rating after the first game.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "simulate":
        simulate_series()
    else:
        main()
