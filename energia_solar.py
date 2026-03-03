import math
import sys
from collections import deque

import pygame


pygame.init()


WIDTH, HEIGHT = 1600, 800
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

C_DC_POS = (230, 108, 96)
C_DC_NEG = (104, 170, 242)


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
    if "L" in tags and "N" in tags:
        return C_FAULT
    if "P" in tags and "M" in tags:
        return C_FAULT
    if "L" in tags:
        return C_L
    if "N" in tags:
        return C_N
    if "P" in tags:
        return C_DC_POS
    if "M" in tags:
        return C_DC_NEG
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


class SolarPanel:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 220, 320)
        self.t_pos = Terminal("pv_pos", (x + 246, y + 110), "+")
        self.t_neg = Terminal("pv_neg", (x + 246, y + 170), "-")

        self.slider_track = pygame.Rect(x + 24, y + 276, 170, 10)
        self.knob_radius = 10
        self.solar_intensity = 0.65
        self.dragging = False

    def terminals(self):
        return [self.t_pos, self.t_neg]

    def _knob_center(self):
        knob_x = int(self.slider_track.x + self.solar_intensity * self.slider_track.w)
        return (knob_x, self.slider_track.centery)

    def _set_intensity_from_x(self, x):
        rel = (x - self.slider_track.x) / self.slider_track.w
        self.solar_intensity = max(0.0, min(1.0, rel))

    def handle_mouse_down(self, pos):
        knob = self._knob_center()
        if math.dist(pos, knob) <= self.knob_radius + 5 or self.slider_track.inflate(16, 22).collidepoint(pos):
            self.dragging = True
            self._set_intensity_from_x(pos[0])
            return True
        return False

    def handle_mouse_up(self):
        self.dragging = False

    def handle_mouse_motion(self, pos):
        if self.dragging:
            self._set_intensity_from_x(pos[0])

    def draw(self, surface, font_title, font_small, tags_by_key):
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=12)

        title = font_title.render("PANEL SOLAR", True, C_TEXT)
        sub = font_small.render("Fuente DC", True, C_DIM)
        surface.blit(title, (self.rect.x + 14, self.rect.y + 14))
        surface.blit(sub, (self.rect.x + 14, self.rect.y + 40))

        cell_area = pygame.Rect(self.rect.x + 22, self.rect.y + 62, 176, 182)
        pygame.draw.rect(surface, (34, 80, 126), cell_area, border_radius=8)
        pygame.draw.rect(surface, (78, 142, 195), cell_area, 2, border_radius=8)

        for gx in range(cell_area.x + 22, cell_area.right, 22):
            pygame.draw.line(surface, (58, 120, 170), (gx, cell_area.y + 2), (gx, cell_area.bottom - 2), 1)
        for gy in range(cell_area.y + 22, cell_area.bottom, 22):
            pygame.draw.line(surface, (58, 120, 170), (cell_area.x + 2, gy), (cell_area.right - 2, gy), 1)

        track = self.slider_track
        knob = self._knob_center()
        pygame.draw.line(surface, C_PANEL_EDGE, (track.left, track.centery), (track.right, track.centery), 4)
        pygame.draw.line(surface, C_DC_POS, (track.left, track.centery), knob, 4)
        pygame.draw.circle(surface, C_TEXT, knob, self.knob_radius)
        pygame.draw.circle(surface, C_BG, knob, self.knob_radius, 2)

        pct_txt = font_small.render(f"Intensidad Solar: {int(self.solar_intensity * 100):3d} %", True, C_TEXT)
        surface.blit(pct_txt, (self.rect.x + 14, self.rect.y + 294))

        pygame.draw.line(
            surface, C_DC_POS, (self.rect.right - 10, self.t_pos.pos[1]), (self.t_pos.pos[0] - 10, self.t_pos.pos[1]), 3
        )
        pygame.draw.line(
            surface, C_DC_NEG, (self.rect.right - 10, self.t_neg.pos[1]), (self.t_neg.pos[0] - 10, self.t_neg.pos[1]), 3
        )

        self.t_pos.draw(surface, font_small, tags_by_key)
        self.t_neg.draw(surface, font_small, tags_by_key)


class ChargeController:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 220, 340)

        self.t_pv_pos = Terminal("ctrl_pv_pos", (x - 26, y + 100), "PV+")
        self.t_pv_neg = Terminal("ctrl_pv_neg", (x - 26, y + 152), "PV-")

        self.t_load_pos = Terminal("ctrl_load_pos", (x + 246, y + 130), "LOAD+")
        self.t_load_neg = Terminal("ctrl_load_neg", (x + 246, y + 182), "LOAD-")

        self.t_batt_pos = Terminal("ctrl_batt_pos", (x + 246, y + 250), "BAT+")
        self.t_batt_neg = Terminal("ctrl_batt_neg", (x + 246, y + 302), "BAT-")

        self.lcd = pygame.Rect(x + 18, y + 58, 184, 88)

    def terminals(self):
        return [
            self.t_pv_pos,
            self.t_pv_neg,
            self.t_load_pos,
            self.t_load_neg,
            self.t_batt_pos,
            self.t_batt_neg,
        ]

    def draw(self, surface, font_title, font_small, tags_by_key, battery_connected, solar_intensity, charge_path, discharge_path):
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=12)

        title = font_title.render("CONTROLADOR", True, C_TEXT)
        sub = font_small.render("Gestor de carga", True, C_DIM)
        surface.blit(title, (self.rect.x + 14, self.rect.y + 14))
        surface.blit(sub, (self.rect.x + 14, self.rect.y + 40))

        pygame.draw.rect(surface, (12, 18, 24), self.lcd, border_radius=8)
        pygame.draw.rect(surface, (74, 88, 104), self.lcd, 2, border_radius=8)

        st_color = C_PE if battery_connected else C_FAULT
        line1 = "BATT: OK" if battery_connected else "BATT: NO CONECTADA"
        line2 = f"SOL: {int(solar_intensity * 100):3d}%"
        line3 = "FLOW: CARGA" if charge_path else ("FLOW: DESCARGA" if discharge_path else "FLOW: ESPERA")
        surface.blit(font_small.render(line1, True, st_color), (self.lcd.x + 10, self.lcd.y + 10))
        surface.blit(font_small.render(line2, True, C_TEXT), (self.lcd.x + 10, self.lcd.y + 34))
        surface.blit(font_small.render(line3, True, C_TEXT), (self.lcd.x + 10, self.lcd.y + 58))

        left_terms = [self.t_pv_pos, self.t_pv_neg]
        right_terms = [self.t_load_pos, self.t_load_neg, self.t_batt_pos, self.t_batt_neg]

        for t in left_terms:
            pygame.draw.line(surface, C_DIM, (t.pos[0] + 10, t.pos[1]), (self.rect.left + 8, t.pos[1]), 3)
        for t in right_terms:
            pygame.draw.line(surface, C_DIM, (self.rect.right - 8, t.pos[1]), (t.pos[0] - 10, t.pos[1]), 3)

        for t in self.terminals():
            t.draw(surface, font_small, tags_by_key)


class BatteryBank:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 220, 350)
        self.t_pos = Terminal("bat_pos", (x - 26, y + 250), "+")
        self.t_neg = Terminal("bat_neg", (x - 26, y + 302), "-")
        self.charge_level = 55.0

    def terminals(self):
        return [self.t_pos, self.t_neg]

    def draw(self, surface, font_title, font_small, tags_by_key, mode_text):
        pygame.draw.rect(surface, (46, 48, 54), self.rect, border_radius=12)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 3, border_radius=12)
        inner = self.rect.inflate(-8, -8)
        pygame.draw.rect(surface, C_PANEL, inner, border_radius=10)

        title = font_title.render("BATERIA", True, C_TEXT)
        sub = font_small.render("Almacenamiento", True, C_DIM)
        surface.blit(title, (self.rect.x + 14, self.rect.y + 14))
        surface.blit(sub, (self.rect.x + 14, self.rect.y + 40))

        bar = pygame.Rect(self.rect.x + 132, self.rect.y + 58, 62, 248)
        pygame.draw.rect(surface, (20, 25, 32), bar, border_radius=8)
        pygame.draw.rect(surface, C_PANEL_EDGE, bar, 2, border_radius=8)

        if self.charge_level >= 60.0:
            fill_color = C_PE
        elif self.charge_level >= 25.0:
            fill_color = C_FAULT
        else:
            fill_color = C_L

        fill_h = int(bar.h * (self.charge_level / 100.0))
        if fill_h > 0:
            fill_rect = pygame.Rect(bar.x + 4, bar.bottom - fill_h + 4, bar.w - 8, max(1, fill_h - 8))
            pygame.draw.rect(surface, fill_color, fill_rect, border_radius=6)

        pct = font_title.render(f"{self.charge_level:5.1f} %", True, C_TEXT)
        mode_lbl = font_small.render(mode_text, True, C_DIM)
        surface.blit(pct, (self.rect.x + 14, self.rect.y + 292))
        surface.blit(mode_lbl, (self.rect.x + 14, self.rect.y + 320))

        pygame.draw.line(
            surface, C_DC_POS, (self.t_pos.pos[0] + 10, self.t_pos.pos[1]), (self.rect.left + 8, self.t_pos.pos[1]), 3
        )
        pygame.draw.line(
            surface, C_DC_NEG, (self.t_neg.pos[0] + 10, self.t_neg.pos[1]), (self.rect.left + 8, self.t_neg.pos[1]), 3
        )

        self.t_pos.draw(surface, font_small, tags_by_key)
        self.t_neg.draw(surface, font_small, tags_by_key)


class Inverter:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 220, 320)
        self.t_dc_pos = Terminal("inv_dc_pos", (x - 26, y + 120), "DC+")
        self.t_dc_neg = Terminal("inv_dc_neg", (x - 26, y + 180), "DC-")
        self.t_ac_l = Terminal("inv_ac_l", (x + 246, y + 130), "L")
        self.t_ac_n = Terminal("inv_ac_n", (x + 246, y + 190), "N")

    def terminals(self):
        return [self.t_dc_pos, self.t_dc_neg, self.t_ac_l, self.t_ac_n]

    def draw(self, surface, font_title, font_small, tags_by_key, on):
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=12)

        title = font_title.render("INVERSOR DC/AC", True, C_TEXT)
        surface.blit(title, (self.rect.x + 14, self.rect.y + 14))

        for i in range(7):
            y = self.rect.y + 76 + i * 15
            pygame.draw.line(surface, (78, 90, 105), (self.rect.x + 22, y), (self.rect.x + 198, y), 2)

        st = "ON" if on else "OFF"
        st_color = C_PE if on else C_L
        state_lbl = font_small.render(f"Estado: {st}", True, st_color)
        surface.blit(state_lbl, (self.rect.x + 14, self.rect.y + 286))

        pygame.draw.line(
            surface,
            C_DC_POS,
            (self.t_dc_pos.pos[0] + 10, self.t_dc_pos.pos[1]),
            (self.rect.left + 8, self.t_dc_pos.pos[1]),
            3,
        )
        pygame.draw.line(
            surface,
            C_DC_NEG,
            (self.t_dc_neg.pos[0] + 10, self.t_dc_neg.pos[1]),
            (self.rect.left + 8, self.t_dc_neg.pos[1]),
            3,
        )
        pygame.draw.line(
            surface, C_L, (self.rect.right - 8, self.t_ac_l.pos[1]), (self.t_ac_l.pos[0] - 10, self.t_ac_l.pos[1]), 3
        )
        pygame.draw.line(
            surface, C_N, (self.rect.right - 8, self.t_ac_n.pos[1]), (self.t_ac_n.pos[0] - 10, self.t_ac_n.pos[1]), 3
        )

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

        lbl = font_title.render("BOMBILLA 220V", True, C_TEXT)
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


def analyze_network(terminals, wires, panel, controller, battery, inverter, lamp, solar_intensity, battery_level):
    keys = [t.key for t in terminals]
    adj_base = {k: set() for k in keys}

    for w in wires:
        add_edge(adj_base, w.start.key, w.end.key)

    chk_pv_pos = has_path(adj_base, panel.t_pos.key, controller.t_pv_pos.key)
    chk_pv_neg = has_path(adj_base, panel.t_neg.key, controller.t_pv_neg.key)

    chk_ctrl_batt_pos = has_path(adj_base, controller.t_batt_pos.key, battery.t_pos.key)
    chk_ctrl_batt_neg = has_path(adj_base, controller.t_batt_neg.key, battery.t_neg.key)

    chk_ctrl_load_pos = has_path(adj_base, controller.t_load_pos.key, inverter.t_dc_pos.key)
    chk_ctrl_load_neg = has_path(adj_base, controller.t_load_neg.key, inverter.t_dc_neg.key)

    chk_inv_l_lamp = has_path(adj_base, inverter.t_ac_l.key, lamp.t_l.key)
    chk_inv_n_lamp = has_path(adj_base, inverter.t_ac_n.key, lamp.t_n.key)

    battery_connected = chk_ctrl_batt_pos and chk_ctrl_batt_neg

    adj_logic = {k: set(v) for k, v in adj_base.items()}
    if battery_connected:
        add_edge(adj_logic, controller.t_pv_pos.key, controller.t_batt_pos.key)
        add_edge(adj_logic, controller.t_pv_neg.key, controller.t_batt_neg.key)
        add_edge(adj_logic, controller.t_batt_pos.key, controller.t_load_pos.key)
        add_edge(adj_logic, controller.t_batt_neg.key, controller.t_load_neg.key)

    charge_path = (
        battery_connected
        and chk_pv_pos
        and chk_pv_neg
        and has_path(adj_logic, panel.t_pos.key, battery.t_pos.key)
        and has_path(adj_logic, panel.t_neg.key, battery.t_neg.key)
    )

    discharge_path = (
        battery_connected
        and chk_ctrl_load_pos
        and chk_ctrl_load_neg
        and has_path(adj_logic, battery.t_pos.key, inverter.t_dc_pos.key)
        and has_path(adj_logic, battery.t_neg.key, inverter.t_dc_neg.key)
    )

    inverter_on = discharge_path and battery_level > 0.1
    lamp_wired = chk_inv_l_lamp and chk_inv_n_lamp
    lamp_on = inverter_on and lamp_wired
    output_voltage = 220 if inverter_on else 0

    tags_by_key = {k: set() for k in keys}

    if solar_intensity > 0.01 and charge_path:
        for node in reachable(adj_logic, panel.t_pos.key):
            tags_by_key[node].add("P")
        for node in reachable(adj_logic, panel.t_neg.key):
            tags_by_key[node].add("M")

    if battery_connected and battery_level > 0.1:
        for node in reachable(adj_logic, battery.t_pos.key):
            tags_by_key[node].add("P")
        for node in reachable(adj_logic, battery.t_neg.key):
            tags_by_key[node].add("M")

    if inverter_on:
        for node in reachable(adj_base, inverter.t_ac_l.key):
            tags_by_key[node].add("L")
        for node in reachable(adj_base, inverter.t_ac_n.key):
            tags_by_key[node].add("N")

    checks = [
        ("Panel + -> Controlador PV+", chk_pv_pos),
        ("Panel - -> Controlador PV-", chk_pv_neg),
        ("Controlador BAT+ -> Bateria +", chk_ctrl_batt_pos),
        ("Controlador BAT- -> Bateria -", chk_ctrl_batt_neg),
        ("Controlador LOAD+ -> Inversor DC+", chk_ctrl_load_pos),
        ("Controlador LOAD- -> Inversor DC-", chk_ctrl_load_neg),
        ("Inversor L -> Bombilla L", chk_inv_l_lamp),
        ("Inversor N -> Bombilla N", chk_inv_n_lamp),
    ]

    return {
        "tags": tags_by_key,
        "checks": checks,
        "battery_connected": battery_connected,
        "charge_path": charge_path,
        "discharge_path": discharge_path,
        "inverter_on": inverter_on,
        "lamp_on": lamp_on,
        "output_voltage": output_voltage,
    }


def draw_status_panel(surface, font_title, font_small, info, builder, wire_count, solar_intensity, battery_level, battery_mode):
    box = pygame.Rect(16, HEIGHT - 214, WIDTH - 32, 190)
    panel_bg = pygame.Surface((box.w, box.h), pygame.SRCALPHA)
    panel_bg.fill((26, 31, 39, 190))
    surface.blit(panel_bg, box.topleft)
    pygame.draw.rect(surface, C_PANEL_EDGE, box, 2, border_radius=12)

    left_x = box.x + 16
    y = box.y + 12
    surface.blit(font_title.render("Controles", True, C_TEXT), (left_x, y))
    y += 22
    controls = [
        "Click izq terminal: iniciar/finalizar cable",
        "Click izq vacio: fijar esquina (Proteus)",
        "R: cambia orientacion HV/VH",
        "Backspace: quitar esquina | C: limpiar cables",
        "Click der: cancelar trazado o borrar cable",
    ]
    for line in controls:
        surface.blit(font_small.render(line, True, C_DIM), (left_x, y))
        y += 15

    mid_x = box.x + 520
    y = box.y + 12
    surface.blit(font_title.render("Chequeo de Conexion", True, C_TEXT), (mid_x, y))
    y += 22
    for label, ok in info["checks"]:
        color = C_PE if ok else C_DIM
        prefix = "[OK]" if ok else "[  ]"
        surface.blit(font_small.render(f"{prefix} {label}", True, color), (mid_x, y))
        y += 15

    right_x = box.right - 320
    y = box.y + 12
    surface.blit(font_title.render("Estado", True, C_TEXT), (right_x, y))
    y += 22

    mode_txt = f"Modo cable: {builder.mode} | cables: {wire_count}"
    surface.blit(font_small.render(mode_txt, True, C_DIM), (right_x, y))
    y += 18

    sol_txt = f"Sol: {int(solar_intensity * 100):3d} %"
    bat_txt = f"Bateria: {battery_level:5.1f} % ({battery_mode})"
    inv_txt = f"Inversor: {'ON' if info['inverter_on'] else 'OFF'}"
    volt_txt = f"Voltaje Salida: {info['output_voltage']}V"

    surface.blit(font_small.render(sol_txt, True, C_TEXT), (right_x, y))
    y += 16
    surface.blit(font_small.render(bat_txt, True, C_TEXT), (right_x, y))
    y += 16
    surface.blit(font_small.render(inv_txt, True, C_TEXT), (right_x, y))
    y += 16
    surface.blit(font_small.render(volt_txt, True, C_TEXT), (right_x, y))
    y += 16

    if not info["battery_connected"]:
        surface.blit(font_small.render("Aviso: el controlador requiere bateria", True, C_FAULT), (right_x, y))
    elif battery_level <= 0.0 and not info["charge_path"]:
        surface.blit(font_small.render("BLACKOUT: bateria agotada", True, C_FAULT), (right_x, y))


def setup_fullscreen():
    info = pygame.display.Info()
    screen_size = (info.current_w, info.current_h)
    screen = pygame.display.set_mode(screen_size, pygame.FULLSCREEN)
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
    pygame.display.set_caption("Simulador Fotovoltaico Off-Grid")
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("consolas", 20, bold=True)
    font_small = pygame.font.SysFont("consolas", 15)
    font_status_title = pygame.font.SysFont("consolas", 17, bold=True)
    font_status_small = pygame.font.SysFont("consolas", 12)

    panel = SolarPanel(50, 100)
    controller = ChargeController(350, 90)
    battery = BatteryBank(650, 90)
    inverter = Inverter(950, 100)
    lamp = LampLoad(1250, 120)

    terminals = [
        *panel.terminals(),
        *controller.terminals(),
        *battery.terminals(),
        *inverter.terminals(),
        *lamp.terminals(),
    ]

    wires = []
    builder = WireBuilder()

    factor_carga = 16.0
    consumo_bombilla = 10.0

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

            elif event.type == pygame.MOUSEMOTION:
                pos = screen_to_world(event.pos, render_size, offset)
                if pos is not None:
                    panel.handle_mouse_motion(pos)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    panel.handle_mouse_up()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = screen_to_world(event.pos, render_size, offset)
                if pos is None:
                    continue
                hit_terminal = find_terminal_at(pos, terminals)

                if event.button == 1:
                    if panel.handle_mouse_down(pos):
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

        info = analyze_network(
            terminals,
            wires,
            panel,
            controller,
            battery,
            inverter,
            lamp,
            panel.solar_intensity,
            battery.charge_level,
        )

        produccion = panel.solar_intensity * factor_carga if info["charge_path"] else 0.0
        consumo = consumo_bombilla if info["lamp_on"] else 0.0
        battery.charge_level += (produccion - consumo) * dt
        battery.charge_level = max(0.0, min(100.0, battery.charge_level))

        if produccion > consumo + 1e-6:
            battery_mode = "Cargando"
        elif consumo > produccion + 1e-6:
            battery_mode = "Descargando"
        elif battery.charge_level <= 0.0 and produccion <= 0.0:
            battery_mode = "Blackout"
        else:
            battery_mode = "Reposo"

        info = analyze_network(
            terminals,
            wires,
            panel,
            controller,
            battery,
            inverter,
            lamp,
            panel.solar_intensity,
            battery.charge_level,
        )

        draw_grid(world)

        panel.draw(world, font_title, font_small, info["tags"])
        controller.draw(
            world,
            font_title,
            font_small,
            info["tags"],
            info["battery_connected"],
            panel.solar_intensity,
            info["charge_path"],
            info["discharge_path"],
        )
        battery.draw(world, font_title, font_small, info["tags"], battery_mode)
        inverter.draw(world, font_title, font_small, info["tags"], info["inverter_on"])
        lamp.draw(world, font_title, font_small, info["tags"], info["lamp_on"])

        for w in wires:
            w.draw(world, info["tags"])

        builder.draw(world, mouse_pos)

        draw_status_panel(
            world,
            font_status_title,
            font_status_small,
            info,
            builder,
            len(wires),
            panel.solar_intensity,
            battery.charge_level,
            battery_mode,
        )

        screen.fill(C_BG)
        scaled = pygame.transform.smoothscale(world, render_size)
        screen.blit(scaled, offset)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run_simulator()
