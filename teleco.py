import pygame
import random
import math
import sys

pygame.init()

# -------------------------------------------------
# CONFIGURACIÓN
# -------------------------------------------------

WIDTH, HEIGHT = 1600, 850
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulador Red Móvil - Arquitectura 2G a 5G")

CLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont("consolas", 16)
BIG_FONT = pygame.font.SysFont("consolas", 32)

# -------------------------------------------------
# GENERATION
# -------------------------------------------------

class Generation:
    def __init__(self, name, capacity, latency, color):
        self.name = name
        self.capacity = capacity
        self.latency = latency
        self.color = color

    def apply(self, network):
        network.generation = self

# -------------------------------------------------
# USER
# -------------------------------------------------

class User:
    def __init__(self, x=None, y=None):
        self.x = x if x else random.randint(100, 800)
        self.y = y if y else random.randint(100, 700)
        self.speed = random.uniform(0.5, 1.5)
        self.traffic = random.randint(5, 25)
        self.connected = None

    def move(self):
        self.x += random.uniform(-1, 1) * self.speed
        self.y += random.uniform(-1, 1) * self.speed

    def update_traffic(self):
        self.traffic = random.randint(5, 25)

    def draw(self):
        pygame.draw.circle(screen, (0, 200, 255),
                           (int(self.x), int(self.y)), 5)

# -------------------------------------------------
# BASE STATION
# -------------------------------------------------

class BaseStation:
    def __init__(self, x, y, coverage):
        self.x = x
        self.y = y
        self.coverage = coverage
        self.connected_users = []

    def distance(self, user):
        return math.hypot(self.x - user.x, self.y - user.y)

    def reset(self):
        self.connected_users.clear()

    def connect(self, user):
        if self.distance(user) <= self.coverage:
            self.connected_users.append(user)
            user.connected = self

    def total_traffic(self):
        return sum(u.traffic for u in self.connected_users)

    def draw(self, color, selected=False):
        pygame.draw.circle(screen, (60,100,60),
                           (self.x, self.y), self.coverage, 1)
        radius = 18 if selected else 14
        pygame.draw.circle(screen, color,
                           (self.x, self.y), radius)

class MacroCell(BaseStation):
    def __init__(self, x, y):
        super().__init__(x, y, 250)

class SmallCell(BaseStation):
    def __init__(self, x, y):
        super().__init__(x, y, 120)

# -------------------------------------------------
# RAN
# -------------------------------------------------

class RAN:
    def __init__(self):
        self.stations = []
        self.users = []

    def add_station(self, station):
        self.stations.append(station)

    def add_user(self, user):
        self.users.append(user)

    def remove_user_near(self, x, y):
        for user in self.users:
            if math.hypot(user.x - x, user.y - y) < 10:
                self.users.remove(user)
                break

    def update(self):
        for station in self.stations:
            station.reset()

        for user in self.users:
            user.move()
            user.update_traffic()

            if self.stations:
                closest = min(self.stations,
                              key=lambda s: s.distance(user))
                if closest.distance(user) <= closest.coverage:
                    closest.connect(user)
                else:
                    user.connected = None

    def draw(self, color, selected_station):
        for station in self.stations:
            station.draw(color, station == selected_station)

        for user in self.users:
            if user.connected:
                pygame.draw.line(screen, (150,150,255),
                                 (user.x, user.y),
                                 (user.connected.x,
                                  user.connected.y), 1)
            user.draw()

    def total_traffic(self):
        return sum(s.total_traffic() for s in self.stations)

# -------------------------------------------------
# NETWORK
# -------------------------------------------------

class Network:
    def __init__(self):
        self.ran = RAN()
        self.generation = None
        self.selected_station = None

    def update(self):
        self.ran.update()

    def draw_architecture(self):
        color = self.generation.color

        if self.generation.name == "2G":
            labels = ["BTS", "BSC", "MSC"]
        elif self.generation.name == "3G":
            labels = ["NodeB", "RNC", "Core"]
        elif self.generation.name == "4G":
            labels = ["eNodeB", "MME", "SGW", "PGW"]
        elif self.generation.name == "5G":
            labels = ["gNodeB", "AMF", "SMF", "UPF", "Edge"]

        start_x = 850
        y = 450

        title = BIG_FONT.render(
            f"{self.generation.name} Architecture",
            True, (255,255,255)
        )
        screen.blit(title, (850, 350))

        for i, label in enumerate(labels):
            x = start_x + i * 160

            pygame.draw.rect(screen, color,
                             (x, y, 130, 60),
                             border_radius=12)

            text = FONT.render(label, True, (255,255,255))
            text_rect = text.get_rect(center=(x+65, y+30))
            screen.blit(text, text_rect)

            if i > 0:
                pygame.draw.line(screen,
                                 (200,200,255),
                                 (x-30, y+30),
                                 (x, y+30), 3)

    def draw(self):
        self.ran.draw(self.generation.color,
                      self.selected_station)
        self.draw_architecture()

    def metrics(self):
        traffic = self.ran.total_traffic()
        return traffic, self.generation.capacity, self.generation.latency

# -------------------------------------------------
# GENERACIONES
# -------------------------------------------------

gen2G = Generation("2G",100,150,(160,160,160))
gen3G = Generation("3G",250,80,(0,150,255))
gen4G = Generation("4G",500,30,(0,220,150))
gen5G = Generation("5G",1200,5,(200,0,255))

generations = [gen2G, gen3G, gen4G, gen5G]
current_gen_index = 3

# -------------------------------------------------
# INICIALIZAR RED
# -------------------------------------------------

network = Network()

network.ran.add_station(MacroCell(300,300))
network.ran.add_station(MacroCell(300,600))
network.ran.add_station(SmallCell(600,450))

for _ in range(40):
    network.ran.add_user(User())

generations[current_gen_index].apply(network)

GENERATION_CHANGE_TIME = 8000
last_generation_change = pygame.time.get_ticks()

# -------------------------------------------------
# LOOP PRINCIPAL
# -------------------------------------------------

running = True

while running:
    CLOCK.tick(60)
    screen.fill((20,30,50))

    current_time = pygame.time.get_ticks()

    if current_time - last_generation_change > GENERATION_CHANGE_TIME:
        current_gen_index = (current_gen_index + 1) % len(generations)
        generations[current_gen_index].apply(network)
        last_generation_change = current_time

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                current_gen_index = (current_gen_index + 1) % len(generations)
                generations[current_gen_index].apply(network)

            if event.key == pygame.K_a:
                for _ in range(10):
                    network.ran.add_user(User())

            if event.key == pygame.K_c:
                network.ran.users.clear()

            if event.key == pygame.K_m:
                x,y = pygame.mouse.get_pos()
                network.ran.add_station(MacroCell(x,y))

            if event.key == pygame.K_s:
                x,y = pygame.mouse.get_pos()
                network.ran.add_station(SmallCell(x,y))

            if event.key == pygame.K_ESCAPE:
                running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx,my = pygame.mouse.get_pos()

            if event.button == 1:
                for station in network.ran.stations:
                    if math.hypot(station.x-mx,
                                  station.y-my) < 20:
                        network.selected_station = station
                        break
                else:
                    network.ran.add_user(User(mx,my))

            if event.button == 3:
                network.ran.remove_user_near(mx,my)

        if event.type == pygame.MOUSEBUTTONUP:
            network.selected_station = None

    if network.selected_station:
        network.selected_station.x, \
        network.selected_station.y = pygame.mouse.get_pos()

    network.update()
    network.draw()

    traffic, capacity, latency = network.metrics()

    info = [
        f"Generación: {network.generation.name}",
        f"Usuarios: {len(network.ran.users)}",
        f"Tráfico: {traffic} Mbps",
        f"Capacidad: {capacity} Mbps",
        f"Latencia: {latency} ms"
    ]

    y=20
    for line in info:
        text = FONT.render(line,True,(255,255,255))
        screen.blit(text,(20,y))
        y+=22

    if traffic > capacity:
        warning = BIG_FONT.render("⚠ RED SATURADA ⚠",
                                  True,(255,80,80))
        screen.blit(warning,(20,y+10))

    pygame.display.flip()

pygame.quit()
sys.exit()