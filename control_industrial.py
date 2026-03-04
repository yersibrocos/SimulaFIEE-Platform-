import math
import sys
from collections import deque

import pygame
from display_mode import apply_display_mode


pygame.init()


WIDTH, HEIGHT = 1500, 800
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


class PowerSource220V:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 250, 220)
        self.t_l = Terminal("src_l", (x + 276, y + 64), "L")
        self.t_n = Terminal("src_n", (x + 276, y + 112), "N")
        self.t_pe = Terminal("src_pe", (x + 276, y + 160), "PE")

    def terminals(self):
        return [self.t_l, self.t_n, self.t_pe]

    def draw(self, surface, font_title, font_small, tags_by_key):
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=12)

        title = font_title.render("ALIMENTACION 220V", True, C_TEXT)
        sub = font_small.render("Fuente simulada L + N + PE", True, C_DIM)
        surface.blit(title, (self.rect.x + 14, self.rect.y + 14))
        surface.blit(sub, (self.rect.x + 14, self.rect.y + 42))

        pygame.draw.line(
            surface, C_L, (self.rect.right - 12, self.t_l.pos[1]), (self.t_l.pos[0] - 10, self.t_l.pos[1]), 3
        )
        pygame.draw.line(
            surface, C_N, (self.rect.right - 12, self.t_n.pos[1]), (self.t_n.pos[0] - 10, self.t_n.pos[1]), 3
        )
        pygame.draw.line(
            surface, C_PE, (self.rect.right - 12, self.t_pe.pos[1]), (self.t_pe.pos[0] - 10, self.t_pe.pos[1]), 3
        )

        self.t_l.draw(surface, font_small, tags_by_key)
        self.t_n.draw(surface, font_small, tags_by_key)
        self.t_pe.draw(surface, font_small, tags_by_key)


class NetworkAnalyzer:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 300, 250)
        self.t_l_in = Terminal("an_l_in", (x - 26, y + 84), "L_in")
        self.t_n_in = Terminal("an_n_in", (x - 26, y + 140), "N_in")
        self.t_l_out = Terminal("an_l_out", (x + 326, y + 84), "L_out")
        self.t_n_out = Terminal("an_n_out", (x + 326, y + 140), "N_out")
        self.screen = pygame.Rect(x + 20, y + 44, 260, 118)

    def terminals(self):
        return [self.t_l_in, self.t_n_in, self.t_l_out, self.t_n_out]

    def draw(self, surface, font_title, font_small, tags_by_key, meter):
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=12)

        title = font_title.render("ANALIZADOR DE REDES", True, C_TEXT)
        surface.blit(title, (self.rect.x + 14, self.rect.y + 14))

        pygame.draw.line(
            surface, C_DIM, (self.t_l_in.pos[0] + 10, self.t_l_in.pos[1]), (self.rect.x + 8, self.t_l_in.pos[1]), 3
        )
        pygame.draw.line(
            surface, C_DIM, (self.t_n_in.pos[0] + 10, self.t_n_in.pos[1]), (self.rect.x + 8, self.t_n_in.pos[1]), 3
        )
        pygame.draw.line(
            surface, C_DIM, (self.rect.right - 8, self.t_l_out.pos[1]), (self.t_l_out.pos[0] - 10, self.t_l_out.pos[1]), 3
        )
        pygame.draw.line(
            surface, C_DIM, (self.rect.right - 8, self.t_n_out.pos[1]), (self.t_n_out.pos[0] - 10, self.t_n_out.pos[1]), 3
        )

        pygame.draw.rect(surface, (13, 18, 24), self.screen, border_radius=8)
        pygame.draw.rect(surface, (74, 88, 104), self.screen, 2, border_radius=8)

        screen_color = C_PE if meter["powered"] else C_DIM
        lines = [
            f"V: {meter['voltage']}",
            f"F: {meter['frequency']}",
            f"I: {meter['current']}",
            f"P: {meter['power']}",
        ]
        for i, line in enumerate(lines):
            txt = font_small.render(line, True, screen_color)
            surface.blit(txt, (self.screen.x + 12, self.screen.y + 12 + i * 24))

        self.t_l_in.draw(surface, font_small, tags_by_key)
        self.t_n_in.draw(surface, font_small, tags_by_key)
        self.t_l_out.draw(surface, font_small, tags_by_key)
        self.t_n_out.draw(surface, font_small, tags_by_key)


class VFD:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 320, 270)
        self.t_l_in = Terminal("vfd_l_in", (x - 26, y + 84), "L_in")
        self.t_n_in = Terminal("vfd_n_in", (x - 26, y + 144), "N_in")
        self.t_u = Terminal("vfd_u", (x + 346, y + 94), "U")
        self.t_v = Terminal("vfd_v", (x + 346, y + 154), "V")
        self.set_freq = 0.0
        self.btn_plus = pygame.Rect(x + 246, y + 54, 44, 30)
        self.btn_minus = pygame.Rect(x + 246, y + 94, 44, 30)
        self.screen = pygame.Rect(x + 20, y + 54, 208, 110)

    def terminals(self):
        return [self.t_l_in, self.t_n_in, self.t_u, self.t_v]

    def change_setpoint(self, delta):
        self.set_freq = max(0.0, min(60.0, self.set_freq + delta))

    def handle_click(self, pos):
        if self.btn_plus.collidepoint(pos):
            self.change_setpoint(1.0)
            return True
        if self.btn_minus.collidepoint(pos):
            self.change_setpoint(-1.0)
            return True
        return False

    def draw(self, surface, font_title, font_small, tags_by_key, powered, output_hz):
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=12)

        title = font_title.render("VARIADOR DE FRECUENCIA (VFD)", True, C_TEXT)
        surface.blit(title, (self.rect.x + 14, self.rect.y + 14))

        pygame.draw.line(
            surface, C_DIM, (self.t_l_in.pos[0] + 10, self.t_l_in.pos[1]), (self.rect.x + 8, self.t_l_in.pos[1]), 3
        )
        pygame.draw.line(
            surface, C_DIM, (self.t_n_in.pos[0] + 10, self.t_n_in.pos[1]), (self.rect.x + 8, self.t_n_in.pos[1]), 3
        )
        pygame.draw.line(
            surface, C_DIM, (self.rect.right - 8, self.t_u.pos[1]), (self.t_u.pos[0] - 10, self.t_u.pos[1]), 3
        )
        pygame.draw.line(
            surface, C_DIM, (self.rect.right - 8, self.t_v.pos[1]), (self.t_v.pos[0] - 10, self.t_v.pos[1]), 3
        )

        pygame.draw.rect(surface, (13, 18, 24), self.screen, border_radius=8)
        pygame.draw.rect(surface, (74, 88, 104), self.screen, 2, border_radius=8)

        st_color = C_PE if powered else C_L
        state = "ON" if powered else "OFF"
        txt_state = font_small.render(f"Estado: {state}", True, st_color)
        txt_set = font_small.render(f"Set: {self.set_freq:>4.1f} Hz", True, C_TEXT)
        txt_out = font_small.render(f"Out: {output_hz:>4.1f} Hz", True, st_color)
        surface.blit(txt_state, (self.screen.x + 12, self.screen.y + 12))
        surface.blit(txt_set, (self.screen.x + 12, self.screen.y + 42))
        surface.blit(txt_out, (self.screen.x + 12, self.screen.y + 72))

        pygame.draw.rect(surface, (70, 82, 96), self.btn_plus, border_radius=6)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.btn_plus, 1, border_radius=6)
        pygame.draw.rect(surface, (70, 82, 96), self.btn_minus, border_radius=6)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.btn_minus, 1, border_radius=6)

        plus_lbl = font_title.render("+", True, C_TEXT)
        minus_lbl = font_title.render("-", True, C_TEXT)
        surface.blit(plus_lbl, (self.btn_plus.centerx - 7, self.btn_plus.y - 2))
        surface.blit(minus_lbl, (self.btn_minus.centerx - 5, self.btn_minus.y - 6))

        hint = font_small.render("Ajuste Hz", True, C_DIM)
        surface.blit(hint, (self.btn_minus.x - 2, self.btn_minus.bottom + 6))

        self.t_l_in.draw(surface, font_small, tags_by_key)
        self.t_n_in.draw(surface, font_small, tags_by_key)
        self.t_u.draw(surface, font_small, tags_by_key)
        self.t_v.draw(surface, font_small, tags_by_key)


class MotorLoad:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 280, 260)
        self.t_u = Terminal("motor_u", (x - 26, y + 100), "U")
        self.t_v = Terminal("motor_v", (x - 26, y + 160), "V")
        self.angle = 0.0

    def terminals(self):
        return [self.t_u, self.t_v]

    def update(self, dt, output_hz, running):
        if running and output_hz > 0.0:
            rpm = output_hz * 30.0
            deg_per_sec = rpm * 6.0
            self.angle = (self.angle + deg_per_sec * dt) % 360.0

    def draw(self, surface, font_title, font_small, tags_by_key, running, rpm):
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=12)

        title = font_title.render("MOTOR ELECTRICO", True, C_TEXT)
        surface.blit(title, (self.rect.x + 14, self.rect.y + 14))

        pygame.draw.line(
            surface, C_DIM, (self.t_u.pos[0] + 10, self.t_u.pos[1]), (self.rect.x + 8, self.t_u.pos[1]), 3
        )
        pygame.draw.line(
            surface, C_DIM, (self.t_v.pos[0] + 10, self.t_v.pos[1]), (self.rect.x + 8, self.t_v.pos[1]), 3
        )

        center = (self.rect.x + 185, self.rect.y + 132)
        outer = 62
        if running:
            glow = pygame.Surface((180, 180), pygame.SRCALPHA)
            pygame.draw.circle(glow, (110, 220, 140, 48), (90, 90), 72)
            surface.blit(glow, (center[0] - 90, center[1] - 90))
            rotor_color = C_PE
        else:
            rotor_color = (120, 130, 145)

        pygame.draw.circle(surface, (24, 28, 36), center, outer)
        pygame.draw.circle(surface, C_PANEL_EDGE, center, outer, 2)

        for i in range(3):
            ang = math.radians(self.angle + i * 120.0)
            tip = (center[0] + int(math.cos(ang) * 44), center[1] + int(math.sin(ang) * 44))
            pygame.draw.line(surface, rotor_color, center, tip, 6)
            pygame.draw.circle(surface, rotor_color, tip, 5)

        pygame.draw.circle(surface, C_TEXT, center, 9)
        rpm_txt = font_small.render(f"{rpm} RPM", True, C_TEXT)
        surface.blit(rpm_txt, (self.rect.x + 14, self.rect.y + 220))

        self.t_u.draw(surface, font_small, tags_by_key)
        self.t_v.draw(surface, font_small, tags_by_key)


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


def add_edge(adj, a, b):
    adj[a].add(b)
    adj[b].add(a)


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


def analyze_network(terminals, wires, source, analyzer, vfd, motor):
    keys = [t.key for t in terminals]
    adj_base = {k: set() for k in keys}

    for w in wires:
        add_edge(adj_base, w.start.key, w.end.key)

    add_edge(adj_base, analyzer.t_l_in.key, analyzer.t_l_out.key)
    add_edge(adj_base, analyzer.t_n_in.key, analyzer.t_n_out.key)

    reach_base = {
        "L": reachable(adj_base, source.t_l.key),
        "N": reachable(adj_base, source.t_n.key),
        "PE": reachable(adj_base, source.t_pe.key),
    }

    short_ln = source.t_n.key in reach_base["L"]
    short_lpe = source.t_pe.key in reach_base["L"]
    fault = short_ln or short_lpe

    chk_source_l_meter = has_path(adj_base, source.t_l.key, analyzer.t_l_in.key)
    chk_source_n_meter = has_path(adj_base, source.t_n.key, analyzer.t_n_in.key)
    chk_meter_l_vfd = has_path(adj_base, analyzer.t_l_out.key, vfd.t_l_in.key)
    chk_meter_n_vfd = has_path(adj_base, analyzer.t_n_out.key, vfd.t_n_in.key)
    chk_vfd_u_motor = has_path(adj_base, vfd.t_u.key, motor.t_u.key)
    chk_vfd_v_motor = has_path(adj_base, vfd.t_v.key, motor.t_v.key)

    analyzer_powered = chk_source_l_meter and chk_source_n_meter and not fault
    vfd_powered = has_path(adj_base, source.t_l.key, vfd.t_l_in.key) and has_path(
        adj_base, source.t_n.key, vfd.t_n_in.key
    ) and not fault
    motor_connected = chk_vfd_u_motor and chk_vfd_v_motor

    output_hz = vfd.set_freq if vfd_powered else 0.0
    motor_running = motor_connected and output_hz > 0.0 and not fault
    motor_rpm = int(output_hz * 30.0) if motor_running else 0

    motor_current = round((output_hz / 60.0) * 8.0, 1) if motor_running else 0.0
    current_through_meter = motor_current if analyzer_powered and chk_meter_l_vfd and chk_meter_n_vfd else 0.0
    power_w = int(round(220.0 * current_through_meter)) if analyzer_powered else 0

    loop_closed = (
        chk_source_l_meter
        and chk_source_n_meter
        and chk_meter_l_vfd
        and chk_meter_n_vfd
        and chk_vfd_u_motor
        and chk_vfd_v_motor
        and not fault
    )

    adj_tags = {k: set(v) for k, v in adj_base.items()}
    if vfd_powered and output_hz > 0.0 and not fault:
        add_edge(adj_tags, vfd.t_l_in.key, vfd.t_u.key)
        add_edge(adj_tags, vfd.t_n_in.key, vfd.t_v.key)

    reach_tags = {
        "L": reachable(adj_tags, source.t_l.key),
        "N": reachable(adj_tags, source.t_n.key),
        "PE": reachable(adj_tags, source.t_pe.key),
    }

    tags_by_key = {k: set() for k in keys}
    for role, nodes in reach_tags.items():
        for node in nodes:
            tags_by_key[node].add(role)

    checks = [
        ("Fuente L -> Analizador L_in", chk_source_l_meter),
        ("Fuente N -> Analizador N_in", chk_source_n_meter),
        ("Analizador L_out -> VFD L_in", chk_meter_l_vfd),
        ("Analizador N_out -> VFD N_in", chk_meter_n_vfd),
        ("VFD U -> Motor U", chk_vfd_u_motor),
        ("VFD V -> Motor V", chk_vfd_v_motor),
    ]

    meter = {
        "powered": analyzer_powered,
        "voltage": "220 V" if analyzer_powered else "--",
        "frequency": "60 Hz" if analyzer_powered else "--",
        "current": f"{current_through_meter:.1f} A",
        "power": f"{power_w} W",
    }

    return {
        "tags": tags_by_key,
        "fault": fault,
        "short_ln": short_ln,
        "short_lpe": short_lpe,
        "checks": checks,
        "analyzer_powered": analyzer_powered,
        "vfd_powered": vfd_powered,
        "motor_connected": motor_connected,
        "motor_running": motor_running,
        "output_hz": output_hz,
        "set_freq": vfd.set_freq,
        "motor_rpm": motor_rpm,
        "loop_closed": loop_closed,
        "meter": meter,
    }


def draw_status_panel(surface, font_title, font_small, info, builder, wire_count):
    box = pygame.Rect(16, HEIGHT - 214, WIDTH - 32, 190)
    panel_bg = pygame.Surface((box.w, box.h), pygame.SRCALPHA)
    panel_bg.fill((26, 31, 39, 190))
    surface.blit(panel_bg, box.topleft)
    pygame.draw.rect(surface, C_PANEL_EDGE, box, 2, border_radius=12)

    left_x = box.x + 16
    y = box.y + 12
    title = font_title.render("Controles", True, C_TEXT)
    surface.blit(title, (left_x, y))
    y += 22
    controls = [
        "Click izq en terminal: iniciar/finalizar cable",
        "Click izq en vacio: fijar esquina (estilo Proteus)",
        "R: cambia orientacion HV/VH",
        "Backspace: quita ultima esquina | C: limpiar cables",
        "Click der: cancelar trazado o borrar cable",
        "Click en + / - del VFD para ajustar frecuencia",
    ]
    for line in controls:
        txt = font_small.render(line, True, C_DIM)
        surface.blit(txt, (left_x, y))
        y += 15

    mid_x = box.x + 540
    y = box.y + 12
    title2 = font_title.render("Chequeo de conexion", True, C_TEXT)
    surface.blit(title2, (mid_x, y))
    y += 22
    for label, ok in info["checks"]:
        color = C_PE if ok else C_DIM
        prefix = "[OK]" if ok else "[  ]"
        txt = font_small.render(f"{prefix} {label}", True, color)
        surface.blit(txt, (mid_x, y))
        y += 15

    right_x = box.right - 320
    y = box.y + 12
    title3 = font_title.render("Estado", True, C_TEXT)
    surface.blit(title3, (right_x, y))
    y += 22

    mode_txt = f"Modo cable: {builder.mode} | cables: {wire_count}"
    surface.blit(font_small.render(mode_txt, True, C_DIM), (right_x, y))
    y += 16

    lazo_txt = "Cerrado" if info["loop_closed"] else "Abierto"
    lazo_color = C_PE if info["loop_closed"] else C_FAULT
    surface.blit(font_small.render(f"Estado del Lazo: {lazo_txt}", True, lazo_color), (right_x, y))
    y += 16

    surface.blit(font_small.render(f"Frecuencia Consigna: {info['set_freq']:.1f} Hz", True, C_TEXT), (right_x, y))
    y += 16
    surface.blit(font_small.render(f"RPM Motor: {info['motor_rpm']} RPM", True, C_TEXT), (right_x, y))
    y += 16

    i_txt = f"Corriente (analizador): {info['meter']['current']}"
    p_txt = f"Potencia (analizador): {info['meter']['power']}"
    surface.blit(font_small.render(i_txt, True, C_TEXT), (right_x, y))
    y += 16
    surface.blit(font_small.render(p_txt, True, C_TEXT), (right_x, y))
    y += 16

    if info["fault"]:
        surface.blit(font_small.render("ALERTA: posible corto L con N/PE", True, C_FAULT), (right_x, y))


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
    pygame.display.set_caption("Simulador de instrumentacion y control industrial")
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("consolas", 20, bold=True)
    font_small = pygame.font.SysFont("consolas", 15)
    font_status_title = pygame.font.SysFont("consolas", 17, bold=True)
    font_status_small = pygame.font.SysFont("consolas", 12)

    source = PowerSource220V(20, 140)
    analyzer = NetworkAnalyzer(380, 124)
    vfd = VFD(760, 114)
    motor = MotorLoad(1160, 150)

    terminals = [
        *source.terminals(),
        *analyzer.terminals(),
        *vfd.terminals(),
        *motor.terminals(),
    ]

    wires = []
    builder = WireBuilder()

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
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
                elif event.key == pygame.K_BACKSPACE:
                    builder.undo_anchor()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = screen_to_world(event.pos, render_size, offset)
                if pos is None:
                    continue
                hit_terminal = find_terminal_at(pos, terminals)

                if event.button == 1:
                    if vfd.handle_click(pos):
                        pass
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

        info = analyze_network(terminals, wires, source, analyzer, vfd, motor)
        motor.update(dt, info["output_hz"], info["motor_running"])

        draw_grid(world)

        source.draw(world, font_title, font_small, info["tags"])
        analyzer.draw(world, font_title, font_small, info["tags"], info["meter"])
        vfd.draw(world, font_title, font_small, info["tags"], info["vfd_powered"], info["output_hz"])
        motor.draw(world, font_title, font_small, info["tags"], info["motor_running"], info["motor_rpm"])

        for w in wires:
            w.draw(world, info["tags"])

        builder.draw(world, mouse_pos)
        draw_status_panel(world, font_status_title, font_status_small, info, builder, len(wires))

        screen.fill(C_BG)
        scaled = pygame.transform.smoothscale(world, render_size)
        screen.blit(scaled, offset)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run_simulator()
