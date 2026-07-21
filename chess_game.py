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
BOTTOM_PANEL = 120
WINDOW_WIDTH = BOARD_SIZE * CELL_SIZE
WINDOW_HEIGHT = BOARD_SIZE * CELL_SIZE + BOTTOM_PANEL

LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
HIGHLIGHT = (186, 202, 68)
SELECT_HIGHLIGHT = (246, 246, 105)
INFO_BG = (100, 100, 100)
INFO_TEXT = (255, 255, 255)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

WHITE_PIECE_FILL = (250, 248, 240)
WHITE_PIECE_OUTLINE = (40, 40, 40)
BLACK_PIECE_FILL = (30, 30, 35)
BLACK_PIECE_OUTLINE = (215, 215, 215)

pygame.font.init()
info_font = pygame.font.SysFont("Arial", 30)


def _piece_points(rect, coords):
    s = rect.width
    cx = rect.centerx
    base_y = rect.bottom - s * 0.06
    return [(cx + dx * s, base_y - dy * s) for dx, dy in coords]


def _draw_poly(screen, points, fill, outline, width):
    pygame.draw.polygon(screen, fill, points)
    pygame.draw.polygon(screen, outline, points, width)


def _draw_circle(screen, center, radius, fill, outline, width):
    pygame.draw.circle(screen, fill, center, radius)
    pygame.draw.circle(screen, outline, center, radius, width)


def draw_chess_piece(screen, piece, rect):
    s = rect.width
    outline_w = max(2, int(s * 0.025))
    fill = WHITE_PIECE_FILL if piece.color == chess.WHITE else BLACK_PIECE_FILL
    outline = WHITE_PIECE_OUTLINE if piece.color == chess.WHITE else BLACK_PIECE_OUTLINE
    pts = lambda coords: _piece_points(rect, coords)

    base = pts([(-0.26, 0.0), (0.26, 0.0), (0.23, 0.07), (-0.23, 0.07)])
    _draw_poly(screen, base, fill, outline, outline_w)
    belt = pts([(-0.20, 0.10), (0.20, 0.10)])
    pygame.draw.line(screen, outline, belt[0], belt[1], max(1, outline_w - 1))

    if piece.piece_type == chess.PAWN:
        body = pts([(-0.13, 0.07), (0.13, 0.07), (0.09, 0.30), (-0.09, 0.30)])
        _draw_poly(screen, body, fill, outline, outline_w)
        collar = pts([(-0.11, 0.30), (0.11, 0.30), (0.11, 0.34), (-0.11, 0.34)])
        _draw_poly(screen, collar, fill, outline, outline_w)
        head = pts([(0, 0.47)])[0]
        _draw_circle(screen, head, s * 0.145, fill, outline, outline_w)

    elif piece.piece_type == chess.ROOK:
        body = pts([(-0.19, 0.07), (0.19, 0.07), (0.19, 0.50), (-0.19, 0.50)])
        _draw_poly(screen, body, fill, outline, outline_w)
        seam_a = pts([(-0.07, 0.11), (-0.07, 0.46)])
        seam_b = pts([(0.07, 0.11), (0.07, 0.46)])
        pygame.draw.line(screen, outline, seam_a[0], seam_a[1], max(1, outline_w - 1))
        pygame.draw.line(screen, outline, seam_b[0], seam_b[1], max(1, outline_w - 1))
        for mx in (-0.19, -0.05, 0.09):
            merlon = pts([(mx, 0.50), (mx + 0.10, 0.50), (mx + 0.10, 0.66), (mx, 0.66)])
            _draw_poly(screen, merlon, fill, outline, outline_w)

    elif piece.piece_type == chess.KNIGHT:
        head = pts([
            (0.14, 0.07), (0.12, 0.22), (0.22, 0.27), (0.31, 0.34), (0.23, 0.39),
            (0.29, 0.45), (0.18, 0.52), (0.23, 0.60), (0.11, 0.55), (-0.05, 0.47),
            (-0.19, 0.32), (-0.19, 0.07),
        ])
        _draw_poly(screen, head, fill, outline, outline_w)
        eye = pts([(0.16, 0.43)])[0]
        pygame.draw.circle(screen, outline, eye, max(2, int(s * 0.022)))
        nostril = pts([(0.27, 0.36)])[0]
        pygame.draw.circle(screen, outline, nostril, max(2, int(s * 0.016)))

    elif piece.piece_type == chess.BISHOP:
        body = pts([(-0.16, 0.07), (0.16, 0.07), (0.09, 0.38), (-0.09, 0.38)])
        _draw_poly(screen, body, fill, outline, outline_w)
        collar = pts([(-0.12, 0.38), (0.12, 0.38), (0.12, 0.42), (-0.12, 0.42)])
        _draw_poly(screen, collar, fill, outline, outline_w)
        head = pts([(0, 0.52)])[0]
        _draw_circle(screen, head, s * 0.135, fill, outline, outline_w)
        slit_a = pts([(-0.035, 0.58)])[0]
        slit_b = pts([(0.035, 0.67)])[0]
        pygame.draw.line(screen, outline, slit_a, slit_b, outline_w)
        top = pts([(0, 0.70)])[0]
        _draw_circle(screen, top, s * 0.04, fill, outline, outline_w)

    elif piece.piece_type == chess.QUEEN:
        body = pts([(-0.17, 0.07), (0.17, 0.07), (0.11, 0.38), (-0.11, 0.38)])
        _draw_poly(screen, body, fill, outline, outline_w)
        collar = pts([(-0.14, 0.38), (0.14, 0.38), (0.14, 0.43), (-0.14, 0.43)])
        _draw_poly(screen, collar, fill, outline, outline_w)
        crown = pts([
            (-0.20, 0.43), (-0.20, 0.50), (-0.13, 0.43), (-0.09, 0.54),
            (-0.045, 0.43), (0, 0.58), (0.045, 0.43), (0.09, 0.54),
            (0.13, 0.43), (0.20, 0.50), (0.20, 0.43),
        ])
        _draw_poly(screen, crown, fill, outline, outline_w)
        tips = (
            (-0.20, 0.50, 0.028), (-0.09, 0.54, 0.032), (0, 0.58, 0.038),
            (0.09, 0.54, 0.032), (0.20, 0.50, 0.028),
        )
        for bx, by, r in tips:
            ball = pts([(bx, by)])[0]
            _draw_circle(screen, ball, s * r, fill, outline, outline_w)

    else:
        body = pts([(-0.18, 0.07), (0.18, 0.07), (0.12, 0.42), (-0.12, 0.42)])
        _draw_poly(screen, body, fill, outline, outline_w)
        collar = pts([(-0.15, 0.42), (0.15, 0.42), (0.15, 0.48), (-0.15, 0.48)])
        _draw_poly(screen, collar, fill, outline, outline_w)
        band = pts([(-0.13, 0.48), (0.13, 0.48), (0.13, 0.53), (-0.13, 0.53)])
        _draw_poly(screen, band, fill, outline, outline_w)
        cross_v = pts([(-0.03, 0.53), (0.03, 0.53), (0.03, 0.72), (-0.03, 0.72)])
        _draw_poly(screen, cross_v, fill, outline, outline_w)
        cross_h = pts([(-0.085, 0.60), (0.085, 0.60), (0.085, 0.655), (-0.085, 0.655)])
        _draw_poly(screen, cross_h, fill, outline, outline_w)

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
        self.ai_move_history = []
        self.max_history = 4

    def compute_ai_depth(self):
        depth = int((self.player_rating - 200) / 400) + 1
        depth = max(1, min(5, depth))
        return depth

    def draw_board(self, screen):
        for rank in range(BOARD_SIZE):
            for file in range(BOARD_SIZE):
                color = LIGHT_SQUARE if (rank + file) % 2 == 0 else DARK_SQUARE
                rect = pygame.Rect(file * CELL_SIZE, rank * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(screen, color, rect)

        if self.selected_square is not None:
            sel_file = chess.square_file(self.selected_square)
            sel_rank = 7 - chess.square_rank(self.selected_square)
            rect = pygame.Rect(sel_file * CELL_SIZE, sel_rank * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, SELECT_HIGHLIGHT, rect)
            for move in self.legal_moves:
                dest = move.to_square
                d_file = chess.square_file(dest)
                d_rank = 7 - chess.square_rank(dest)
                dest_rect = pygame.Rect(d_file * CELL_SIZE, d_rank * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                s = pygame.Surface((CELL_SIZE, CELL_SIZE))
                s.set_alpha(100)
                s.fill(HIGHLIGHT)
                screen.blit(s, dest_rect.topleft)

        for square in chess.SQUARES:
            if self.animating_move is not None:
                anim_move, anim_piece, _, _ = self.animating_move
                if square == anim_move.to_square:
                    continue

            piece = self.board.piece_at(square)
            if piece:
                file = chess.square_file(square)
                rank = 7 - chess.square_rank(square)
                rect = pygame.Rect(file * CELL_SIZE, rank * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                draw_chess_piece(screen, piece, rect)

        if self.animating_move is not None:
            move, piece, start_pos, end_pos = self.animating_move
            current_x = start_pos[0] + (end_pos[0] - start_pos[0]) * self.animation_progress
            current_y = start_pos[1] + (end_pos[1] - start_pos[1]) * self.animation_progress
            rect = pygame.Rect(0, 0, CELL_SIZE, CELL_SIZE)
            rect.center = (current_x, current_y)
            draw_chess_piece(screen, piece, rect)

        panel_rect = pygame.Rect(0, BOARD_SIZE * CELL_SIZE, WINDOW_WIDTH, BOTTOM_PANEL)
        pygame.draw.rect(screen, INFO_BG, panel_rect)

        turn_str = "Your Turn (White)" if self.board.turn == chess.WHITE else "AI Turn (Black)"
        turn_text = info_font.render(turn_str, True, INFO_TEXT)
        screen.blit(turn_text, (20, BOARD_SIZE * CELL_SIZE + 10))

        rating_text = info_font.render(f"Player: {int(self.player_rating)}   AI: {int(self.ai_rating)}", True, INFO_TEXT)
        screen.blit(rating_text, (20, BOARD_SIZE * CELL_SIZE + 40))

        ai_text = info_font.render(f"AI Depth: {self.ai_depth}", True, INFO_TEXT)
        screen.blit(ai_text, (20, BOARD_SIZE * CELL_SIZE + 70))

        if self.game_over:
            result_text = info_font.render(f"Game Over: {self.board.result()}", True, INFO_TEXT)
            screen.blit(result_text, (300, BOARD_SIZE * CELL_SIZE + 10))
            inst_text = info_font.render("Press R to restart OR click [Replay] below", True, INFO_TEXT)
            screen.blit(inst_text, (300, BOARD_SIZE * CELL_SIZE + 40))

            self.replay_button_rect = pygame.Rect(WINDOW_WIDTH - 150, BOARD_SIZE * CELL_SIZE + 40, 130, 40)
            pygame.draw.rect(screen, GREEN, self.replay_button_rect)
            replay_text = info_font.render("Replay", True, BLACK)
            text_rect = replay_text.get_rect(center=self.replay_button_rect.center)
            screen.blit(replay_text, text_rect)

    def get_square_from_pos(self, pos):
        x, y = pos
        if x < 0 or x >= WINDOW_WIDTH or y < 0 or y >= BOARD_SIZE * CELL_SIZE:
            return None
        file = x // CELL_SIZE
        rank = y // CELL_SIZE
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
        start_file = chess.square_file(move.from_square)
        start_rank = 7 - chess.square_rank(move.from_square)
        end_file = chess.square_file(move.to_square)
        end_rank = 7 - chess.square_rank(move.to_square)
        start_x = start_file * CELL_SIZE + CELL_SIZE // 2
        start_y = start_rank * CELL_SIZE + CELL_SIZE // 2
        end_x = end_file * CELL_SIZE + CELL_SIZE // 2
        end_y = end_rank * CELL_SIZE + CELL_SIZE // 2

        moving_piece = self.board.piece_at(move.from_square)
        self.board.push(move)
        self.move_history.append(move)

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
        start_file = chess.square_file(move.from_square)
        start_rank = 7 - chess.square_rank(move.from_square)
        end_file = chess.square_file(move.to_square)
        end_rank = 7 - chess.square_rank(move.to_square)
        start_x = start_file * CELL_SIZE + CELL_SIZE // 2
        start_y = start_rank * CELL_SIZE + CELL_SIZE // 2
        end_x = end_file * CELL_SIZE + CELL_SIZE // 2
        end_y = end_rank * CELL_SIZE + CELL_SIZE // 2

        moving_piece = self.board.piece_at(move.from_square)
        self.board.push(move)

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

def choose_start_mode(screen, clock, saved):
    title_font = pygame.font.Font(None, 64)
    option_font = pygame.font.Font(None, 36)
    hint_font = pygame.font.Font(None, 24)

    continue_label = f"Continue (Rating: {int(saved[0])})" if saved else "Continue (Rating: 1000)"
    continue_rect = pygame.Rect(WINDOW_WIDTH // 2 - 220, 340, 440, 60)
    recalibrate_rect = pygame.Rect(WINDOW_WIDTH // 2 - 220, 430, 440, 60)

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

        screen.fill(BLACK)
        title = title_font.render("AI Chess", True, (200, 0, 0))
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 200)))

        for rect, label in ((continue_rect, continue_label), (recalibrate_rect, "Recalibrate (Fresh Baseline Game)")):
            pygame.draw.rect(screen, INFO_BG, rect)
            text = option_font.render(label, True, WHITE)
            screen.blit(text, text.get_rect(center=rect.center))

        hint = hint_font.render(
            "Recalibrate resets your rating to 1000 and re-ranks you from this game.", True, (180, 180, 180)
        )
        screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, 500)))

        pygame.display.update()


def main():
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("AI Chess – Rated & Replay Mode")
    clock = pygame.time.Clock()

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
