import pygame
import sys
import chess
import chess.engine
import math
import random
import time
import os
import json
import shutil

pygame.init()

APP_SUPPORT_DIR = os.path.expanduser("~/Library/Application Support/AI Chess Elo")
RATINGS_FILE = os.path.join(APP_SUPPORT_DIR, "ratings.json")


def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def find_stockfish():
    bundled = resource_path("stockfish")
    if os.path.exists(bundled):
        return bundled
    return shutil.which("stockfish")


def load_saved_ratings():
    if not os.path.exists(RATINGS_FILE):
        return None
    try:
        with open(RATINGS_FILE, "r") as f:
            data = json.load(f)
        return data["player_rating"], data["ai_rating"], data.get("history", [])
    except (OSError, json.JSONDecodeError, KeyError):
        return None


def save_ratings(player_rating, ai_rating, history):
    os.makedirs(APP_SUPPORT_DIR, exist_ok=True)
    with open(RATINGS_FILE, "w") as f:
        json.dump({"player_rating": player_rating, "ai_rating": ai_rating, "history": history}, f)

BOARD_SIZE = 8
BASE_MARGIN_RATIO = 0.30
BASE_LABEL_RATIO = 0.28
BASE_PANEL_RATIO = 1.50

DEFAULT_WINDOW_WIDTH = int(100 * (BOARD_SIZE + 2 * BASE_MARGIN_RATIO))
DEFAULT_WINDOW_HEIGHT = int(100 * (BASE_MARGIN_RATIO + BOARD_SIZE + BASE_LABEL_RATIO + BASE_PANEL_RATIO))

CELL_SIZE = 100
BOARD_PIXELS = BOARD_SIZE * CELL_SIZE
BOARD_MARGIN = CELL_SIZE * BASE_MARGIN_RATIO
FILE_LABEL_H = CELL_SIZE * BASE_LABEL_RATIO
BOTTOM_PANEL = CELL_SIZE * BASE_PANEL_RATIO
WINDOW_WIDTH = DEFAULT_WINDOW_WIDTH
WINDOW_HEIGHT = DEFAULT_WINDOW_HEIGHT
BOARD_ORIGIN_X = BOARD_MARGIN
BOARD_ORIGIN_Y = BOARD_MARGIN
PANEL_TOP = BOARD_ORIGIN_Y + BOARD_PIXELS + FILE_LABEL_H

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
RED = (200, 70, 70)
REVIEW_BLUE = (90, 140, 210)
GOOD_BG = (28, 55, 32)
GOOD_BADGE = (80, 175, 100)
BAD_BG = (70, 30, 30)
BAD_BADGE = (200, 70, 70)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

pygame.font.init()
info_font = info_font_bold = label_font = title_font = option_font = hint_font = review_font = review_font_bold = None


def rebuild_fonts(cell):
    global info_font, info_font_bold, label_font, title_font, option_font, hint_font, review_font, review_font_bold
    info_font = pygame.font.SysFont("Arial", max(14, int(cell * 0.26)))
    info_font_bold = pygame.font.SysFont("Arial", max(14, int(cell * 0.26)), bold=True)
    label_font = pygame.font.SysFont("Arial", max(10, int(cell * 0.15)), bold=True)
    title_font = pygame.font.SysFont("Arial", max(28, int(cell * 0.62)), bold=True)
    option_font = pygame.font.SysFont("Arial", max(16, int(cell * 0.32)), bold=True)
    hint_font = pygame.font.SysFont("Arial", max(12, int(cell * 0.20)))
    review_font = pygame.font.SysFont("Arial", max(14, int(cell * 0.24)))
    review_font_bold = pygame.font.SysFont("Arial", max(14, int(cell * 0.24)), bold=True)


rebuild_fonts(CELL_SIZE)

_FONT_CACHE = {}


def _get_font(size, bold=False, name="Arial"):
    key = (name, size, bold)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = pygame.font.SysFont(name, size, bold=bold)
    return _FONT_CACHE[key]


def fit_text(text, base_size, max_width, color, bold=False, min_size=10):
    size = max(min_size, base_size)
    while size > min_size:
        font = _get_font(size, bold)
        if font.size(text)[0] <= max_width:
            break
        size -= 1
    return _get_font(size, bold).render(text, True, color)


_GRADIENT_CACHE = {}


def get_background_gradient(width, height, top_color=(70, 48, 32), bottom_color=(40, 26, 16)):
    width, height = max(1, int(width)), max(1, int(height))
    key = (width, height, top_color, bottom_color)
    cached = _GRADIENT_CACHE.get("key")
    if cached != key:
        surf = pygame.Surface((width, height))
        for y in range(height):
            t = y / height
            r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
            g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
            b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (width, y))
        _GRADIENT_CACHE["key"] = key
        _GRADIENT_CACHE["surface"] = surf
    return _GRADIENT_CACHE["surface"]


PIECE_IMAGES_SRC = {}
PIECE_IMAGES = {}


def init_piece_images():
    mapping = {
        chess.KING: "K", chess.QUEEN: "Q", chess.ROOK: "R",
        chess.BISHOP: "B", chess.KNIGHT: "N", chess.PAWN: "P",
    }
    for piece_type, letter in mapping.items():
        for color, prefix in ((chess.WHITE, "w"), (chess.BLACK, "b")):
            path = resource_path("assets", "pieces", f"{prefix}{letter}.png")
            PIECE_IMAGES_SRC[(color, piece_type)] = pygame.image.load(path).convert_alpha()
    rescale_piece_images(int(CELL_SIZE))


def rescale_piece_images(size):
    size = max(16, size)
    for key, src in PIECE_IMAGES_SRC.items():
        PIECE_IMAGES[key] = pygame.transform.smoothscale(src, (size, size))


def set_layout(width, height):
    global CELL_SIZE, BOARD_MARGIN, FILE_LABEL_H, BOTTOM_PANEL, BOARD_PIXELS
    global WINDOW_WIDTH, WINDOW_HEIGHT, BOARD_ORIGIN_X, BOARD_ORIGIN_Y, PANEL_TOP

    WINDOW_WIDTH, WINDOW_HEIGHT = width, height
    ratio_w = BOARD_SIZE + 2 * BASE_MARGIN_RATIO
    ratio_h = BASE_MARGIN_RATIO + BOARD_SIZE + BASE_LABEL_RATIO + BASE_PANEL_RATIO
    cell = min(width / ratio_w, height / ratio_h)
    cell = max(40, cell)

    CELL_SIZE = cell
    BOARD_MARGIN = cell * BASE_MARGIN_RATIO
    FILE_LABEL_H = cell * BASE_LABEL_RATIO
    BOTTOM_PANEL = cell * BASE_PANEL_RATIO
    BOARD_PIXELS = cell * BOARD_SIZE

    content_w = BOARD_PIXELS + 2 * BOARD_MARGIN
    content_h = BOARD_MARGIN + BOARD_PIXELS + FILE_LABEL_H + BOTTOM_PANEL
    offset_x = (width - content_w) / 2
    offset_y = (height - content_h) / 2
    BOARD_ORIGIN_X = offset_x + BOARD_MARGIN
    BOARD_ORIGIN_Y = offset_y + BOARD_MARGIN
    PANEL_TOP = BOARD_ORIGIN_Y + BOARD_PIXELS + FILE_LABEL_H

    rebuild_fonts(cell)
    if PIECE_IMAGES_SRC:
        rescale_piece_images(int(cell))


def handle_resize_events(event, screen, fullscreen):
    if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
        fullscreen = not fullscreen
        if fullscreen:
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            screen = pygame.display.set_mode((DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT), pygame.RESIZABLE)
        set_layout(*screen.get_size())
    elif event.type == pygame.VIDEORESIZE and not fullscreen:
        screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
        set_layout(*event.size)
    return screen, fullscreen


def draw_chess_piece(screen, piece, rect):
    shadow_w = int(rect.width * 0.6)
    shadow_h = int(rect.height * 0.16)
    shadow_surf = pygame.Surface((max(1, shadow_w), max(1, shadow_h)), pygame.SRCALPHA)
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


def _hover_color(color, hovered, amount=24):
    if not hovered:
        return color
    return tuple(min(255, c + amount) for c in color)


REVIEW_DEPTH = 3
STOCKFISH_REVIEW_DEPTH = 14


def win_percent(centipawns):
    centipawns = max(-1000, min(1000, centipawns))
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * centipawns)) - 1)


def move_accuracy(win_pct_before, win_pct_after):
    win_pct_loss = max(0.0, win_pct_before - win_pct_after)
    accuracy = 103.1668 * math.exp(-0.04354 * win_pct_loss) - 3.1669
    return max(0.0, min(100.0, accuracy))


def accuracy_to_score(accuracy):
    return max(1, min(10, round(accuracy / 10)))


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
        self.move_sans = []
        self.last_game_moves = []
        self.ratings_updated = False
        self.last_ai_piece = None
        self.last_move = None
        self.ai_move_history = []
        self.max_history = 4
        self.review_data = None

    def compute_ai_depth(self):
        depth = int((self.player_rating - 200) / 400) + 1
        depth = max(1, min(5, depth))
        return depth

    def square_rect(self, square):
        file = chess.square_file(square)
        rank = 7 - chess.square_rank(square)
        return pygame.Rect(
            int(BOARD_ORIGIN_X + file * CELL_SIZE),
            int(BOARD_ORIGIN_Y + rank * CELL_SIZE),
            int(CELL_SIZE), int(CELL_SIZE),
        )

    def draw_board(self, screen):
        frame_rect = pygame.Rect(0, 0, int(WINDOW_WIDTH), int(PANEL_TOP))
        screen.blit(get_background_gradient(frame_rect.width, frame_rect.height), (0, 0))
        pygame.draw.rect(
            screen, FRAME_EDGE,
            pygame.Rect(int(BOARD_ORIGIN_X - 3), int(BOARD_ORIGIN_Y - 3), int(BOARD_PIXELS + 6), int(BOARD_PIXELS + 6)),
            3,
        )

        for rank in range(BOARD_SIZE):
            for file in range(BOARD_SIZE):
                color = LIGHT_SQUARE if (rank + file) % 2 == 0 else DARK_SQUARE
                rect = pygame.Rect(
                    int(BOARD_ORIGIN_X + file * CELL_SIZE), int(BOARD_ORIGIN_Y + rank * CELL_SIZE),
                    int(CELL_SIZE) + 1, int(CELL_SIZE) + 1,
                )
                pygame.draw.rect(screen, color, rect)

        if self.last_move is not None:
            _alpha_fill(screen, self.square_rect(self.last_move.from_square), LAST_MOVE_HIGHLIGHT)
            _alpha_fill(screen, self.square_rect(self.last_move.to_square), LAST_MOVE_HIGHLIGHT)

        if self.selected_square is not None:
            _alpha_fill(screen, self.square_rect(self.selected_square), SELECT_HIGHLIGHT)
            for move in self.legal_moves:
                dest_rect = self.square_rect(move.to_square)
                cs = int(CELL_SIZE)
                indicator = pygame.Surface((cs, cs), pygame.SRCALPHA)
                if self.board.is_capture(move):
                    pygame.draw.circle(indicator, CAPTURE_RING_COLOR, (cs // 2, cs // 2), cs // 2 - 6, max(3, cs // 16))
                else:
                    pygame.draw.circle(indicator, MOVE_DOT_COLOR, (cs // 2, cs // 2), cs // 7)
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
            rect = pygame.Rect(0, 0, int(CELL_SIZE), int(CELL_SIZE))
            rect.center = (current_x, current_y)
            draw_chess_piece(screen, piece, rect)

        files = "abcdefgh"
        for file in range(BOARD_SIZE):
            label = label_font.render(files[file], True, LABEL_COLOR)
            x = int(BOARD_ORIGIN_X + file * CELL_SIZE + CELL_SIZE // 2)
            y = int(BOARD_ORIGIN_Y + BOARD_PIXELS + FILE_LABEL_H // 2)
            screen.blit(label, label.get_rect(center=(x, y)))
        for rank in range(BOARD_SIZE):
            label = label_font.render(str(8 - rank), True, LABEL_COLOR)
            x = int(BOARD_ORIGIN_X - BOARD_MARGIN / 2)
            y = int(BOARD_ORIGIN_Y + rank * CELL_SIZE + CELL_SIZE // 2)
            screen.blit(label, label.get_rect(center=(x, y)))

        self.draw_move_sidebar(screen)

        panel_rect = pygame.Rect(0, int(PANEL_TOP), int(WINDOW_WIDTH), int(WINDOW_HEIGHT - PANEL_TOP))
        pygame.draw.rect(screen, PANEL_BG, panel_rect)
        pygame.draw.rect(screen, PANEL_ACCENT, pygame.Rect(0, int(PANEL_TOP), int(WINDOW_WIDTH), 3))

        cell = CELL_SIZE
        pad = int(cell * 0.24)
        turn_str = "Your Turn (White)" if self.board.turn == chess.WHITE else "AI Turn (Black)"
        turn_text = info_font_bold.render(turn_str, True, INFO_TEXT)
        screen.blit(turn_text, (pad, int(PANEL_TOP + cell * 0.14)))

        rating_text = info_font.render(f"Player: {int(self.player_rating)}   AI: {int(self.ai_rating)}", True, MUTED_TEXT)
        screen.blit(rating_text, (pad, int(PANEL_TOP + cell * 0.48)))

        ai_text = info_font.render(f"AI Depth: {self.ai_depth}", True, MUTED_TEXT)
        screen.blit(ai_text, (pad, int(PANEL_TOP + cell * 0.78)))

        if self.game_over:
            result_text = fit_text(
                f"Game Over: {self.board.result()}  —  Press R to restart", int(cell * 0.26),
                WINDOW_WIDTH - pad * 2, INFO_TEXT, bold=True,
            )
            screen.blit(result_text, (pad, int(PANEL_TOP + cell * 1.12)))

            btn_w = int(cell * 1.5)
            btn_h = int(cell * 0.5)
            gap = int(cell * 0.16)
            btn_y = int(PANEL_TOP + (BOTTOM_PANEL - btn_h) / 2)
            self.replay_button_rect = pygame.Rect(int(WINDOW_WIDTH - pad - btn_w), btn_y, btn_w, btn_h)
            self.review_button_rect = pygame.Rect(self.replay_button_rect.left - gap - btn_w, btn_y, btn_w, btn_h)
            mouse_pos = pygame.mouse.get_pos()

            review_color = _hover_color(REVIEW_BLUE, self.review_button_rect.collidepoint(mouse_pos))
            pygame.draw.rect(screen, review_color, self.review_button_rect, border_radius=8)
            review_text = fit_text("Review", int(cell * 0.26), btn_w - 16, BLACK, bold=True)
            screen.blit(review_text, review_text.get_rect(center=self.review_button_rect.center))

            replay_color = _hover_color(GREEN, self.replay_button_rect.collidepoint(mouse_pos))
            pygame.draw.rect(screen, replay_color, self.replay_button_rect, border_radius=8)
            replay_text = fit_text("Replay", int(cell * 0.26), btn_w - 16, BLACK, bold=True)
            screen.blit(replay_text, replay_text.get_rect(center=self.replay_button_rect.center))

    def draw_move_sidebar(self, screen):
        cell = CELL_SIZE
        sidebar_left = BOARD_ORIGIN_X + BOARD_PIXELS + BOARD_MARGIN
        available = WINDOW_WIDTH - sidebar_left - BOARD_MARGIN
        min_w = cell * 2.0
        if available < min_w:
            return
        sidebar_w = min(available, cell * 3.2)
        sidebar_rect = pygame.Rect(int(sidebar_left), int(BOARD_ORIGIN_Y), int(sidebar_w), int(BOARD_PIXELS))
        pygame.draw.rect(screen, PANEL_BG, sidebar_rect, border_radius=10)
        pygame.draw.rect(screen, PANEL_ACCENT, sidebar_rect, 2, border_radius=10)

        header = info_font_bold.render("Moves", True, INFO_TEXT)
        screen.blit(header, (sidebar_rect.x + 14, sidebar_rect.y + int(cell * 0.14)))
        pygame.draw.line(
            screen, PANEL_ACCENT,
            (sidebar_rect.x + 14, sidebar_rect.y + int(cell * 0.46)),
            (sidebar_rect.right - 14, sidebar_rect.y + int(cell * 0.46)), 1,
        )

        row_h = int(cell * 0.34)
        list_top = sidebar_rect.y + int(cell * 0.58)
        visible_rows = max(1, (sidebar_rect.bottom - int(cell * 0.15) - list_top) // row_h)

        pairs = []
        sans = self.move_sans
        for i in range(0, len(sans), 2):
            num = i // 2 + 1
            white_san = sans[i]
            black_san = sans[i + 1] if i + 1 < len(sans) else ""
            pairs.append((num, white_san, black_san))

        visible_pairs = pairs[-visible_rows:]
        row_y = list_top
        num_w = int(cell * 0.42)
        move_w = int((sidebar_w - 28 - num_w) / 2)
        for num, w_san, b_san in visible_pairs:
            num_text = hint_font.render(f"{num}.", True, MUTED_TEXT)
            screen.blit(num_text, (sidebar_rect.x + 14, row_y))
            w_text = fit_text(w_san, int(cell * 0.20), move_w, INFO_TEXT)
            screen.blit(w_text, (sidebar_rect.x + 14 + num_w, row_y))
            if b_san:
                b_text = fit_text(b_san, int(cell * 0.20), move_w, INFO_TEXT)
                screen.blit(b_text, (sidebar_rect.x + 14 + num_w + move_w, row_y))
            row_y += row_h

        if not pairs:
            placeholder = hint_font.render("No moves yet", True, MUTED_TEXT)
            screen.blit(placeholder, (sidebar_rect.x + 14, list_top))

    def get_square_from_pos(self, pos):
        x, y = pos
        bx = x - BOARD_ORIGIN_X
        by = y - BOARD_ORIGIN_Y
        if bx < 0 or bx >= BOARD_PIXELS or by < 0 or by >= BOARD_PIXELS:
            return None
        file = int(bx // CELL_SIZE)
        rank = int(by // CELL_SIZE)
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
        san = self.board.san(move)
        self.board.push(move)
        self.move_history.append(move)
        self.move_sans.append(san)
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
        san = self.board.san(move)
        self.board.push(move)
        self.move_sans.append(san)
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

    def king_safety(self, board, color):
        non_pawn_material = sum(
            len(board.pieces(pt, chess.WHITE)) + len(board.pieces(pt, chess.BLACK))
            for pt in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
        )
        if non_pawn_material <= 6:
            return 0

        king_square = board.king(color)
        if king_square is None:
            return 0
        home_rank = 0 if color == chess.WHITE else 7
        castled = chess.square_rank(king_square) == home_rank and chess.square_file(king_square) in (2, 6)
        if castled:
            return 60
        has_rights = board.has_kingside_castling_rights(color) or board.has_queenside_castling_rights(color)
        if not has_rights:
            rank_distance = abs(chess.square_rank(king_square) - home_rank)
            return -120 - rank_distance * 40
        return 0

    DEVELOPMENT_SQUARES = {
        chess.WHITE: ((chess.KNIGHT, chess.B1), (chess.KNIGHT, chess.G1), (chess.BISHOP, chess.C1), (chess.BISHOP, chess.F1)),
        chess.BLACK: ((chess.KNIGHT, chess.B8), (chess.KNIGHT, chess.G8), (chess.BISHOP, chess.C8), (chess.BISHOP, chess.F8)),
    }

    def development_score(self, board, color):
        if len(board.move_stack) > 30:
            return 0
        score = 0
        for piece_type, square in self.DEVELOPMENT_SQUARES[color]:
            piece = board.piece_at(square)
            if piece is None or piece.piece_type != piece_type or piece.color != color:
                score += 18
        return score

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

        eval += self.king_safety(board, chess.WHITE)
        eval -= self.king_safety(board, chess.BLACK)
        eval += self.development_score(board, chess.WHITE)
        eval -= self.development_score(board, chess.BLACK)
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

    def evaluate_root_moves(self, board, depth):
        results = {}
        maximizing = board.turn == chess.WHITE
        for move in board.legal_moves:
            board.push(move)
            _, score = self.minimax(board, depth - 1, -math.inf, math.inf, not maximizing)
            board.pop()
            results[move] = score
        return results

    def review_game(self):
        if not self.last_game_moves:
            return []
        engine_path = find_stockfish()
        if engine_path:
            try:
                return self._review_with_stockfish(engine_path)
            except (chess.engine.EngineError, OSError):
                pass
        return self._review_with_builtin_engine()

    def _review_with_stockfish(self, engine_path):
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        limit = chess.engine.Limit(depth=STOCKFISH_REVIEW_DEPTH)
        review_board = chess.Board()
        results = []
        try:
            for move in self.last_game_moves:
                if review_board.turn == chess.WHITE:
                    eval_before = engine.analyse(review_board, limit)["score"].white().score(mate_score=10000)
                    san = review_board.san(move)
                    move_number = review_board.fullmove_number
                    review_board.push(move)
                    eval_after = engine.analyse(review_board, limit)["score"].white().score(mate_score=10000)
                    accuracy = move_accuracy(win_percent(eval_before), win_percent(eval_after))
                    results.append({
                        "move_number": move_number,
                        "san": san,
                        "score": accuracy_to_score(accuracy),
                    })
                else:
                    review_board.push(move)
        finally:
            engine.quit()
        return results

    def _review_with_builtin_engine(self):
        review_board = chess.Board()
        results = []
        for move in self.last_game_moves:
            if review_board.turn == chess.WHITE:
                move_evals = self.evaluate_root_moves(review_board, REVIEW_DEPTH)
                best_eval = max(move_evals.values())
                played_eval = move_evals[move]
                accuracy = move_accuracy(win_percent(best_eval), win_percent(played_eval))
                san = review_board.san(move)
                results.append({
                    "move_number": review_board.fullmove_number,
                    "san": san,
                    "score": accuracy_to_score(accuracy),
                })
            review_board.push(move)
        return results

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

        player_moves = self.move_history[0::2]
        moves_made = len(player_moves)
        pieces_moved = len(set(move.from_square for move in player_moves if move.from_square != move.to_square))

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
        self.move_sans = []
        screen.fill(BLACK)
        self.draw_board(screen)
        pygame.display.update()
        pygame.time.delay(1000)
        for move in self.last_game_moves:
            self.animate_move_replay(move, screen, clock)
        pygame.time.delay(1000)
        self.board.reset()
        self.move_history = []
        self.move_sans = []
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
        self.move_sans = []
        self.ratings_updated = False
        if not self.calibration_mode:
            self.ai_rating = self.player_rating
        self.ai_move_history = []
        self.last_move = None
        self.review_data = None


def choose_start_mode(screen, clock, saved, fullscreen):
    history = saved[2] if saved else []
    continue_label = f"Continue (Rating: {int(saved[0])})" if saved else "Continue (Rating: 1000)"

    while True:
        clock.tick(30)
        cell = CELL_SIZE
        title_y = int(WINDOW_HEIGHT * 0.13)
        btn_w = min(int(cell * 4.6), int(WINDOW_WIDTH * 0.7))
        btn_h = int(cell * 0.56)

        continue_rect = pygame.Rect(0, 0, btn_w, btn_h)
        continue_rect.center = (WINDOW_WIDTH // 2, title_y + int(cell * 1.5))
        recalibrate_rect = pygame.Rect(0, 0, btn_w, btn_h)
        recalibrate_rect.center = (WINDOW_WIDTH // 2, continue_rect.bottom + int(cell * 0.35) + btn_h // 2)

        hint_y = recalibrate_rect.bottom + int(cell * 0.45)
        card_top = hint_y + int(cell * 0.5)
        card_w = min(int(cell * 6.4), int(WINDOW_WIDTH * 0.88))
        row_h = int(cell * 0.4)
        max_rows = 8
        shown = list(reversed(history))[:max_rows]
        card_header_h = int(cell * 0.55)
        card_h = card_header_h + row_h * max(1, len(shown)) + int(cell * 0.15)
        max_card_h = WINDOW_HEIGHT - card_top - int(cell * 0.3)
        card_h = min(card_h, max(int(cell * 1.2), max_card_h))
        card_rect = pygame.Rect(0, 0, card_w, card_h)
        card_rect.centerx = WINDOW_WIDTH // 2
        card_rect.top = card_top

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            screen, fullscreen = handle_resize_events(event, screen, fullscreen)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if continue_rect.collidepoint(event.pos):
                    return screen, fullscreen, "continue"
                if recalibrate_rect.collidepoint(event.pos):
                    return screen, fullscreen, "recalibrate"

        screen.blit(get_background_gradient(WINDOW_WIDTH, WINDOW_HEIGHT), (0, 0))
        if (chess.WHITE, chess.KING) in PIECE_IMAGES_SRC:
            watermark_size = int(WINDOW_HEIGHT * 0.9)
            watermark = pygame.transform.smoothscale(PIECE_IMAGES_SRC[(chess.WHITE, chess.KING)], (watermark_size, watermark_size))
            watermark.set_alpha(16)
            screen.blit(watermark, watermark.get_rect(center=(int(WINDOW_WIDTH * 0.88), int(WINDOW_HEIGHT * 0.4))))

        title = title_font.render("AI Chess Elo", True, (216, 178, 122))
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, title_y)))

        mouse_pos = pygame.mouse.get_pos()
        for rect, label in ((continue_rect, continue_label), (recalibrate_rect, "Recalibrate (Fresh Baseline Game)")):
            hovered = rect.collidepoint(mouse_pos)
            pygame.draw.rect(screen, _hover_color(PANEL_BG, hovered, 10), rect, border_radius=10)
            pygame.draw.rect(screen, PANEL_ACCENT, rect, 2, border_radius=10)
            text = fit_text(label, int(cell * 0.32), rect.width - 28, WHITE, bold=True)
            screen.blit(text, text.get_rect(center=rect.center))

        hint = fit_text(
            "Recalibrate resets your rating to 1000 and re-ranks you from this game.  (F11: fullscreen)",
            int(cell * 0.20), int(WINDOW_WIDTH * 0.92), MUTED_TEXT,
        )
        screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, hint_y)))

        pygame.draw.rect(screen, PANEL_BG, card_rect, border_radius=10)
        pygame.draw.rect(screen, PANEL_ACCENT, card_rect, 2, border_radius=10)
        header = info_font_bold.render("Recent Games", True, INFO_TEXT)
        screen.blit(header, (card_rect.x + 18, card_rect.y + int(cell * 0.1)))

        if not shown:
            placeholder = hint_font.render("No games played yet — play your first game below!", True, MUTED_TEXT)
            screen.blit(placeholder, (card_rect.x + 18, card_rect.y + card_header_h))
        else:
            row_y = card_rect.y + card_header_h
            for entry in shown:
                if row_y + row_h > card_rect.bottom - 4:
                    break
                delta = entry["after"] - entry["before"]
                delta_str = f"+{delta}" if delta > 0 else str(delta)
                delta_color = GREEN if delta > 0 else RED if delta < 0 else MUTED_TEXT
                line1 = hint_font.render(f"{entry['date']}  ·  {entry['result']}", True, MUTED_TEXT)
                screen.blit(line1, (card_rect.x + 18, row_y + 2))
                line2 = hint_font.render(f"{entry['before']} → {entry['after']}", True, INFO_TEXT)
                line2_rect = line2.get_rect()
                line2_rect.topright = (card_rect.right - 90, row_y + 2)
                screen.blit(line2, line2_rect)
                delta_text = hint_font.render(f"({delta_str})", True, delta_color)
                delta_rect = delta_text.get_rect()
                delta_rect.topright = (card_rect.right - 18, row_y + 2)
                screen.blit(delta_text, delta_rect)
                row_y += row_h

        pygame.display.update()


def show_review_screen(screen, clock, review_data, fullscreen):
    scroll = 0
    avg = sum(r["score"] for r in review_data) / len(review_data) if review_data else 0

    while True:
        clock.tick(30)
        cell = CELL_SIZE
        header_h = int(cell * 1.5)
        row_h = int(cell * 0.5)
        list_top = header_h
        list_bottom = WINDOW_HEIGHT - int(cell * 0.7)
        visible_rows = max(1, (list_bottom - list_top) // row_h)
        max_scroll = max(0, len(review_data) - visible_rows)
        scroll = max(0, min(scroll, max_scroll))

        back_button_rect = pygame.Rect(0, 0, int(cell * 1.8), int(cell * 0.5))
        back_button_rect.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT - int(cell * 0.38))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            screen, fullscreen = handle_resize_events(event, screen, fullscreen)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return screen, fullscreen
                if event.key == pygame.K_DOWN:
                    scroll = min(max_scroll, scroll + 1)
                if event.key == pygame.K_UP:
                    scroll = max(0, scroll - 1)
            if event.type == pygame.MOUSEWHEEL:
                scroll = max(0, min(max_scroll, scroll - event.y))
            if event.type == pygame.MOUSEBUTTONDOWN:
                if back_button_rect.collidepoint(event.pos):
                    return screen, fullscreen

        screen.blit(get_background_gradient(WINDOW_WIDTH, WINDOW_HEIGHT), (0, 0))
        title = title_font.render("Game Review", True, (216, 178, 122))
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, int(cell * 0.5))))
        subtitle = option_font.render(f"Average Move Quality: {avg:.1f}/10", True, INFO_TEXT)
        screen.blit(subtitle, subtitle.get_rect(center=(WINDOW_WIDTH // 2, int(cell * 1.0))))

        list_w = min(int(cell * 6.5), int(WINDOW_WIDTH * 0.9))
        list_x = (WINDOW_WIDTH - list_w) // 2
        visible = review_data[scroll:scroll + visible_rows]
        y = list_top
        for entry in visible:
            row_rect = pygame.Rect(int(list_x), int(y), int(list_w), int(row_h - 6))
            score = entry["score"]
            if score <= 3:
                bg, badge = BAD_BG, BAD_BADGE
            elif score >= 9:
                bg, badge = GOOD_BG, GOOD_BADGE
            else:
                bg, badge = PANEL_BG, PANEL_ACCENT
            pygame.draw.rect(screen, bg, row_rect, border_radius=6)
            badge_rect = pygame.Rect(0, 0, int(cell * 0.5), int(cell * 0.34))
            badge_rect.midright = (row_rect.right - 16, row_rect.centery)
            move_text = fit_text(f"{entry['move_number']}. {entry['san']}", int(cell * 0.24), row_rect.width - 32 - badge_rect.width, INFO_TEXT)
            screen.blit(move_text, (row_rect.x + 16, row_rect.centery - move_text.get_height() // 2))
            pygame.draw.rect(screen, badge, badge_rect, border_radius=6)
            score_text = review_font_bold.render(str(score), True, WHITE)
            screen.blit(score_text, score_text.get_rect(center=badge_rect.center))
            y += row_h

        if not review_data:
            empty = hint_font.render("No moves to review.", True, MUTED_TEXT)
            screen.blit(empty, empty.get_rect(center=(WINDOW_WIDTH // 2, list_top + 40)))

        back_hovered = back_button_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, _hover_color(PANEL_BG, back_hovered, 10), back_button_rect, border_radius=8)
        pygame.draw.rect(screen, PANEL_ACCENT, back_button_rect, 2, border_radius=8)
        back_text = fit_text("Back (Esc)", int(cell * 0.32), back_button_rect.width - 16, WHITE, bold=True)
        screen.blit(back_text, back_text.get_rect(center=back_button_rect.center))

        pygame.display.update()


def main():
    fullscreen = False
    screen = pygame.display.set_mode((DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("AI Chess – Rated & Replay Mode")
    clock = pygame.time.Clock()
    set_layout(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
    init_piece_images()

    saved = load_saved_ratings()
    history = list(saved[2]) if saved else []
    screen, fullscreen, mode = choose_start_mode(screen, clock, saved, fullscreen)
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
            screen, fullscreen = handle_resize_events(event, screen, fullscreen)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if game.game_over:
                    if hasattr(game, "replay_button_rect") and game.replay_button_rect.collidepoint(pygame.mouse.get_pos()):
                        game.replay_game(screen, clock)
                        continue
                    if hasattr(game, "review_button_rect") and game.review_button_rect.collidepoint(pygame.mouse.get_pos()):
                        screen, fullscreen = show_review_screen(screen, clock, game.review_data or [], fullscreen)
                        continue
                if game.board.turn == chess.WHITE and not game.game_over:
                    game.handle_click(pygame.mouse.get_pos(), screen, clock)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game.reset_game()

        if game.game_over and not game.ratings_updated:
            before = game.player_rating
            game.update_ratings()
            game.ratings_updated = True
            result = game.board.result()
            outcome = "Win" if result == "1-0" else "Loss" if result == "0-1" else "Draw"
            history.append({
                "date": time.strftime("%b %d"),
                "result": outcome,
                "before": round(before),
                "after": round(game.player_rating),
            })
            history = history[-50:]
            save_ratings(game.player_rating, game.ai_rating, history)

            screen.blit(get_background_gradient(WINDOW_WIDTH, WINDOW_HEIGHT), (0, 0))
            loading = title_font.render("Analyzing your game…", True, (216, 178, 122))
            screen.blit(loading, loading.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)))
            pygame.display.update()
            game.review_data = game.review_game()

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
