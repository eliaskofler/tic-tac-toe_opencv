"""The tic-tac-toe grid, difficulty-select buttons, and the win/result overlay."""
import time

import pygame

from .. import config
from ..animation import pop_in_scale, tint


def get_level_zones(layout):
    """Rects (in warped board coordinates) for the EASY / MID / HARD choices, laid out as
    a 2x2 grid of equal-sized cells. The 4th cell ("filler") isn't a real choice - it just
    fills out the grid so EASY isn't twice the area of MID/HARD (which made it nearly
    impossible to cover 25% of it with a single X)."""
    board_rect = layout.board_rect
    margin = 40  # keep the buttons off the board's edges, not just spaced from each other
    gap = 30
    available_w = board_rect.width - margin * 2
    available_h = board_rect.height - margin * 2

    col_w = (available_w - gap) // 2
    row_h = (available_h - gap) // 2

    grid_w = col_w * 2 + gap
    grid_h = row_h * 2 + gap
    start_x = board_rect.left + (board_rect.width - grid_w) // 2
    start_y = board_rect.top + (board_rect.height - grid_h) // 2
    right_x = start_x + col_w + gap
    bottom_y = start_y + row_h + gap

    return {
        "easy": pygame.Rect(start_x, start_y, col_w, row_h),
        "mid": pygame.Rect(right_x, start_y, col_w, row_h),
        "hard": pygame.Rect(start_x, bottom_y, col_w, row_h),
        "filler": pygame.Rect(right_x, bottom_y, col_w, row_h),
    }


def draw_zone(screen, font, rect, label, color, radius=20, shadow_offset=6, scale=1.0):
    if scale != 1.0:
        rect = rect.inflate(int(rect.width * (scale - 1)), int(rect.height * (scale - 1)))
        shadow_offset = int(shadow_offset * scale)

    shadow_color = tuple(max(0, ch - 60) for ch in color)
    pygame.draw.rect(screen, shadow_color, rect.move(shadow_offset, shadow_offset), border_radius=radius)

    pygame.draw.rect(screen, tint(color, 0.65), rect, border_radius=radius)
    pygame.draw.rect(screen, color, rect, width=3, border_radius=radius)
    text_surf = font.render(label, True, color)
    screen.blit(text_surf, text_surf.get_rect(center=rect.center))


def render_board_surface(layout, state, fonts, include_result=True):
    """Renders the grid/marks onto a fresh board-local surface, ready to be clipped and
    blitted at board_rect.topleft. Once the round is over, the grid is cleared away and
    only the result banner + restart countdown are shown."""
    board_rect = layout.board_rect
    cell_w, cell_h = layout.cell_w, layout.cell_h
    board = state.board

    board_surf = pygame.Surface(board_rect.size, pygame.SRCALPHA)
    board_surf.fill((255, 255, 255, 255))

    revealing = (
        state.game_over
        and state.game_over_time is not None
        and time.time() - state.game_over_time < config.REVEAL_DELAY
    )

    if not state.game_over or revealing:
        for r in range(3):
            for c in range(3):
                if board[r][c] == "X":
                    cell_rect = pygame.Rect(c * cell_w, r * cell_h, cell_w, cell_h)
                    board_surf.fill((150, 220, 150), cell_rect)
                elif board[r][c] == "O":
                    cell_rect = pygame.Rect(c * cell_w, r * cell_h, cell_w, cell_h)
                    board_surf.fill((150, 190, 230), cell_rect)

        for i in range(1, 3):
            pygame.draw.line(board_surf, (70, 70, 70), (i * cell_w, 0), (i * cell_w, board_rect.height), 3)
            pygame.draw.line(board_surf, (70, 70, 70), (0, i * cell_h), (board_rect.width, i * cell_h), 3)

        for r in range(3):
            for c in range(3):
                if board[r][c] == "":
                    continue

                center_x = c * cell_w + cell_w // 2
                center_y = r * cell_h + cell_h // 2
                offset = min(cell_w, cell_h) // 4

                anim_start = state.mark_anim_start.get((r, c))
                if anim_start is not None:
                    t = min(1.0, (time.time() - anim_start) / config.MARK_ANIM_DURATION)
                    offset = int(offset * pop_in_scale(t))

                if board[r][c] == "X":
                    pygame.draw.line(board_surf, (34, 139, 34), (center_x - offset, center_y - offset), (center_x + offset, center_y + offset), 5)
                    pygame.draw.line(board_surf, (34, 139, 34), (center_x + offset, center_y - offset), (center_x - offset, center_y + offset), 5)
                elif board[r][c] == "O":
                    pygame.draw.circle(board_surf, (30, 100, 220), (center_x, center_y), offset, 6)

    if include_result and state.game_over and state.game_over_time is not None and not revealing:
        if state.winner == "Tie":
            result_text, result_color = "TIE!", (100, 100, 100)
        elif state.winner == "X":
            result_text, result_color = "YOU WIN!", (34, 139, 34)
        else:
            result_text, result_color = "YOU LOSE!", (200, 40, 40)

        result_surf = fonts.result.render(result_text, True, result_color)
        board_surf.blit(result_surf, result_surf.get_rect(center=(board_rect.width // 2, board_rect.height // 2 - 80)))

        remaining = max(0, config.RESTART_DELAY - int(time.time() - state.game_over_time - config.REVEAL_DELAY))
        countdown_surf = fonts.countdown.render(str(remaining), True, (40, 40, 40))
        board_surf.blit(countdown_surf, countdown_surf.get_rect(center=(board_rect.width // 2, board_rect.height // 2 + 60)))

    return board_surf


def clip_to_board_radius(surf):
    mask_surf = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(mask_surf, (255, 255, 255, 255), mask_surf.get_rect(), border_radius=config.PANEL_RADIUS)
    surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
