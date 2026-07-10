"""Generic "floating card" drawing primitives shared by the side panel and board frame."""
import pygame


def draw_card(screen, rect, accent_color, radius=16, shadow_offset=6):
    shadow_color = tuple(max(0, ch - 50) for ch in accent_color)
    pygame.draw.rect(screen, shadow_color, rect.move(shadow_offset, shadow_offset), border_radius=radius)
    pygame.draw.rect(screen, (255, 255, 255), rect, border_radius=radius)
    pygame.draw.rect(screen, accent_color, rect, width=3, border_radius=radius)


def draw_translucent_border(screen, rect, color, radius, width=3, alpha=110):
    border_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(border_surf, (*color, alpha), border_surf.get_rect(), width=width, border_radius=radius)
    screen.blit(border_surf, rect.topleft)


def draw_rounded_gradient(screen, rect, color_top, color_bottom, radius):
    gradient_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    h = max(1, rect.height)
    for i in range(rect.height):
        t = i / h
        color = tuple(int(color_top[ch] + (color_bottom[ch] - color_top[ch]) * t) for ch in range(3))
        pygame.draw.line(gradient_surf, (*color, 255), (0, i), (rect.width, i))

    mask_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(mask_surf, (255, 255, 255, 255), mask_surf.get_rect(), border_radius=radius)
    gradient_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    screen.blit(gradient_surf, rect.topleft)


def wrap_text(text, font, max_width):
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
