"""The right-hand status/statistics side panel."""
import pygame

from .. import config
from ..animation import tint
from .widgets import draw_card, draw_rounded_gradient, draw_translucent_border, wrap_text


def draw_side_panel(screen, layout, state, fonts):
    panel_rect = layout.panel_rect
    if panel_rect.width <= 0 or panel_rect.height <= 0:
        return

    bg_rect = panel_rect.inflate(-config.PANEL_MARGIN * 2, -config.PANEL_MARGIN * 2)
    if bg_rect.width <= 0 or bg_rect.height <= 0:
        return

    difficulty_color = config.LEVEL_COLORS.get(state.current_level_label, config.NO_DIFFICULTY_COLOR)
    draw_rounded_gradient(screen, bg_rect, tint(difficulty_color, 0.75), tint(difficulty_color, 0.55), config.PANEL_RADIUS)

    border_color = tuple(max(0, ch - 60) for ch in difficulty_color)
    draw_translucent_border(screen, bg_rect, border_color, config.PANEL_RADIUS)

    pad = 18
    inner_w = bg_rect.width - pad * 2
    x = bg_rect.left + pad

    # --- Difficulty title ---
    title_text = state.current_level_label if state.current_level_label else "Tic.. Tac.. Toe"
    diff_title_surf = fonts.panel_title.render(title_text, True, border_color)
    screen.blit(diff_title_surf, diff_title_surf.get_rect(midtop=(bg_rect.centerx, bg_rect.top + pad)))
    top_y = bg_rect.top + pad + diff_title_surf.get_height() + 14

    # --- Statistics card (anchored to the top) ---
    stats = state.stats
    stat_rows = [
        ("Games", str(stats["games"]), None),
        ("Wins", str(stats["wins"]), config.WIN_COLOR),
        ("Losses", str(stats["losses"]), config.LOSS_COLOR),
        ("Ties", str(stats["ties"]), config.TIE_COLOR),
    ]
    title_h = fonts.panel_header.get_height()
    row_h = fonts.panel.get_height() + 14
    bar_h = 18
    stats_card_h = 16 + title_h + 10 + row_h * len(stat_rows) + 8 + bar_h + fonts.panel.get_height() + 14
    stats_card = pygame.Rect(x, top_y, inner_w, stats_card_h)
    draw_card(screen, stats_card, config.STATS_ACCENT)

    sy = stats_card.top + 12
    title_surf = fonts.panel_header.render("STATISTICS", True, config.STATS_ACCENT)
    screen.blit(title_surf, (stats_card.left + 14, sy))
    sy += title_surf.get_height() + 10

    for label, value, dot_color in stat_rows:
        if dot_color:
            pygame.draw.circle(screen, dot_color, (stats_card.left + 22, sy + row_h // 2 - 2), 6)
        label_surf = fonts.panel.render(label, True, config.INK_COLOR)
        screen.blit(label_surf, (stats_card.left + 38, sy))
        value_surf = fonts.panel.render(value, True, dot_color or config.INK_COLOR)
        screen.blit(value_surf, (stats_card.right - 14 - value_surf.get_width(), sy))
        sy += row_h

    games = stats["games"]
    win_rate = (stats["wins"] / games) if games else 0.0
    bar_x = stats_card.left + 14
    bar_w = stats_card.width - 28
    pygame.draw.rect(screen, (230, 230, 230), (bar_x, sy, bar_w, bar_h), border_radius=bar_h // 2)
    fill_w = int(bar_w * win_rate)
    if fill_w > 0:
        pygame.draw.rect(screen, config.WIN_COLOR, (bar_x, sy, fill_w, bar_h), border_radius=bar_h // 2)
    sy += bar_h + 6
    rate_surf = fonts.panel.render(f"Win rate: {win_rate * 100:.0f}%", True, config.INK_COLOR)
    screen.blit(rate_surf, (bar_x, sy))

    # --- Status card (anchored to the bottom) ---
    status_lines = wrap_text(state.status_msg, fonts.panel, inner_w - 28)
    line_h = fonts.panel.get_height() + 4
    status_card_h = 16 + title_h + 6 + len(status_lines) * line_h + 10
    status_card = pygame.Rect(x, bg_rect.bottom - pad - status_card_h, inner_w, status_card_h)
    draw_card(screen, status_card, config.STATUS_ACCENT)

    ty = status_card.top + 12
    title_surf = fonts.panel_header.render("STATUS", True, config.STATUS_ACCENT)
    screen.blit(title_surf, (status_card.left + 14, ty))
    ty += title_surf.get_height() + 6
    for line in status_lines:
        line_surf = fonts.panel.render(line, True, config.INK_COLOR)
        screen.blit(line_surf, (status_card.left + 14, ty))
        ty += line_h
