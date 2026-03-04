import math
import sys
from collections import deque

import pygame
from display_mode import apply_display_mode


pygame.init()


WIDTH, HEIGHT = 1400, 800
WINDOW_SIZE = (1280, 720)
FPS = 60
GRID = 20


C_BG = (20, 24, 30)
C_GRID = (34, 40, 50)
C_PANEL = (40, 47, 58)
C_PANEL_EDGE = (100, 110, 130)
C_TEXT = (225, 230, 240)
C_DIM = (150, 158, 175)
C_WIRE_IDLE = (120, 126, 136)
C_L = (245, 92, 92)
C_N = (100, 175, 250)
C_PE = (105, 205, 125)
C_FAULT = (255, 195, 70)
C_PREVIEW = (255, 245, 170)


def snap_point(pos):
    return (round(pos[0] / GRID) * GRID, round(pos[1] / GRID) * GRID)


def manhattan_path(start, end, mode):
    if mode == "HV":
        mid = (end[0], start[1])
    else:
        mid = (start[0], end[1])

    pts = [start]
    if mid != start and mid != end:
        pts.append(mid)
    if end != pts[-1]:
        pts.append(end)
    return pts


def simplify_polyline(points):
    if not points:
        return []

    compact = [points[0]]
    for p in points[1:]:
        if p != compact[-1]:
            compact.append(p)

    if len(compact) < 3:
        return compact

    result = [compact[0]]
    for i in range(1, len(compact) - 1):
        a = result[-1]
        b = compact[i]
        c = compact[i + 1]
        collinear = (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1])
        if not collinear:
            result.append(b)
    result.append(compact[-1])
    return result


def signal_color(tags):
    if "L" in tags and ("N" in tags or "PE" in tags):
        return C_FAULT
    if "L" in tags:
        return C_L
    if "N" in tags:
        return C_N
    if "PE" in tags:
        return C_PE
    return C_WIRE_IDLE


def draw_grid(surface):
    surface.fill(C_BG)
    for x in range(0, WIDTH, GRID):
        pygame.draw.line(surface, C_GRID, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, GRID):
        pygame.draw.line(surface, C_GRID, (0, y), (WIDTH, y), 1)


class Terminal:
    def __init__(self, key, pos, tag="", radius=8):
        self.key = key
        self.pos = snap_point(pos)
        self.tag = tag
        self.radius = radius

    def hit_test(self, pos):
        return math.dist(self.pos, pos) <= self.radius + 6

    def draw(self, surface, font, tags_by_key):
        tags = tags_by_key.get(self.key, set())
        color = signal_color(tags)
        pygame.draw.circle(surface, C_BG, self.pos, self.radius + 4)
        pygame.draw.circle(surface, color, self.pos, self.radius)
        pygame.draw.circle(surface, C_TEXT, self.pos, self.radius, 1)
        if self.tag:
            lbl = font.render(self.tag, True, C_TEXT)
            surface.blit(lbl, (self.pos[0] + 10, self.pos[1] - 8))


class Wire:
    def __init__(self, start_terminal, end_terminal, points):
        self.start = start_terminal
        self.end = end_terminal
        self.points = simplify_polyline(points)

    def draw(self, surface, tags_by_key):
        tags = tags_by_key.get(self.start.key, set()) | tags_by_key.get(self.end.key, set())
        color = signal_color(tags)
        if len(self.points) >= 2:
            pygame.draw.lines(surface, color, False, self.points, 4)
            for p in self.points[1:-1]:
                pygame.draw.circle(surface, color, p, 3)

    def hit_test(self, pos, tolerance=6):
        px, py = pos
        if len(self.points) < 2:
            return False
        for i in range(len(self.points) - 1):
            (x1, y1), (x2, y2) = self.points[i], self.points[i + 1]
            if x1 == x2:
                if abs(px - x1) <= tolerance and min(y1, y2) - tolerance <= py <= max(y1, y2) + tolerance:
                    return True
            elif y1 == y2:
                if abs(py - y1) <= tolerance and min(x1, x2) - tolerance <= px <= max(x1, x2) + tolerance:
                    return True
        return False


class WireBuilder:
    def __init__(self):
        self.active = False
        self.start_terminal = None
        self.points = []
        self.mode = "HV"

    def begin(self, terminal):
        self.active = True
        self.start_terminal = terminal
        self.points = [terminal.pos]

    def cancel(self):
        self.active = False
        self.start_terminal = None
        self.points = []

    def toggle_mode(self):
        self.mode = "VH" if self.mode == "HV" else "HV"

    def undo_anchor(self):
        if len(self.points) > 1:
            self.points.pop()

    def _path_to(self, pos):
        if not self.active:
            return []
        last = self.points[-1]
        target = snap_point(pos)
        return manhattan_path(last, target, self.mode)

    def preview_points(self, pos):
        if not self.active:
            return []
        path = self._path_to(pos)
        return simplify_polyline(self.points + path[1:])

    def add_anchor(self, pos):
        if not self.active:
            return
        path = self._path_to(pos)
        for p in path[1:]:
            if p != self.points[-1]:
                self.points.append(p)
        self.points = simplify_polyline(self.points)

    def finish(self, end_terminal):
        if not self.active or end_terminal.key == self.start_terminal.key:
            self.cancel()
            return None
        path = manhattan_path(self.points[-1], end_terminal.pos, self.mode)
        all_points = simplify_polyline(self.points + path[1:])
        wire = Wire(self.start_terminal, end_terminal, all_points)
        self.cancel()
        return wire

    def draw(self, surface, mouse_pos):
        if not self.active:
            return
        for p in self.points:
            pygame.draw.circle(surface, C_PREVIEW, p, 3)
        preview = self.preview_points(mouse_pos)
        if len(preview) >= 2:
            pygame.draw.lines(surface, C_PREVIEW, False, preview, 2)


class Breaker:
    def __init__(self, rect, t_in, t_out):
        self.rect = pygame.Rect(rect)
        self.t_in = t_in
        self.t_out = t_out
        self.closed = False

    def toggle(self):
        self.closed = not self.closed

    def draw(self, surface, font):
        pygame.draw.rect(surface, (55, 64, 76), self.rect, border_radius=8)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=8)

        left_pin = (self.rect.left + 20, self.rect.centery)
        right_pin = (self.rect.right - 20, self.rect.centery)
        if self.closed:
            lever_end = right_pin
            lever_color = C_PE
        else:
            lever_end = (self.rect.centerx + 25, self.rect.top + 18)
            lever_color = C_L
        pygame.draw.line(surface, lever_color, left_pin, lever_end, 5)

        txt = "ON" if self.closed else "OFF"
        lbl = font.render(f"Breaker {txt}", True, C_TEXT)
        surface.blit(lbl, (self.rect.left + 16, self.rect.bottom + 8))


class WallSwitch:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 190, 100)
        self.t_in = Terminal("wall_sw_in", (x - 26, y + 50), "SW-IN")
        self.t_out = Terminal("wall_sw_out", (x + 216, y + 50), "SW-OUT")
        self.closed = False

    def terminals(self):
        return [self.t_in, self.t_out]

    def toggle(self):
        self.closed = not self.closed

    def draw(self, surface, font_title, font_small, tags_by_key):
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=10)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=10)

        title = font_title.render("INTERRUPTOR PARED", True, C_TEXT)
        surface.blit(title, (self.rect.x + 14, self.rect.y + 14))

        left_pin = (self.rect.left + 22, self.rect.y + 58)
        right_pin = (self.rect.right - 22, self.rect.y + 58)
        if self.closed:
            lever_end = right_pin
            lever_color = C_PE
            state_txt = "ON"
        else:
            lever_end = (self.rect.centerx + 18, self.rect.y + 30)
            lever_color = C_L
            state_txt = "OFF"

        pygame.draw.line(surface, C_DIM, (self.t_in.pos[0] + 10, self.t_in.pos[1]), left_pin, 3)
        pygame.draw.line(surface, C_DIM, right_pin, (self.t_out.pos[0] - 10, self.t_out.pos[1]), 3)
        pygame.draw.line(surface, lever_color, left_pin, lever_end, 5)

        state_label = font_small.render(f"Estado: {state_txt}", True, C_TEXT)
        surface.blit(state_label, (self.rect.x + 14, self.rect.y + 74))

        self.t_in.draw(surface, font_small, tags_by_key)
        self.t_out.draw(surface, font_small, tags_by_key)


class SourceUnit:
    def __init__(self, x, y, title, subtitle, role, key):
        self.rect = pygame.Rect(x, y, 240, 92)
        self.title = title
        self.subtitle = subtitle
        self.role = role
        self.terminal = Terminal(key, (x + 266, y + 46), role)

    def draw(self, surface, font_title, font_small, tags_by_key):
        color = signal_color({self.role})
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=10)
        pygame.draw.rect(surface, color, self.rect, 2, border_radius=10)

        t1 = font_title.render(self.title, True, C_TEXT)
        t2 = font_small.render(self.subtitle, True, C_DIM)
        surface.blit(t1, (self.rect.x + 14, self.rect.y + 14))
        surface.blit(t2, (self.rect.x + 14, self.rect.y + 48))

        pygame.draw.line(
            surface,
            color,
            (self.rect.right - 10, self.rect.centery),
            (self.terminal.pos[0] - 10, self.terminal.pos[1]),
            3,
        )
        self.terminal.draw(surface, font_small, tags_by_key)


class PanelBoard:
    def __init__(self):
        self.rect = pygame.Rect(320, 80, 560, 620)
        self.t_l_in = Terminal("panel_l_in", (400, 190), "L-IN")
        self.t_l_out = Terminal("panel_l_out", (790, 190), "L-OUT")
        self.t_n_bar = Terminal("panel_n", (790, 330), "N-BAR")
        self.t_pe_bar = Terminal("panel_pe", (790, 470), "PE-BAR")
        self.breaker = Breaker((520, 145, 170, 78), self.t_l_in, self.t_l_out)

    def terminals(self):
        return [self.t_l_in, self.t_l_out, self.t_n_bar, self.t_pe_bar]

    def draw(self, surface, font_title, font_small, tags_by_key):
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=14)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=14)

        title = font_title.render("TABLERO ELECTRICO DOMICILIARIO", True, C_TEXT)
        surface.blit(title, (self.rect.x + 20, self.rect.y + 16))

        line_y = self.rect.y + 64
        pygame.draw.line(surface, C_PANEL_EDGE, (self.rect.x + 18, line_y), (self.rect.right - 18, line_y), 1)

        pygame.draw.line(surface, C_DIM, (self.t_l_in.pos[0], self.t_l_in.pos[1]), (self.breaker.rect.left, self.breaker.rect.centery), 3)
        pygame.draw.line(surface, C_DIM, (self.breaker.rect.right, self.breaker.rect.centery), (self.t_l_out.pos[0], self.t_l_out.pos[1]), 3)

        n_bar_start = (620, self.t_n_bar.pos[1])
        pe_bar_start = (620, self.t_pe_bar.pos[1])
        pygame.draw.line(surface, C_N, n_bar_start, self.t_n_bar.pos, 6)
        pygame.draw.line(surface, C_PE, pe_bar_start, self.t_pe_bar.pos, 6)

        lbl_n = font_small.render("Barra neutral", True, C_DIM)
        lbl_pe = font_small.render("Barra de tierra", True, C_DIM)
        surface.blit(lbl_n, (560, self.t_n_bar.pos[1] - 24))
        surface.blit(lbl_pe, (560, self.t_pe_bar.pos[1] - 24))

        self.breaker.draw(surface, font_small)
        for t in self.terminals():
            t.draw(surface, font_small, tags_by_key)


class LampLoad:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 320, 300)
        self.t_l = Terminal("lamp_l", (x, y + 98), "L")
        self.t_n = Terminal("lamp_n", (x, y + 146), "N")

    def terminals(self):
        return [self.t_l, self.t_n]

    def draw(self, surface, font_title, font_small, tags_by_key, on):
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=12)

        lbl = font_title.render("FOCO", True, C_TEXT)
        surface.blit(lbl, (self.rect.x + 18, self.rect.y + 16))

        center = (self.rect.x + 220, self.rect.y + 105)
        if on:
            glow = pygame.Surface((180, 180), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 240, 170, 50), (90, 90), 80)
            pygame.draw.circle(glow, (255, 240, 170, 90), (90, 90), 50)
            surface.blit(glow, (center[0] - 90, center[1] - 90))
            bulb_color = (255, 240, 170)
        else:
            bulb_color = (70, 70, 55)
        pygame.draw.circle(surface, bulb_color, center, 28)
        pygame.draw.circle(surface, C_TEXT, center, 28, 2)
        pygame.draw.rect(surface, (120, 120, 125), (center[0] - 12, center[1] + 24, 24, 15))

        self.t_l.draw(surface, font_small, tags_by_key)
        self.t_n.draw(surface, font_small, tags_by_key)


class OutletLoad:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 320, 240)
        self.t_l = Terminal("outlet_l", (x, y + 76), "L")
        self.t_n = Terminal("outlet_n", (x, y + 132), "N")
        self.t_pe = Terminal("outlet_pe", (x, y + 188), "PE")

    def terminals(self):
        return [self.t_l, self.t_n, self.t_pe]

    def draw(self, surface, font_title, font_small, tags_by_key, powered, grounded):
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=12)

        lbl = font_title.render("ENCHUFE", True, C_TEXT)
        surface.blit(lbl, (self.rect.x + 18, self.rect.y + 16))

        face = pygame.Rect(self.rect.x + 182, self.rect.y + 52, 112, 138)
        face_color = (215, 220, 225) if powered else (150, 155, 165)
        pygame.draw.rect(surface, face_color, face, border_radius=16)
        pygame.draw.rect(surface, (90, 95, 105), face, 2, border_radius=16)

        pygame.draw.rect(surface, (70, 75, 82), (face.x + 28, face.y + 36, 12, 36), border_radius=4)
        pygame.draw.rect(surface, (70, 75, 82), (face.x + 72, face.y + 36, 12, 36), border_radius=4)
        pe_color = C_PE if grounded else (90, 95, 105)
        pygame.draw.circle(surface, pe_color, (face.centerx, face.y + 102), 9, 3)

        self.t_l.draw(surface, font_small, tags_by_key)
        self.t_n.draw(surface, font_small, tags_by_key)
        self.t_pe.draw(surface, font_small, tags_by_key)


def find_terminal_at(pos, terminals):
    for t in terminals:
        if t.hit_test(pos):
            return t
    return None


def pop_wire_at(pos, wires):
    for i in range(len(wires) - 1, -1, -1):
        if wires[i].hit_test(pos):
            wires.pop(i)
            return True
    return False


def reachable(adj, start_key):
    if start_key not in adj:
        return set()
    visited = {start_key}
    queue = deque([start_key])
    while queue:
        node = queue.popleft()
        for nxt in adj[node]:
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    return visited


def has_path(adj, start_key, target_key):
    return target_key in reachable(adj, start_key)


def analyze_network(terminals, wires, panel, wall_switch, sources, lamp, outlet):
    keys = [t.key for t in terminals]
    adj = {k: set() for k in keys}

    for w in wires:
        a, b = w.start.key, w.end.key
        adj[a].add(b)
        adj[b].add(a)

    if panel.breaker.closed:
        a, b = panel.t_l_in.key, panel.t_l_out.key
        adj[a].add(b)
        adj[b].add(a)

    if wall_switch.closed:
        a, b = wall_switch.t_in.key, wall_switch.t_out.key
        adj[a].add(b)
        adj[b].add(a)

    reach = {role: reachable(adj, sources[role].key) for role in sources}

    tags_by_key = {k: set() for k in keys}
    for role, nodes in reach.items():
        for node in nodes:
            tags_by_key[node].add(role)

    short_ln = sources["N"].key in reach["L"]
    short_lpe = sources["PE"].key in reach["L"]
    fault = short_ln or short_lpe

    lamp_on = ("L" in tags_by_key[lamp.t_l.key]) and ("N" in tags_by_key[lamp.t_n.key]) and not fault
    outlet_powered = ("L" in tags_by_key[outlet.t_l.key]) and ("N" in tags_by_key[outlet.t_n.key]) and not fault
    outlet_grounded = "PE" in tags_by_key[outlet.t_pe.key]

    checks = [
        ("Fase a L-IN", has_path(adj, sources["L"].key, panel.t_l_in.key)),
        ("Neutro a N-BAR", has_path(adj, sources["N"].key, panel.t_n_bar.key)),
        ("Tierra a PE-BAR", has_path(adj, sources["PE"].key, panel.t_pe_bar.key)),
        ("L-OUT a switch", has_path(adj, panel.t_l_out.key, wall_switch.t_in.key)),
        ("Switch a foco", has_path(adj, wall_switch.t_out.key, lamp.t_l.key)),
        ("N-BAR a foco", has_path(adj, panel.t_n_bar.key, lamp.t_n.key)),
        ("L-OUT a enchufe", has_path(adj, panel.t_l_out.key, outlet.t_l.key)),
        ("N-BAR a enchufe", has_path(adj, panel.t_n_bar.key, outlet.t_n.key)),
        ("PE-BAR a enchufe", has_path(adj, panel.t_pe_bar.key, outlet.t_pe.key)),
    ]

    done_install = all(v for _, v in checks)
    return {
        "tags": tags_by_key,
        "fault": fault,
        "short_ln": short_ln,
        "short_lpe": short_lpe,
        "lamp_on": lamp_on,
        "outlet_powered": outlet_powered,
        "outlet_grounded": outlet_grounded,
        "checks": checks,
        "done_install": done_install,
    }


def draw_status_panel(surface, font_title, font_small, info, builder, wire_count):
    box = pygame.Rect(16, HEIGHT - 244, WIDTH - 32, 220)
    panel_bg = pygame.Surface((box.w, box.h), pygame.SRCALPHA)
    panel_bg.fill((26, 31, 39, 190))
    surface.blit(panel_bg, box.topleft)
    pygame.draw.rect(surface, C_PANEL_EDGE, box, 2, border_radius=12)
    title_step = font_title.get_linesize() + 4
    line_step = font_small.get_linesize() + 3

    left_x = box.x + 16
    y = box.y + 12
    title = font_title.render("Controles", True, C_TEXT)
    surface.blit(title, (left_x, y))
    y += title_step
    controls = [
        "Click izq en terminal: iniciar/finalizar cable",
        "Click izq en vacio: fijar esquina (estilo Proteus)",
        "R: cambia orientacion HV/VH",
        "Backspace: quita ultima esquina | C: limpiar cables",
        "Click der: cancelar trazado o borrar cable",
        "Click en breaker, o en interruptor pared, para ON/OFF",
    ]
    for line in controls:
        txt = font_small.render(line, True, C_DIM)
        surface.blit(txt, (left_x, y))
        y += line_step

    mid_x = box.x + 540
    y = box.y + 12
    title2 = font_title.render("Chequeo de conexion", True, C_TEXT)
    surface.blit(title2, (mid_x, y))
    y += title_step
    for label, ok in info["checks"]:
        color = C_PE if ok else C_DIM
        prefix = "[OK]" if ok else "[  ]"
        txt = font_small.render(f"{prefix} {label}", True, color)
        surface.blit(txt, (mid_x, y))
        y += line_step

    right_x = box.right - 330
    y = box.y + 12
    title3 = font_title.render("Estado", True, C_TEXT)
    surface.blit(title3, (right_x, y))
    y += title_step

    mode_txt = f"Modo cable: {builder.mode} | cables: {wire_count}"
    surface.blit(font_small.render(mode_txt, True, C_DIM), (right_x, y))
    y += line_step

    foco = "Foco: ENCENDIDO" if info["lamp_on"] else "Foco: apagado"
    enchufe = "Enchufe: energizado" if info["outlet_powered"] else "Enchufe: sin energia"
    tierra = "Tierra enchufe: conectada" if info["outlet_grounded"] else "Tierra enchufe: no conectada"
    surface.blit(font_small.render(foco, True, C_TEXT), (right_x, y))
    y += line_step
    surface.blit(font_small.render(enchufe, True, C_TEXT), (right_x, y))
    y += line_step
    surface.blit(font_small.render(tierra, True, C_TEXT), (right_x, y))
    y += line_step

    if info["fault"]:
        warning = "ALERTA: posible corto (L con N o PE)"
        surface.blit(font_small.render(warning, True, C_FAULT), (right_x, y))
    else:
        if info["done_install"] and info["lamp_on"] and info["outlet_powered"] and info["outlet_grounded"]:
            ok_msg = "Instalacion funcional completa"
            surface.blit(font_small.render(ok_msg, True, C_PE), (right_x, y))


def setup_fullscreen():
    screen = apply_display_mode(WINDOW_SIZE)
    screen_size = screen.get_size()
    scale = min(screen_size[0] / WIDTH, screen_size[1] / HEIGHT)
    render_size = (int(WIDTH * scale), int(HEIGHT * scale))
    offset = ((screen_size[0] - render_size[0]) // 2, (screen_size[1] - render_size[1]) // 2)
    return screen, render_size, offset


def screen_to_world(pos, render_size, offset):
    x, y = pos
    ox, oy = offset
    rw, rh = render_size
    if not (ox <= x < ox + rw and oy <= y < oy + rh):
        return None
    return (int((x - ox) * WIDTH / rw), int((y - oy) * HEIGHT / rh))


def run_simulator():
    screen, render_size, offset = setup_fullscreen()
    world = pygame.Surface((WIDTH, HEIGHT))
    pygame.display.set_caption("Simulador de tablero electrico 2D")
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("consolas", 20, bold=True)
    font_small = pygame.font.SysFont("consolas", 15)
    font_status_title = pygame.font.SysFont("consolas", 17, bold=True)
    font_status_small = pygame.font.SysFont("consolas", 12)

    source_l = SourceUnit(24, 120, "ALIMENTADOR 1", "Fase (L)", "L", "src_l")
    source_n = SourceUnit(24, 248, "ALIMENTADOR 2", "Neutro (N)", "N", "src_n")
    source_pe = SourceUnit(24, 376, "PUESTA A TIERRA", "Conectar manualmente", "PE", "src_pe")

    panel = PanelBoard()
    wall_switch = WallSwitch(600, 400)
    lamp = LampLoad(980, 120)
    outlet = OutletLoad(980, 360)

    terminals = [
        source_l.terminal,
        source_n.terminal,
        source_pe.terminal,
        *panel.terminals(),
        *wall_switch.terminals(),
        *lamp.terminals(),
        *outlet.terminals(),
    ]

    sources = {
        "L": source_l.terminal,
        "N": source_n.terminal,
        "PE": source_pe.terminal,
    }

    wires = []
    builder = WireBuilder()

    running = True
    while running:
        mouse_world = screen_to_world(pygame.mouse.get_pos(), render_size, offset)
        mouse_pos = mouse_world if mouse_world else (-10000, -10000)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    builder.toggle_mode()
                elif event.key == pygame.K_c:
                    wires.clear()
                elif event.key == pygame.K_b:
                    panel.breaker.toggle()
                elif event.key == pygame.K_BACKSPACE:
                    builder.undo_anchor()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = screen_to_world(event.pos, render_size, offset)
                if pos is None:
                    continue
                hit_terminal = find_terminal_at(pos, terminals)

                if event.button == 1:
                    if panel.breaker.rect.collidepoint(pos):
                        panel.breaker.toggle()
                    elif wall_switch.rect.collidepoint(pos):
                        wall_switch.toggle()
                    elif builder.active:
                        if hit_terminal and hit_terminal.key != builder.start_terminal.key:
                            new_wire = builder.finish(hit_terminal)
                            if new_wire:
                                wires.append(new_wire)
                        else:
                            builder.add_anchor(pos)
                    else:
                        if hit_terminal:
                            builder.begin(hit_terminal)

                elif event.button == 3:
                    if builder.active:
                        builder.cancel()
                    else:
                        pop_wire_at(pos, wires)

        info = analyze_network(terminals, wires, panel, wall_switch, sources, lamp, outlet)

        draw_grid(world)

        source_l.draw(world, font_title, font_small, info["tags"])
        source_n.draw(world, font_title, font_small, info["tags"])
        source_pe.draw(world, font_title, font_small, info["tags"])
        panel.draw(world, font_title, font_small, info["tags"])
        wall_switch.draw(world, font_title, font_small, info["tags"])
        lamp.draw(world, font_title, font_small, info["tags"], info["lamp_on"])
        outlet.draw(world, font_title, font_small, info["tags"], info["outlet_powered"], info["outlet_grounded"])

        for w in wires:
            w.draw(world, info["tags"])

        builder.draw(world, mouse_pos)

        draw_status_panel(world, font_status_title, font_status_small, info, builder, len(wires))

        screen.fill(C_BG)
        scaled = pygame.transform.smoothscale(world, render_size)
        screen.blit(scaled, offset)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run_simulator()
