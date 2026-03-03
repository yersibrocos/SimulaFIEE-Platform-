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
C_POS = (245, 92, 92)
C_NEG = (100, 175, 250)
C_GOOD = (105, 205, 125)
C_WARN = (255, 195, 70)
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


def draw_grid(surface):
    surface.fill(C_BG)
    for x in range(0, WIDTH, GRID):
        pygame.draw.line(surface, C_GRID, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, GRID):
        pygame.draw.line(surface, C_GRID, (0, y), (WIDTH, y), 1)


class Terminal:
    def __init__(self, key, pos, label, role="wire"):
        self.key = key
        self.pos = snap_point(pos)
        self.label = label
        self.role = role
        self.radius = 8

    def hit_test(self, pos):
        return math.dist(self.pos, pos) <= self.radius + 6

    def draw(self, surface, font, reached_plus, reached_minus):
        if self.key in reached_plus and self.key in reached_minus:
            color = C_WARN
        elif self.key in reached_plus:
            color = C_POS
        elif self.key in reached_minus:
            color = C_NEG
        else:
            color = C_WIRE_IDLE

        pygame.draw.circle(surface, C_BG, self.pos, self.radius + 4)
        pygame.draw.circle(surface, color, self.pos, self.radius)
        pygame.draw.circle(surface, C_TEXT, self.pos, self.radius, 1)
        lbl = font.render(self.label, True, C_TEXT)
        surface.blit(lbl, (self.pos[0] + 10, self.pos[1] - 8))


class Wire:
    def __init__(self, start_terminal, end_terminal, points):
        self.start = start_terminal
        self.end = end_terminal
        self.points = simplify_polyline(points)

    def draw(self, surface, reached_plus, reached_minus):
        start_mix = self.start.key in reached_plus and self.start.key in reached_minus
        end_mix = self.end.key in reached_plus and self.end.key in reached_minus
        if start_mix or end_mix:
            color = C_WARN
        elif self.start.key in reached_plus or self.end.key in reached_plus:
            color = C_POS
        elif self.start.key in reached_minus or self.end.key in reached_minus:
            color = C_NEG
        else:
            color = C_WIRE_IDLE

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

    def preview_points(self, pos):
        if not self.active:
            return []
        path = self._path_to(pos)
        return simplify_polyline(self.points + path[1:])

    def draw(self, surface, mouse_pos):
        if not self.active:
            return
        for p in self.points:
            pygame.draw.circle(surface, C_PREVIEW, p, 3)
        preview = self.preview_points(mouse_pos)
        if len(preview) >= 2:
            pygame.draw.lines(surface, C_PREVIEW, False, preview, 2)


class ModuleBox:
    def __init__(self, title, rect, terminals):
        self.title = title
        self.rect = pygame.Rect(rect)
        self.terminals = terminals

    def draw(self, surface, font_title):
        pygame.draw.rect(surface, C_PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surface, C_PANEL_EDGE, self.rect, 2, border_radius=12)
        title = font_title.render(self.title, True, C_TEXT)
        surface.blit(title, (self.rect.x + 14, self.rect.y + 14))


class SwitchModule(ModuleBox):
    def __init__(self, title, rect, t_in, t_out):
        super().__init__(title, rect, [t_in, t_out])
        self.t_in = t_in
        self.t_out = t_out
        self.closed = False

    def toggle(self):
        self.closed = not self.closed

    def draw(self, surface, font_title, font_small):
        super().draw(surface, font_title)
        left_pin = (self.rect.left + 30, self.rect.centery + 12)
        right_pin = (self.rect.right - 30, self.rect.centery + 12)
        pygame.draw.line(surface, C_DIM, (self.t_in.pos[0] + 10, self.t_in.pos[1]), left_pin, 3)
        pygame.draw.line(surface, C_DIM, right_pin, (self.t_out.pos[0] - 10, self.t_out.pos[1]), 3)

        if self.closed:
            lever_end = right_pin
            lever_color = C_GOOD
        else:
            lever_end = (self.rect.centerx + 22, self.rect.y + 40)
            lever_color = C_POS

        pygame.draw.line(surface, lever_color, left_pin, lever_end, 5)
        st = "ON" if self.closed else "OFF"
        lbl = font_small.render(f"Estado: {st}", True, C_TEXT)
        surface.blit(lbl, (self.rect.x + 14, self.rect.bottom - 24))


class LampModule(ModuleBox):
    def __init__(self, title, rect, t_plus, t_minus):
        super().__init__(title, rect, [t_plus, t_minus])
        self.t_plus = t_plus
        self.t_minus = t_minus

    def draw(self, surface, font_title, on):
        super().draw(surface, font_title)
        center = (self.rect.centerx + 40, self.rect.centery + 8)
        if on:
            glow = pygame.Surface((180, 180), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 240, 170, 60), (90, 90), 80)
            pygame.draw.circle(glow, (255, 240, 170, 95), (90, 90), 50)
            surface.blit(glow, (center[0] - 90, center[1] - 90))
            bulb_color = (255, 240, 170)
        else:
            bulb_color = (70, 70, 55)
        pygame.draw.circle(surface, bulb_color, center, 28)
        pygame.draw.circle(surface, C_TEXT, center, 28, 2)
        pygame.draw.rect(surface, (120, 120, 125), (center[0] - 12, center[1] + 24, 24, 15))


def find_terminal_at(pos, terminals):
    for terminal in terminals:
        if terminal.hit_test(pos):
            return terminal
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


def has_path(adj, start, target):
    return target in reachable(adj, start)


def analyze(terminals, wires, switch_module, t_src_p, t_src_n, t_fuse_in, t_fuse_out, t_sw_in, t_sw_out, t_r_in, t_r_out, t_lamp_p, t_lamp_n):
    keys = [t.key for t in terminals]
    adj = {k: set() for k in keys}

    for wire in wires:
        a, b = wire.start.key, wire.end.key
        adj[a].add(b)
        adj[b].add(a)

    # Component internal continuity
    adj[t_fuse_in.key].add(t_fuse_out.key)
    adj[t_fuse_out.key].add(t_fuse_in.key)
    adj[t_r_in.key].add(t_r_out.key)
    adj[t_r_out.key].add(t_r_in.key)
    if switch_module.closed:
        adj[t_sw_in.key].add(t_sw_out.key)
        adj[t_sw_out.key].add(t_sw_in.key)

    plus_nodes = reachable(adj, t_src_p.key)
    minus_nodes = reachable(adj, t_src_n.key)

    checks = [
        ("Fuente + a fusible", has_path(adj, t_src_p.key, t_fuse_in.key)),
        ("Fusible a switch", has_path(adj, t_fuse_out.key, t_sw_in.key)),
        ("Switch a resistencia", has_path(adj, t_sw_out.key, t_r_in.key)),
        ("Resistencia a foco +", has_path(adj, t_r_out.key, t_lamp_p.key)),
        ("Foco - a fuente -", has_path(adj, t_lamp_n.key, t_src_n.key)),
    ]

    short_circuit = t_src_n.key in plus_nodes
    objective_ok = all(ok for _, ok in checks)
    lamp_on = objective_ok and switch_module.closed and not short_circuit

    return {
        "adj": adj,
        "plus": plus_nodes,
        "minus": minus_nodes,
        "checks": checks,
        "short": short_circuit,
        "objective_ok": objective_ok,
        "lamp_on": lamp_on,
    }


def draw_controls_panel(surface, font_title, font_small, builder, wire_count):
    box = pygame.Rect(16, HEIGHT - 206, 640, 190)
    bg = pygame.Surface((box.w, box.h), pygame.SRCALPHA)
    bg.fill((26, 31, 39, 198))
    surface.blit(bg, box.topleft)
    pygame.draw.rect(surface, C_PANEL_EDGE, box, 2, border_radius=12)

    x = box.x + 14
    y = box.y + 10
    surface.blit(font_title.render("Controles", True, C_TEXT), (x, y))
    y += 24

    lines = [
        "Click izq terminal: iniciar/finalizar cable",
        "Click izq vacio: poner esquina",
        "R: modo HV/VH | Backspace: borrar esquina",
        "Click der: cancelar trazado o borrar cable",
        "C: limpiar cables | Click en switch: ON/OFF",
        "ESC: salir del simulador",
    ]

    for line in lines:
        surface.blit(font_small.render(line, True, C_DIM), (x, y))
        y += 22

    mode_txt = f"Modo: {builder.mode} | Cables: {wire_count}"
    surface.blit(font_small.render(mode_txt, True, C_TEXT), (x, box.bottom - 24))


def draw_objective_panel(surface, font_title, font_small, info, switch_closed):
    box = pygame.Rect(WIDTH - 550, HEIGHT - 206, 534, 190)
    bg = pygame.Surface((box.w, box.h), pygame.SRCALPHA)
    bg.fill((26, 31, 39, 198))
    surface.blit(bg, box.topleft)
    pygame.draw.rect(surface, C_PANEL_EDGE, box, 2, border_radius=12)

    x = box.x + 14
    y = box.y + 10
    surface.blit(font_title.render("Objetivo", True, C_TEXT), (x, y))
    y += 24

    for label, ok in info["checks"]:
        color = C_GOOD if ok else C_DIM
        prefix = "[OK]" if ok else "[  ]"
        surface.blit(font_small.render(f"{prefix} {label}", True, color), (x, y))
        y += 22

    sw = "Switch cerrado" if switch_closed else "Switch abierto"
    surface.blit(font_small.render(sw, True, C_TEXT), (x, y))
    y += 22

    if info["short"]:
        surface.blit(font_small.render("Alerta: posible corto (+ con -)", True, C_WARN), (x, y))
    elif info["lamp_on"]:
        surface.blit(font_small.render("Objetivo cumplido: foco encendido", True, C_GOOD), (x, y))
    else:
        surface.blit(font_small.render("Completa conexiones y cierra el switch", True, C_DIM), (x, y))


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
    pygame.display.set_caption("Circuito electrico - FIEE")
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("consolas", 20, bold=True)
    font_small = pygame.font.SysFont("consolas", 16)

    t_src_p = Terminal("src_p", (150, 180), "+", role="plus")
    t_src_n = Terminal("src_n", (150, 320), "-", role="minus")

    t_fuse_in = Terminal("fuse_in", (430, 190), "IN")
    t_fuse_out = Terminal("fuse_out", (610, 190), "OUT")

    t_sw_in = Terminal("sw_in", (770, 190), "IN")
    t_sw_out = Terminal("sw_out", (970, 190), "OUT")

    t_r_in = Terminal("r_in", (430, 430), "IN")
    t_r_out = Terminal("r_out", (610, 430), "OUT")

    t_lamp_p = Terminal("lamp_p", (1040, 360), "+")
    t_lamp_n = Terminal("lamp_n", (1040, 500), "-")

    source_box = ModuleBox("FUENTE DC 24V", (40, 120, 240, 260), [t_src_p, t_src_n])
    fuse_box = ModuleBox("FUSIBLE", (450, 130, 140, 120), [t_fuse_in, t_fuse_out])
    switch_box = SwitchModule("SWITCH", (790, 130, 160, 120), t_sw_in, t_sw_out)
    resistor_box = ModuleBox("RESISTENCIA", (450, 370, 140, 120), [t_r_in, t_r_out])
    lamp_box = LampModule("FOCO", (920, 300, 320, 260), t_lamp_p, t_lamp_n)

    terminals = [
        t_src_p,
        t_src_n,
        t_fuse_in,
        t_fuse_out,
        t_sw_in,
        t_sw_out,
        t_r_in,
        t_r_out,
        t_lamp_p,
        t_lamp_n,
    ]

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
                elif event.key == pygame.K_BACKSPACE:
                    builder.undo_anchor()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = screen_to_world(event.pos, render_size, offset)
                if pos is None:
                    continue
                hit_terminal = find_terminal_at(pos, terminals)

                if event.button == 1:
                    if switch_box.rect.collidepoint(pos):
                        switch_box.toggle()
                    elif builder.active:
                        if hit_terminal and hit_terminal.key != builder.start_terminal.key:
                            new_wire = builder.finish(hit_terminal)
                            if new_wire:
                                wires.append(new_wire)
                        else:
                            builder.add_anchor(pos)
                    elif hit_terminal:
                        builder.begin(hit_terminal)

                elif event.button == 3:
                    if builder.active:
                        builder.cancel()
                    else:
                        pop_wire_at(pos, wires)

        info = analyze(
            terminals,
            wires,
            switch_box,
            t_src_p,
            t_src_n,
            t_fuse_in,
            t_fuse_out,
            t_sw_in,
            t_sw_out,
            t_r_in,
            t_r_out,
            t_lamp_p,
            t_lamp_n,
        )

        draw_grid(world)

        source_box.draw(world, font_title)
        fuse_box.draw(world, font_title)
        switch_box.draw(world, font_title, font_small)
        resistor_box.draw(world, font_title)
        lamp_box.draw(world, font_title, info["lamp_on"])

        # Visual links inside modules
        pygame.draw.line(world, C_DIM, (t_fuse_in.pos[0] + 10, t_fuse_in.pos[1]), (t_fuse_out.pos[0] - 10, t_fuse_out.pos[1]), 3)
        pygame.draw.line(world, C_DIM, (t_r_in.pos[0] + 10, t_r_in.pos[1]), (t_r_out.pos[0] - 10, t_r_out.pos[1]), 3)

        for wire in wires:
            wire.draw(world, info["plus"], info["minus"])

        for terminal in terminals:
            terminal.draw(world, font_small, info["plus"], info["minus"])

        builder.draw(world, mouse_pos)

        draw_controls_panel(world, font_title, font_small, builder, len(wires))
        draw_objective_panel(world, font_title, font_small, info, switch_box.closed)

        screen.fill(C_BG)
        scaled = pygame.transform.smoothscale(world, render_size)
        screen.blit(scaled, offset)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run_simulator()
