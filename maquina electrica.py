import math
import sys
from collections import deque

import pygame


pygame.init()


WIDTH, HEIGHT = 1400, 800
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

C_L1 = (193, 111, 53)   # Marron
C_L2 = (226, 196, 64)   # Amarillo
C_L3 = (119, 159, 222)  # Azul


PHASES = ("L1", "L2", "L3")
PHASE_COLORS = {
    "L1": C_L1,
    "L2": C_L2,
    "L3": C_L3,
}


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
    phase_hits = [p for p in PHASES if p in tags]
    if len(phase_hits) > 1:
        return C_FAULT
    if phase_hits and "PE" in tags:
        return C_FAULT
    if len(phase_hits) == 1:
        return PHASE_COLORS[phase_hits[0]]
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


class ThreePhaseBreaker:
    def __init__(self, rect, in_terms, out_terms):
        self.rect = pygame.Rect(rect)
        self.in_terms = in_terms
        self.out_terms = out_terms
        self.closed = False

    def toggle(self):
        self.closed = not self.closed

    def pairs(self):
        return list(zip(self.in_terms, self.out_terms))

    def draw(self, surface, font):
        pygame.draw.rect(surface, (55, 64, 76), self.rect, border_radius=10)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=10)

        for idx, (t_in, t_out) in enumerate(self.pairs()):
            y = t_in.pos[1]
            left_pin = (self.rect.left + 24, y)
            right_pin = (self.rect.right - 24, y)

            if self.closed:
                lever_end = right_pin
                lever_color = C_PE
            else:
                lever_end = (self.rect.centerx + 22, y - 18)
                lever_color = C_L

            pygame.draw.line(surface, lever_color, left_pin, lever_end, 5)
            pole = font.render(f"P{idx + 1}", True, C_DIM)
            surface.blit(pole, (self.rect.centerx - 12, y - 10))

        txt = "ON" if self.closed else "OFF"
        lbl = font.render(f"Disyuntor 3P {txt}", True, C_TEXT)
        surface.blit(lbl, (self.rect.left + 18, self.rect.bottom + 8))


class SourceUnit:
    def __init__(self, x, y, title, subtitle, role, key):
        self.rect = pygame.Rect(x, y, 250, 92)
        self.title = title
        self.subtitle = subtitle
        self.role = role
        self.terminal = Terminal(key, (x + 276, y + 46), role)

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


class ThreePhasePanel:
    def __init__(self):
        self.rect = pygame.Rect(320, 80, 560, 560)

        self.t_l1_in = Terminal("panel_l1_in", (390, 180), "L1-IN")
        self.t_l2_in = Terminal("panel_l2_in", (390, 260), "L2-IN")
        self.t_l3_in = Terminal("panel_l3_in", (390, 340), "L3-IN")

        self.t_l1_out = Terminal("panel_l1_out", (800, 180), "L1-OUT")
        self.t_l2_out = Terminal("panel_l2_out", (800, 260), "L2-OUT")
        self.t_l3_out = Terminal("panel_l3_out", (800, 340), "L3-OUT")

        self.t_pe_bar = Terminal("panel_pe", (800, 470), "PE-BAR")

        self.phase_in = {
            "L1": self.t_l1_in,
            "L2": self.t_l2_in,
            "L3": self.t_l3_in,
        }
        self.phase_out = {
            "L1": self.t_l1_out,
            "L2": self.t_l2_out,
            "L3": self.t_l3_out,
        }

        self.breaker = ThreePhaseBreaker(
            (500, 130, 200, 280),
            [self.t_l1_in, self.t_l2_in, self.t_l3_in],
            [self.t_l1_out, self.t_l2_out, self.t_l3_out],
        )

    def phase_pairs(self):
        return self.breaker.pairs()

    def terminals(self):
        return [
            self.t_l1_in,
            self.t_l2_in,
            self.t_l3_in,
            self.t_l1_out,
            self.t_l2_out,
            self.t_l3_out,
            self.t_pe_bar,
        ]

    def draw(self, surface, font_title, font_small, tags_by_key):
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=14)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=14)

        title = font_title.render("TABLERO TRIFASICO", True, C_TEXT)
        surface.blit(title, (self.rect.x + 20, self.rect.y + 16))

        line_y = self.rect.y + 64
        pygame.draw.line(surface, C_PANEL_EDGE, (self.rect.x + 18, line_y), (self.rect.right - 18, line_y), 1)

        for phase in PHASES:
            t_in = self.phase_in[phase]
            t_out = self.phase_out[phase]
            color = PHASE_COLORS[phase]
            left_pin = (self.breaker.rect.left + 24, t_in.pos[1])
            right_pin = (self.breaker.rect.right - 24, t_out.pos[1])

            pygame.draw.line(surface, color, t_in.pos, left_pin, 3)
            pygame.draw.line(surface, color, right_pin, t_out.pos, 3)

        pe_bar_start = (620, self.t_pe_bar.pos[1])
        pygame.draw.line(surface, C_PE, pe_bar_start, self.t_pe_bar.pos, 6)
        lbl_pe = font_small.render("Barra de tierra (PE)", True, C_DIM)
        surface.blit(lbl_pe, (530, self.t_pe_bar.pos[1] - 24))

        self.breaker.draw(surface, font_small)

        for t in self.terminals():
            t.draw(surface, font_small, tags_by_key)


class MotorThreePhase:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 430, 420)
        self.box = pygame.Rect(x + 175, y + 86, 220, 200)

        col1 = self.box.x + 36
        col2 = self.box.x + 110
        col3 = self.box.x + 184
        top_y = self.box.y + 70
        bot_y = self.box.y + 146

        self.t_w2 = Terminal("motor_w2", (col1, top_y), "W2")
        self.t_u2 = Terminal("motor_u2", (col2, top_y), "U2")
        self.t_v2 = Terminal("motor_v2", (col3, top_y), "V2")

        self.t_u1 = Terminal("motor_u1", (col1, bot_y), "U1")
        self.t_v1 = Terminal("motor_v1", (col2, bot_y), "V1")
        self.t_w1 = Terminal("motor_w1", (col3, bot_y), "W1")

    def terminals(self):
        return [self.t_w2, self.t_u2, self.t_v2, self.t_u1, self.t_v1, self.t_w1]

    def draw(self, surface, font_title, font_small, tags_by_key, motor_state):
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=14)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=14)

        title = font_title.render("MOTOR ASINCRONO 3~", True, C_TEXT)
        surface.blit(title, (self.rect.x + 20, self.rect.y + 16))

        center = (self.rect.x + 120, self.rect.y + 220)
        pygame.draw.circle(surface, (63, 72, 83), center, 108)
        pygame.draw.circle(surface, C_PANEL_EDGE, center, 108, 3)
        pygame.draw.circle(surface, (49, 57, 67), center, 72, 2)

        shaft = pygame.Rect(center[0] + 92, center[1] - 14, 50, 28)
        pygame.draw.rect(surface, (145, 152, 163), shaft, border_radius=8)
        pygame.draw.rect(surface, C_PANEL_EDGE, shaft, 1, border_radius=8)

        if motor_state.startswith("GIRANDO"):
            spin_color = C_PE if "ESTRELLA" in motor_state else C_PREVIEW
            for r in (42, 56, 70):
                arc_rect = pygame.Rect(center[0] - r, center[1] - r, r * 2, r * 2)
                pygame.draw.arc(surface, spin_color, arc_rect, 0.5, 4.7, 2)

        pygame.draw.rect(surface, (34, 40, 50), self.box, border_radius=10)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.box, 2, border_radius=10)

        mid_y = self.box.y + 108
        col_a = self.box.x + 73
        col_b = self.box.x + 147
        pygame.draw.line(surface, C_PANEL_EDGE, (self.box.x + 8, mid_y), (self.box.right - 8, mid_y), 1)
        pygame.draw.line(surface, C_PANEL_EDGE, (col_a, self.box.y + 8), (col_a, self.box.bottom - 8), 1)
        pygame.draw.line(surface, C_PANEL_EDGE, (col_b, self.box.y + 8), (col_b, self.box.bottom - 8), 1)

        lbl = font_small.render("Caja de bornes IEC", True, C_TEXT)
        surface.blit(lbl, (self.box.x + 20, self.box.y + 16))

        for t in self.terminals():
            t.draw(surface, font_small, tags_by_key)


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


def build_components(adj):
    comp_id = {}
    comps = []

    for node in adj:
        if node in comp_id:
            continue
        cid = len(comps)
        q = deque([node])
        comp_id[node] = cid
        comp_nodes = {node}

        while q:
            cur = q.popleft()
            for nxt in adj[cur]:
                if nxt not in comp_id:
                    comp_id[nxt] = cid
                    comp_nodes.add(nxt)
                    q.append(nxt)

        comps.append(comp_nodes)

    return comp_id, comps


def analyze_network(terminals, wires, panel, sources, motor):
    keys = [t.key for t in terminals]
    adj = {k: set() for k in keys}

    for w in wires:
        a, b = w.start.key, w.end.key
        adj[a].add(b)
        adj[b].add(a)

    if panel.breaker.closed:
        for t_in, t_out in panel.phase_pairs():
            a, b = t_in.key, t_out.key
            adj[a].add(b)
            adj[b].add(a)

    reach = {role: reachable(adj, sources[role].key) for role in sources}

    tags_by_key = {k: set() for k in keys}
    for role, nodes in reach.items():
        for node in nodes:
            tags_by_key[node].add(role)

    short_phase_phase = any(
        sources[p2].key in reach[p1]
        for i, p1 in enumerate(PHASES)
        for p2 in PHASES[i + 1 :]
    )
    short_phase_pe = any(sources["PE"].key in reach[p] for p in PHASES)
    fault = short_phase_phase or short_phase_pe

    comp_id, comps = build_components(adj)
    comp_phase_tags = [set() for _ in comps]
    for phase in PHASES:
        cid = comp_id.get(sources[phase].key)
        if cid is not None:
            comp_phase_tags[cid].add(phase)

    def phases_at(node_key):
        cid = comp_id.get(node_key)
        if cid is None:
            return set()
        return comp_phase_tags[cid]

    k_w2 = motor.t_w2.key
    k_u2 = motor.t_u2.key
    k_v2 = motor.t_v2.key
    k_u1 = motor.t_u1.key
    k_v1 = motor.t_v1.key
    k_w1 = motor.t_w1.key

    top_keys = [k_w2, k_u2, k_v2]
    bottom_keys = [k_u1, k_v1, k_w1]

    bottom_phase_sets = [phases_at(k) for k in bottom_keys]
    bottom_union = set()
    for s in bottom_phase_sets:
        bottom_union |= s

    bottom_distinct_phases = all(len(s) == 1 for s in bottom_phase_sets) and bottom_union == set(PHASES)
    bottom_isolated = len({comp_id[k] for k in bottom_keys}) == 3

    top_same_component = len({comp_id[k] for k in top_keys}) == 1
    top_cid = comp_id[top_keys[0]]
    top_no_phase = len(comp_phase_tags[top_cid]) == 0
    top_separate = top_cid not in {comp_id[k] for k in bottom_keys}

    star_valid = top_same_component and top_no_phase and top_separate and bottom_distinct_phases and bottom_isolated

    pair_a_ok = comp_id[k_u1] == comp_id[k_w2]  # U1-W2
    pair_b_ok = comp_id[k_v1] == comp_id[k_u2]  # V1-U2
    pair_c_ok = comp_id[k_w1] == comp_id[k_v2]  # W1-V2

    pair_cids = [comp_id[k_u1], comp_id[k_v1], comp_id[k_w1]]
    pair_distinct = len(set(pair_cids)) == 3

    pair_phase_sets = [comp_phase_tags[cid] for cid in pair_cids]
    pair_union = set()
    for s in pair_phase_sets:
        pair_union |= s
    pair_phase_ok = all(len(s) == 1 for s in pair_phase_sets) and pair_union == set(PHASES)

    delta_valid = pair_a_ok and pair_b_ok and pair_c_ok and pair_distinct and pair_phase_ok

    source_to_panel = all(has_path(adj, sources[p].key, panel.phase_in[p].key) for p in PHASES)
    alimentacion_presente = source_to_panel and (bottom_union == set(PHASES))
    pe_to_bar = has_path(adj, sources["PE"].key, panel.t_pe_bar.key)

    config_valid = star_valid or delta_valid
    topology = "ESTRELLA" if star_valid else ("TRIANGULO" if delta_valid else "NINGUNA")

    if fault:
        motor_state = "CORTO DETECTADO"
    elif panel.breaker.closed and alimentacion_presente and star_valid:
        motor_state = "GIRANDO EN ESTRELLA"
    elif panel.breaker.closed and alimentacion_presente and delta_valid:
        motor_state = "GIRANDO EN TRIANGULO"
    else:
        motor_state = "PARADO"

    checks = [
        ("Alimentacion presente", alimentacion_presente),
        ("Disyuntor activado", panel.breaker.closed),
        ("Configuracion de bornes valida", config_valid),
        ("PE a barra", pe_to_bar),
    ]

    return {
        "tags": tags_by_key,
        "fault": fault,
        "short_phase_phase": short_phase_phase,
        "short_phase_pe": short_phase_pe,
        "star_valid": star_valid,
        "delta_valid": delta_valid,
        "topology": topology,
        "motor_state": motor_state,
        "alimentacion_presente": alimentacion_presente,
        "checks": checks,
    }


def draw_status_panel(surface, font_title, font_small, info, builder, wire_count):
    box = pygame.Rect(20, HEIGHT - 174, WIDTH - 40, 154)
    pygame.draw.rect(surface, (26, 31, 39), box, border_radius=12)
    pygame.draw.rect(surface, C_PANEL_EDGE, box, 2, border_radius=12)

    left_x = box.x + 16
    y = box.y + 14
    title = font_title.render("Controles", True, C_TEXT)
    surface.blit(title, (left_x, y))
    y += 26
    controls = [
        "Click izq en terminal: iniciar/finalizar cable",
        "Click izq en vacio: fijar esquina (estilo Proteus)",
        "R: cambia orientacion HV/VH",
        "Backspace: quita ultima esquina | C: limpiar cables",
        "Click der: cancelar trazado o borrar cable",
        "Click en disyuntor 3P o tecla B para ON/OFF",
    ]
    for line in controls:
        txt = font_small.render(line, True, C_DIM)
        surface.blit(txt, (left_x, y))
        y += 18

    mid_x = box.x + 540
    y = box.y + 14
    title2 = font_title.render("Validacion", True, C_TEXT)
    surface.blit(title2, (mid_x, y))
    y += 26
    for label, ok in info["checks"]:
        color = C_PE if ok else C_DIM
        prefix = "[OK]" if ok else "[  ]"
        txt = font_small.render(f"{prefix} {label}", True, color)
        surface.blit(txt, (mid_x, y))
        y += 18

    right_x = box.right - 360
    y = box.y + 14
    title3 = font_title.render("Estado", True, C_TEXT)
    surface.blit(title3, (right_x, y))
    y += 26

    mode_txt = f"Modo cable: {builder.mode} | cables: {wire_count}"
    surface.blit(font_small.render(mode_txt, True, C_DIM), (right_x, y))
    y += 18

    state_color = C_TEXT
    if info["fault"]:
        state_color = C_FAULT
    elif info["motor_state"].startswith("GIRANDO"):
        state_color = C_PE

    state_txt = f"Estado del Motor: {info['motor_state']}"
    surface.blit(font_small.render(state_txt, True, state_color), (right_x, y))
    y += 18

    topo_txt = f"Topologia detectada: {info['topology']}"
    surface.blit(font_small.render(topo_txt, True, C_TEXT), (right_x, y))
    y += 18

    if info["fault"]:
        if info["short_phase_phase"]:
            warn = "Falla: contacto entre fases."
        elif info["short_phase_pe"]:
            warn = "Falla: contacto fase-tierra."
        else:
            warn = "Falla electrica detectada."
        surface.blit(font_small.render(warn, True, C_FAULT), (right_x, y))


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
    pygame.display.set_caption("Simulador de conexion de motor trifasico (Estrella/Triangulo)")
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("consolas", 20, bold=True)
    font_small = pygame.font.SysFont("consolas", 15)

    source_l1 = SourceUnit(24, 104, "RED TRIFASICA", "Fase L1 (R)", "L1", "src_l1")
    source_l2 = SourceUnit(24, 220, "RED TRIFASICA", "Fase L2 (S)", "L2", "src_l2")
    source_l3 = SourceUnit(24, 336, "RED TRIFASICA", "Fase L3 (T)", "L3", "src_l3")
    source_pe = SourceUnit(24, 452, "PUESTA A TIERRA", "Borne PE", "PE", "src_pe")

    panel = ThreePhasePanel()
    motor = MotorThreePhase(900, 120)

    terminals = [
        source_l1.terminal,
        source_l2.terminal,
        source_l3.terminal,
        source_pe.terminal,
        *panel.terminals(),
        *motor.terminals(),
    ]

    sources = {
        "L1": source_l1.terminal,
        "L2": source_l2.terminal,
        "L3": source_l3.terminal,
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

        info = analyze_network(terminals, wires, panel, sources, motor)

        draw_grid(world)

        source_l1.draw(world, font_title, font_small, info["tags"])
        source_l2.draw(world, font_title, font_small, info["tags"])
        source_l3.draw(world, font_title, font_small, info["tags"])
        source_pe.draw(world, font_title, font_small, info["tags"])
        panel.draw(world, font_title, font_small, info["tags"])
        motor.draw(world, font_title, font_small, info["tags"], info["motor_state"])

        for w in wires:
            w.draw(world, info["tags"])

        builder.draw(world, mouse_pos)

        draw_status_panel(world, font_title, font_small, info, builder, len(wires))

        screen.fill(C_BG)
        scaled = pygame.transform.smoothscale(world, render_size)
        screen.blit(scaled, offset)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run_simulator()
