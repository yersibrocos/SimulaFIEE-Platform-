from pathlib import Path
import os
import subprocess
import sys

import pygame


WINDOW_SIZE = (1280, 720)
FPS = 60
TRANSITION_MS = 500
DISPLAY_WINDOWED = "windowed"
DISPLAY_WINDOWED_LARGE = "windowed_large"
DISPLAY_FULLSCREEN = "fullscreen"

STATE_MENU = "menu"
STATE_EXPLORE_1 = "explore_1"
STATE_EXPLORE_2 = "explore_2"
STATE_WORKSHOP_ELECTRIC = "workshop_electric"
STATE_WORKSHOP_ELECTRONICS = "workshop_electronics"
STATE_WORKSHOP_TELECOM = "workshop_telecom"
STATE_WORKSHOP_CYBER = "workshop_cyber"


class TextButton:
    def __init__(self, rect, label, font):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.font = font
        self.hovered = False
        self.base_color = (18, 43, 72)
        self.hover_color = (25, 62, 105)
        self.border_color = (233, 245, 255)
        self.text_color = (245, 250, 255)

    def draw(self, screen):
        color = self.hover_color if self.hovered else self.base_color
        pygame.draw.rect(screen, color, self.rect, border_radius=14)
        pygame.draw.rect(screen, self.border_color, self.rect, width=2, border_radius=14)
  
        text_surface = self.font.render(self.label, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def update_hover(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


class ArrowButton:
    def __init__(self, rect, direction, label, font):
        self.rect = pygame.Rect(rect)
        self.direction = direction
        self.label = label
        self.font = font
        self.hovered = False
        self.base_color = (10, 31, 55)
        self.hover_color = (20, 58, 97)
        self.border_color = (230, 241, 255)
        self.text_color = (240, 247, 255)

    def draw(self, screen):
        color = self.hover_color if self.hovered else self.base_color
        pygame.draw.rect(screen, color, self.rect, border_radius=14)
        pygame.draw.rect(screen, self.border_color, self.rect, width=2, border_radius=14)

        x, y, w, h = self.rect
        if self.direction == "left":
            points = [(x + 20, y + h // 2), (x + 42, y + 16), (x + 42, y + h - 16)]
            text_center = (x + (w + 35) // 2, y + h // 2)
        else:
            points = [(x + w - 20, y + h // 2), (x + w - 42, y + 16), (x + w - 42, y + h - 16)]
            text_center = (x + (w - 35) // 2, y + h // 2)

        pygame.draw.polygon(screen, self.text_color, points)
        text_surface = self.font.render(self.label, True, self.text_color)
        text_rect = text_surface.get_rect(center=text_center)
        screen.blit(text_surface, text_rect)

    def update_hover(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


def present_frame(display_surface, frame_surface):
    display_size = display_surface.get_size()
    if display_size == WINDOW_SIZE:
        display_surface.blit(frame_surface, (0, 0))
    else:
        scaled = pygame.transform.smoothscale(frame_surface, display_size)
        display_surface.blit(scaled, (0, 0))
    pygame.display.flip()


def to_virtual_pos(pos, display_surface):
    w, h = display_surface.get_size()
    if w == 0 or h == 0:
        return pos
    scale_x = WINDOW_SIZE[0] / w
    scale_y = WINDOW_SIZE[1] / h
    return int(pos[0] * scale_x), int(pos[1] * scale_y)


def apply_display_mode(mode):
    if mode == DISPLAY_FULLSCREEN:
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    if mode == DISPLAY_WINDOWED_LARGE:
        return pygame.display.set_mode((1600, 900))
    return pygame.display.set_mode(WINDOW_SIZE)


def load_background(base_path, size, candidates):
    for name in candidates:
        path = base_path / name
        if path.exists():
            image = pygame.image.load(str(path)).convert()
            return pygame.transform.smoothscale(image, size), name

    raise FileNotFoundError(f"No se encontro ninguna imagen valida: {', '.join(candidates)}")


def draw_title(screen, font):
    subtitle_font = pygame.font.SysFont("Segoe UI", 28, bold=True)
    shadow = font.render("SimulaFIEE Platform", True, (5, 8, 12))
    title = font.render("SimulaFIEE Platform", True, (247, 252, 255))
    subtitle_shadow = subtitle_font.render(
        "Simulador de Ingenierias de la Facultad de Ingenieria Electrica y Electronica",
        True,
        (5, 8, 12),
    )
    subtitle = subtitle_font.render(
        "Simulador de Ingenierias de la Facultad de Ingenieria Electrica y Electronica",
        True,
        (231, 243, 255),
    )

    shadow_rect = shadow.get_rect(center=(WINDOW_SIZE[0] // 2 + 2, 92 + 2))
    title_rect = title.get_rect(center=(WINDOW_SIZE[0] // 2, 92))
    subtitle_shadow_rect = subtitle_shadow.get_rect(center=(WINDOW_SIZE[0] // 2 + 1, 146 + 1))
    subtitle_rect = subtitle.get_rect(center=(WINDOW_SIZE[0] // 2, 146))
    screen.blit(shadow, shadow_rect)
    screen.blit(title, title_rect)
    screen.blit(subtitle_shadow, subtitle_shadow_rect)
    screen.blit(subtitle, subtitle_rect)


def fade_transition(display_surface, frame_surface, clock, current_surface, target_surface, duration_ms):
    if current_surface is target_surface:
        return

    start = pygame.time.get_ticks()
    overlay = target_surface.copy()

    while True:
        elapsed = pygame.time.get_ticks() - start
        progress = min(1.0, elapsed / duration_ms)
        alpha = int(progress * 255)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        frame_surface.blit(current_surface, (0, 0))
        overlay.set_alpha(alpha)
        frame_surface.blit(overlay, (0, 0))
        present_frame(display_surface, frame_surface)
        clock.tick(FPS)

        if progress >= 1.0:
            break


def launch_external_script(base_path, script_name, display_mode):
    script_path = base_path / script_name
    if not script_path.exists():
        return

    env = dict(os.environ)
    env["SIMULAFIEE_DISPLAY_MODE"] = display_mode
    subprocess.run([sys.executable, str(script_path)], cwd=str(base_path), check=False, env=env)


def main():
    pygame.init()
    pygame.display.set_caption(
        "SimulaFIEE Platform — Simulador de Ingenierias de la Facultad de Ingenieria Electrica y Electronica"
    )
    display_mode = DISPLAY_WINDOWED
    display_surface = apply_display_mode(display_mode)
    screen = pygame.Surface(WINDOW_SIZE).convert()
    clock = pygame.time.Clock()

    base_path = Path(__file__).resolve().parent
    background_menu, menu_name = load_background(base_path, WINDOW_SIZE, ["FIEE.2.jpg", "FIEE2.jpg"])
    background_explore_1, _ = load_background(base_path, WINDOW_SIZE, ["FIEE4.jpg"])
    background_explore_2, _ = load_background(base_path, WINDOW_SIZE, ["FIEE_entrada.png"])
    background_workshop_electric, _ = load_background(base_path, WINDOW_SIZE, ["FIEE5.png", "FIEE5.jpg"])

    backgrounds = {
        STATE_MENU: background_menu,
        STATE_EXPLORE_1: background_explore_1,
        STATE_EXPLORE_2: background_explore_2,
        STATE_WORKSHOP_ELECTRIC: background_workshop_electric,
        STATE_WORKSHOP_ELECTRONICS: background_workshop_electric,
        STATE_WORKSHOP_TELECOM: background_workshop_electric,
        STATE_WORKSHOP_CYBER: background_workshop_electric,
    }

    title_font = pygame.font.SysFont("Segoe UI", 58, bold=True)
    button_font = pygame.font.SysFont("Segoe UI", 34, bold=True)
    arrow_font = pygame.font.SysFont("Segoe UI", 32, bold=True)
    info_font = pygame.font.SysFont("Segoe UI", 22)

    button_w = 360
    button_h = 72
    x = (WINDOW_SIZE[0] - button_w) // 2
    first_y = 230
    gap = 24

    explore_button = TextButton((x, first_y, button_w, button_h), "Explorar la FIEE", button_font)
    exit_button = TextButton((x, first_y + button_h + gap, button_w, button_h), "Salir", button_font)

    left_back = ArrowButton((40, WINDOW_SIZE[1] - 110, 220, 70), "left", "Volver", arrow_font)
    right_next = ArrowButton((WINDOW_SIZE[0] - 260, WINDOW_SIZE[1] - 110, 220, 70), "right", "Seguir", arrow_font)
    right_back = ArrowButton((WINDOW_SIZE[0] - 260, WINDOW_SIZE[1] - 110, 220, 70), "left", "Volver", arrow_font)
    electric_workshop_back = ArrowButton((WINDOW_SIZE[0] - 260, WINDOW_SIZE[1] - 110, 220, 70), "left", "Volver", arrow_font)

    workshop_arrow_w = 480
    workshop_arrow_h = 70
    workshop_arrow_x = 36
    workshop_arrow_start_y = 174
    workshop_arrow_gap = 18

    workshop_electric = ArrowButton(
        (workshop_arrow_x, workshop_arrow_start_y, workshop_arrow_w, workshop_arrow_h),
        "right",
        "Taller de electrica",
        arrow_font,
    )
    workshop_electronics = ArrowButton(
        (
            workshop_arrow_x,
            workshop_arrow_start_y + (workshop_arrow_h + workshop_arrow_gap),
            workshop_arrow_w,
            workshop_arrow_h,
        ),
        "right",
        "Taller de electronica",
        arrow_font,
    )
    workshop_telecom = ArrowButton(
        (
            workshop_arrow_x,
            workshop_arrow_start_y + (workshop_arrow_h + workshop_arrow_gap) * 2,
            workshop_arrow_w,
            workshop_arrow_h,
        ),
        "right",
        "Taller de telecomunicaciones",
        arrow_font,
    )
    workshop_cyber = ArrowButton(
        (
            workshop_arrow_x,
            workshop_arrow_start_y + (workshop_arrow_h + workshop_arrow_gap) * 3,
            workshop_arrow_w,
            workshop_arrow_h,
        ),
        "right",
        "Taller de ciberseguridad",
        arrow_font,
    )
    explore_2_workshops = (
        workshop_electric,
        workshop_electronics,
        workshop_telecom,
        workshop_cyber,
    )

    module_button_w = 300
    module_button_h = 48
    module_gap = 12
    module_col_gap = 46
    module_start_y = 150
    module_left_x = (WINDOW_SIZE[0] - module_button_w) // 2
    module_right_x = WINDOW_SIZE[0] // 2 + module_col_gap // 2

    modules_left = [
        "Tablero electrico",
        "Motor electrico",
        "Control industrial",
        "Energia solar",
        "Circuito electrico",
    ]
    modules_right = []
    electric_workshop_modules = []

    for index, label in enumerate(modules_left):
        electric_workshop_modules.append(
            TextButton(
                (
                    module_left_x,
                    module_start_y + index * (module_button_h + module_gap),
                    module_button_w,
                    module_button_h,
                ),
                label,
                info_font,
            )
        )

    for index, label in enumerate(modules_right):
        electric_workshop_modules.append(
            TextButton(
                (
                    module_right_x,
                    module_start_y + index * (module_button_h + module_gap),
                    module_button_w,
                    module_button_h,
                ),
                label,
                info_font,
            )
        )

    placeholder_button_w = 360
    placeholder_button_h = 60
    placeholder_gap = 20
    placeholder_x = (WINDOW_SIZE[0] - placeholder_button_w) // 2
    placeholder_start_y = 230

    def build_placeholder_modules(labels=None):
        if labels is None:
            labels = ["Componentes Electrónica", "Protoboard"]

        return [
            TextButton(
                (
                    placeholder_x,
                    placeholder_start_y + index * (placeholder_button_h + placeholder_gap),
                    placeholder_button_w,
                    placeholder_button_h,
                ),
                label,
                info_font,
            )
            for index, label in enumerate(labels)
        ]

    electronics_workshop_modules = build_placeholder_modules()
    telecom_workshop_modules = build_placeholder_modules(["Simulador telecomunicaciones"])
    cyber_workshop_modules = build_placeholder_modules(["Proteccion del servidor"])

    state = STATE_MENU
    current_background = backgrounds[state]

    running = True
    while running:
        mouse_pos = to_virtual_pos(pygame.mouse.get_pos(), display_surface)

        if state == STATE_MENU:
            for button in (explore_button, exit_button):
                button.update_hover(mouse_pos)
        elif state == STATE_EXPLORE_1:
            left_back.update_hover(mouse_pos)
            right_next.update_hover(mouse_pos)
        elif state == STATE_EXPLORE_2:
            for button in explore_2_workshops:
                button.update_hover(mouse_pos)
            right_back.update_hover(mouse_pos)
        elif state == STATE_WORKSHOP_ELECTRIC:
            electric_workshop_back.update_hover(mouse_pos)
            for button in electric_workshop_modules:
                button.update_hover(mouse_pos)
        elif state == STATE_WORKSHOP_ELECTRONICS:
            electric_workshop_back.update_hover(mouse_pos)
            for button in electronics_workshop_modules:
                button.update_hover(mouse_pos)
        elif state == STATE_WORKSHOP_TELECOM:
            electric_workshop_back.update_hover(mouse_pos)
            for button in telecom_workshop_modules:
                button.update_hover(mouse_pos)
        elif state == STATE_WORKSHOP_CYBER:
            electric_workshop_back.update_hover(mouse_pos)
            for button in cyber_workshop_modules:
                button.update_hover(mouse_pos)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if state in (
                    STATE_WORKSHOP_ELECTRIC,
                    STATE_WORKSHOP_ELECTRONICS,
                    STATE_WORKSHOP_TELECOM,
                    STATE_WORKSHOP_CYBER,
                ):
                    target_state = STATE_EXPLORE_2
                elif state == STATE_EXPLORE_2:
                    target_state = STATE_EXPLORE_1
                elif state == STATE_EXPLORE_1:
                    target_state = STATE_MENU
                else:
                    target_state = None

                if target_state:
                    target_background = backgrounds[target_state]
                    fade_transition(display_surface, screen, clock, current_background, target_background, TRANSITION_MS)
                    state = target_state
                    current_background = target_background

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = to_virtual_pos(event.pos, display_surface)
                if state == STATE_MENU:
                    if explore_button.is_clicked(click_pos):
                        target_state = STATE_EXPLORE_1
                        target_background = backgrounds[target_state]
                        fade_transition(display_surface, screen, clock, current_background, target_background, TRANSITION_MS)
                        state = target_state
                        current_background = target_background
                    elif exit_button.is_clicked(click_pos):
                        running = False

                elif state == STATE_EXPLORE_1:
                    if left_back.is_clicked(click_pos):
                        target_state = STATE_MENU
                        target_background = backgrounds[target_state]
                        fade_transition(display_surface, screen, clock, current_background, target_background, TRANSITION_MS)
                        state = target_state
                        current_background = target_background
                    elif right_next.is_clicked(click_pos):
                        target_state = STATE_EXPLORE_2
                        target_background = backgrounds[target_state]
                        fade_transition(display_surface, screen, clock, current_background, target_background, TRANSITION_MS)
                        state = target_state
                        current_background = target_background

                elif state == STATE_EXPLORE_2:
                    if right_back.is_clicked(click_pos):
                        target_state = STATE_EXPLORE_1
                        target_background = backgrounds[target_state]
                        fade_transition(display_surface, screen, clock, current_background, target_background, TRANSITION_MS)
                        state = target_state
                        current_background = target_background
                    elif workshop_electric.is_clicked(click_pos):
                        target_state = STATE_WORKSHOP_ELECTRIC
                        target_background = backgrounds[target_state]
                        fade_transition(display_surface, screen, clock, current_background, target_background, TRANSITION_MS)
                        state = target_state
                        current_background = target_background
                    elif workshop_electronics.is_clicked(click_pos):
                        target_state = STATE_WORKSHOP_ELECTRONICS
                        target_background = backgrounds[target_state]
                        fade_transition(display_surface, screen, clock, current_background, target_background, TRANSITION_MS)
                        state = target_state
                        current_background = target_background
                    elif workshop_telecom.is_clicked(click_pos):
                        target_state = STATE_WORKSHOP_TELECOM
                        target_background = backgrounds[target_state]
                        fade_transition(display_surface, screen, clock, current_background, target_background, TRANSITION_MS)
                        state = target_state
                        current_background = target_background
                    elif workshop_cyber.is_clicked(click_pos):
                        target_state = STATE_WORKSHOP_CYBER
                        target_background = backgrounds[target_state]
                        fade_transition(display_surface, screen, clock, current_background, target_background, TRANSITION_MS)
                        state = target_state
                        current_background = target_background

                elif state == STATE_WORKSHOP_ELECTRIC:
                    if electric_workshop_back.is_clicked(click_pos):
                        target_state = STATE_EXPLORE_2
                        target_background = backgrounds[target_state]
                        fade_transition(display_surface, screen, clock, current_background, target_background, TRANSITION_MS)
                        state = target_state
                        current_background = target_background
                    elif electric_workshop_modules[0].is_clicked(click_pos):
                        launch_external_script(base_path, "electrica.py", display_mode)
                    elif electric_workshop_modules[1].is_clicked(click_pos):
                        launch_external_script(base_path, "maquina electrica.py", display_mode)
                    elif electric_workshop_modules[2].is_clicked(click_pos):
                        launch_external_script(base_path, "control_industrial.py", display_mode)
                    elif electric_workshop_modules[3].is_clicked(click_pos):
                        launch_external_script(base_path, "energia_solar.py", display_mode)
                    elif electric_workshop_modules[4].is_clicked(click_pos):
                        launch_external_script(base_path, "circuito electrico.py", display_mode)
                elif state == STATE_WORKSHOP_ELECTRONICS:
                    if electric_workshop_back.is_clicked(click_pos):
                        target_state = STATE_EXPLORE_2
                        target_background = backgrounds[target_state]
                        fade_transition(display_surface, screen, clock, current_background, target_background, TRANSITION_MS)
                        state = target_state
                        current_background = target_background
                    elif electronics_workshop_modules[0].is_clicked(click_pos):
                        launch_external_script(base_path, "mainAC.py", display_mode)
                    elif electronics_workshop_modules[1].is_clicked(click_pos):
                        launch_external_script(base_path, "mainPR.py", display_mode)
                elif state == STATE_WORKSHOP_TELECOM:
                    if electric_workshop_back.is_clicked(click_pos):
                        target_state = STATE_EXPLORE_2
                        target_background = backgrounds[target_state]
                        fade_transition(display_surface, screen, clock, current_background, target_background, TRANSITION_MS)
                        state = target_state
                        current_background = target_background
                    elif telecom_workshop_modules[0].is_clicked(click_pos):
                        launch_external_script(base_path, "teleco.py", display_mode)
                elif state == STATE_WORKSHOP_CYBER:
                    if electric_workshop_back.is_clicked(click_pos):
                        target_state = STATE_EXPLORE_2
                        target_background = backgrounds[target_state]
                        fade_transition(display_surface, screen, clock, current_background, target_background, TRANSITION_MS)
                        state = target_state
                        current_background = target_background
                    elif cyber_workshop_modules[0].is_clicked(click_pos):
                        launch_external_script(base_path, "ciber.py", display_mode)

        screen.blit(current_background, (0, 0))

        if state == STATE_MENU:
            overlay = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 75))
            screen.blit(overlay, (0, 0))

            draw_title(screen, title_font)
            explore_button.draw(screen)
            exit_button.draw(screen)

            info = info_font.render(f"Fondo principal: {menu_name}", True, (240, 248, 255))
            screen.blit(info, (18, 18))

        elif state == STATE_EXPLORE_1:
            left_back.draw(screen)
            right_next.draw(screen)

        elif state == STATE_EXPLORE_2:
            for button in explore_2_workshops:
                button.draw(screen)
            right_back.draw(screen)

        elif state == STATE_WORKSHOP_ELECTRIC:
            overlay = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
            overlay.fill((2, 10, 22, 80))
            screen.blit(overlay, (0, 0))

            title = button_font.render("Taller de electrica", True, (245, 251, 255))
            screen.blit(title, title.get_rect(center=(WINDOW_SIZE[0] // 2, 90)))

            for button in electric_workshop_modules:
                button.draw(screen)
            electric_workshop_back.draw(screen)
        elif state == STATE_WORKSHOP_ELECTRONICS:
            overlay = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
            overlay.fill((2, 10, 22, 80))
            screen.blit(overlay, (0, 0))

            title = button_font.render("Taller de electronica", True, (245, 251, 255))
            screen.blit(title, title.get_rect(center=(WINDOW_SIZE[0] // 2, 90)))

            for button in electronics_workshop_modules:
                button.draw(screen)
            electric_workshop_back.draw(screen)
        elif state == STATE_WORKSHOP_TELECOM:
            overlay = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
            overlay.fill((2, 10, 22, 80))
            screen.blit(overlay, (0, 0))

            title = button_font.render("Taller de telecomunicaciones", True, (245, 251, 255))
            screen.blit(title, title.get_rect(center=(WINDOW_SIZE[0] // 2, 90)))

            for button in telecom_workshop_modules:
                button.draw(screen)
            electric_workshop_back.draw(screen)
        elif state == STATE_WORKSHOP_CYBER:
            overlay = pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)
            overlay.fill((2, 10, 22, 80))
            screen.blit(overlay, (0, 0))

            title = button_font.render("Taller de ciberseguridad", True, (245, 251, 255))
            screen.blit(title, title.get_rect(center=(WINDOW_SIZE[0] // 2, 90)))

            for button in cyber_workshop_modules:
                button.draw(screen)
            electric_workshop_back.draw(screen)

        present_frame(display_surface, screen)
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
