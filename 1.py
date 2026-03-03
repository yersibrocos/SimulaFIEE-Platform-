import pygame
import random
import sys

pygame.init()

# ---------------- CONFIG ----------------
WIDTH, HEIGHT = 1400, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulador Telecom - 5G + Fibra Óptica")

FONT = pygame.font.SysFont("consolas", 18)
CLOCK = pygame.time.Clock()

# ---------------- COLORES ----------------
BLACK = (20, 20, 20)
WHITE = (230, 230, 230)
GREEN = (0, 255, 0)
RED = (220, 60, 60)
YELLOW = (255, 200, 0)
BLUE = (0, 150, 255)
PURPLE = (160, 80, 255)

# ==========================================================
# -------------------- CLASES TELECOM ----------------------
# ==========================================================

class UserDevice:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.base_demand = random.randint(5, 25)

    def generate_traffic(self):
        return max(1, self.base_demand + random.randint(-5, 5))

    def draw(self):
        pygame.draw.circle(screen, BLUE, (self.x, self.y), 8)


class Packet:
    def __init__(self, start_pos, end_pos, speed=3):
        self.x, self.y = start_pos
        self.end_x, self.end_y = end_pos
        self.speed = speed
        self.finished = False

    def update(self):
        dx = self.end_x - self.x
        dy = self.end_y - self.y
        dist = (dx**2 + dy**2) ** 0.5
        if dist < self.speed:
            self.finished = True
        else:
            self.x += self.speed * dx / dist
            self.y += self.speed * dy / dist

    def draw(self):
        pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), 4)


class Antenna5G:
    def __init__(self, x, y, capacity):
        self.x = x
        self.y = y
        self.capacity = capacity
        self.users = []

    def connect_user(self, user):
        self.users.append(user)

    def total_traffic(self):
        return sum(user.generate_traffic() for user in self.users)

    def is_congested(self, traffic):
        return traffic > self.capacity

    def draw(self):
        pygame.draw.rect(screen, GREEN, (self.x - 15, self.y - 40, 30, 80))


class FiberLink:
    def __init__(self, capacity, distance_km):
        self.capacity = capacity
        self.distance = distance_km

    def latency_ms(self):
        return round(self.distance * 0.005, 3)

    def is_saturated(self, traffic):
        return traffic > self.capacity


class CoreNetwork:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.received = 0

    def receive(self, traffic):
        self.received += traffic

    def draw(self):
        pygame.draw.rect(screen, PURPLE, (self.x - 30, self.y - 30, 60, 60))


# ==========================================================
# -------------------- INICIALIZACIÓN ----------------------
# ==========================================================

antenna = Antenna5G(500, 400, capacity=300)
fiber = FiberLink(capacity=800, distance_km=20)
core = CoreNetwork(1000, 400)

users = []
packets = []

for i in range(25):
    x = random.randint(100, 400)
    y = random.randint(150, 650)
    user = UserDevice(x, y)
    users.append(user)
    antenna.connect_user(user)

# ==========================================================
# -------------------- GAME LOOP ---------------------------
# ==========================================================

running = True
while running:
    CLOCK.tick(60)
    screen.fill(BLACK)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # ---------------- SIMULACIÓN ----------------

    traffic = antenna.total_traffic()
    antenna_congested = antenna.is_congested(traffic)
    fiber_saturated = fiber.is_saturated(traffic)

    core.receive(traffic)

    # Generar paquetes visuales
    if random.random() < 0.3:
        user = random.choice(users)
        packets.append(Packet((user.x, user.y), (antenna.x, antenna.y)))

    if random.random() < 0.2:
        packets.append(Packet((antenna.x, antenna.y), (core.x, core.y)))

    # Actualizar paquetes
    for packet in packets:
        packet.update()

    packets = [p for p in packets if not p.finished]

    # ---------------- DIBUJO ----------------

    # Dibujar enlaces
    pygame.draw.line(screen, WHITE, (antenna.x, antenna.y),
                     (core.x, core.y), 3)

    # Dibujar usuarios
    for user in users:
        user.draw()
        pygame.draw.line(screen, WHITE, (user.x, user.y),
                         (antenna.x, antenna.y), 1)

    # Dibujar antena y core
    antenna.draw()
    core.draw()

    # Dibujar paquetes
    for packet in packets:
        packet.draw()

    # ---------------- PANEL INFO ----------------

    info_x = 50
    info_y = 50

    info_lines = [
        "SIMULACION RED 5G + FIBRA",
        f"Usuarios conectados: {len(users)}",
        f"Tráfico generado: {traffic} Mbps",
        f"Capacidad Antena: {antenna.capacity} Mbps",
        f"Antena congestionada: {'SI' if antenna_congested else 'NO'}",
        f"Capacidad Fibra: {fiber.capacity} Mbps",
        f"Fibra saturada: {'SI' if fiber_saturated else 'NO'}",
        f"Latencia estimada fibra: {fiber.latency_ms()} ms",
        f"Tráfico acumulado en Core: {int(core.received)} Mbps"
    ]

    y = info_y
    for line in info_lines:
        color = GREEN
        if "SI" in line:
            color = RED
        screen.blit(FONT.render(line, True, color), (info_x, y))
        y += 25

    pygame.display.flip()

pygame.quit()
sys.exit()