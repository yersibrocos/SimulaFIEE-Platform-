import pygame
import random
import math
import sys

pygame.init()

info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Mobile Network Simulator")

CLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont("consolas", 16)
BIG_FONT = pygame.font.SysFont("consolas", 32)


class Generation:

    def __init__(self, name, capacity, latency, color):
        self.name = name
        self.capacity = capacity
        self.latency = latency
        self.color = color

    def apply(self, network):
        network.generation = self


class User:

    def __init__(self, x=None, y=None):
        self.x = x if x else random.randint(100, WIDTH//2)
        self.y = y if y else random.randint(100, HEIGHT-100)
        self.speed = random.uniform(0.5, 1.5)
        self.traffic = random.randint(5, 25)
        self.connected = None

    def move(self):
        self.x += random.uniform(-1, 1) * self.speed
        self.y += random.uniform(-1, 1) * self.speed

    def update_traffic(self):
        self.traffic = random.randint(5, 25)

    def draw(self):
        pygame.draw.circle(screen, (0, 200, 255), (int(self.x), int(self.y)), 5)


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

    def draw(self, color, selected):
        pygame.draw.circle(screen, (60, 100, 60), (int(self.x), int(self.y)), self.coverage, 1)
        r = 18 if selected else 14
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), r)


class MacroCell(BaseStation):

    def __init__(self, x, y):
        super().__init__(x, y, 250)


class SmallCell(BaseStation):

    def __init__(self, x, y):
        super().__init__(x, y, 120)


class RAN:

    def __init__(self):
        self.stations = []
        self.users = []

    def add_station(self, station):
        self.stations.append(station)

    def add_user(self, user):
        self.users.append(user)

    def remove_user_near(self, x, y):
        for u in self.users:
            if math.hypot(u.x - x, u.y - y) < 10:
                self.users.remove(u)
                break

    def update(self):
        for s in self.stations:
            s.reset()

        for u in self.users:
            u.move()
            u.update_traffic()

            if self.stations:
                closest = min(self.stations, key=lambda s: s.distance(u))
                if closest.distance(u) <= closest.coverage:
                    closest.connect(u)
                else:
                    u.connected = None

    def draw(self, color, selected):
        for s in self.stations:
            s.draw(color, s == selected)

        for u in self.users:
            if u.connected:
                pygame.draw.line(screen, (150, 150, 255),
                                 (u.x, u.y),
                                 (u.connected.x, u.connected.y), 1)
            u.draw()

    def traffic(self):
        return sum(s.total_traffic() for s in self.stations)


class ArchitectureView:

    def draw(self, generation):

        if generation.name == "2G":
            labels = ["BTS", "BSC", "MSC"]
        elif generation.name == "3G":
            labels = ["NodeB", "RNC", "Core"]
        elif generation.name == "4G":
            labels = ["eNodeB", "MME", "SGW", "PGW"]
        else:
            labels = ["gNodeB", "AMF", "SMF", "UPF", "Edge"]

        start_x = int(WIDTH * 0.55)
        y = int(HEIGHT * 0.55)

        title = BIG_FONT.render(generation.name + " Architecture", True, (255, 255, 255))
        screen.blit(title, (start_x, y - 100))

        for i, label in enumerate(labels):

            x = start_x + i * 160

            pygame.draw.rect(screen, generation.color, (x, y, 130, 60), border_radius=12)

            t = FONT.render(label, True, (255, 255, 255))
            rect = t.get_rect(center=(x + 65, y + 30))
            screen.blit(t, rect)

            if i > 0:
                pygame.draw.line(screen, (200, 200, 255), (x - 30, y + 30), (x, y + 30), 3)


class InstructionPanel:

    def __init__(self):
        self.visible = True

    def toggle(self):
        self.visible = not self.visible

    def draw(self):

        if not self.visible:
            return

        lines = [
            "CONTROLS",
            "SPACE Change generation",
            "A Add users",
            "C Clear users",
            "Left Click Create user",
            "Right Click Remove user",
            "M Macro cell",
            "S Small cell",
            "Drag station Move",
            "H Toggle help",
            "ESC Exit"
        ]

        pygame.draw.rect(screen, (10, 20, 35),
                         (10, HEIGHT - 230, 420, 220), border_radius=10)

        y = HEIGHT - 220

        for l in lines:
            t = FONT.render(l, True, (200, 200, 255))
            screen.blit(t, (20, y))
            y += 20


class StatsPanel:

    def draw(self, network):

        traffic = network.ran.traffic()

        info = [
            "Generation: " + network.generation.name,
            "Users: " + str(len(network.ran.users)),
            "Traffic: " + str(traffic) + " Mbps",
            "Capacity: " + str(network.generation.capacity) + " Mbps",
            "Latency: " + str(network.generation.latency) + " ms"
        ]

        y = 20

        for line in info:
            t = FONT.render(line, True, (255, 255, 255))
            screen.blit(t, (20, y))
            y += 22

        if traffic > network.generation.capacity:
            w = BIG_FONT.render("NETWORK SATURATED", True, (255, 80, 80))
            screen.blit(w, (20, y + 10))


class Network:

    def __init__(self):
        self.ran = RAN()
        self.generation = None
        self.selected = None

    def update(self):
        self.ran.update()

    def draw(self):
        self.ran.draw(self.generation.color, self.selected)


class Simulation:

    def __init__(self):

        self.network = Network()
        self.architecture = ArchitectureView()
        self.instructions = InstructionPanel()
        self.stats = StatsPanel()

        self.generations = [
            Generation("2G", 100, 150, (160, 160, 160)),
            Generation("3G", 250, 80, (0, 150, 255)),
            Generation("4G", 500, 30, (0, 220, 150)),
            Generation("5G", 1200, 5, (200, 0, 255))
        ]

        self.index = 3
        self.generations[self.index].apply(self.network)

        self.network.ran.add_station(MacroCell(300, 300))
        self.network.ran.add_station(MacroCell(300, 600))
        self.network.ran.add_station(SmallCell(600, 450))

        for _ in range(40):
            self.network.ran.add_user(User())

    def change_generation(self):
        self.index = (self.index + 1) % len(self.generations)
        self.generations[self.index].apply(self.network)

    def events(self):

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_SPACE:
                    self.change_generation()

                if event.key == pygame.K_a:
                    for _ in range(10):
                        self.network.ran.add_user(User())

                if event.key == pygame.K_c:
                    self.network.ran.users.clear()

                if event.key == pygame.K_m:
                    x, y = pygame.mouse.get_pos()
                    self.network.ran.add_station(MacroCell(x, y))

                if event.key == pygame.K_s:
                    x, y = pygame.mouse.get_pos()
                    self.network.ran.add_station(SmallCell(x, y))

                if event.key == pygame.K_h:
                    self.instructions.toggle()

                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:

                mx, my = pygame.mouse.get_pos()

                if event.button == 1:

                    for s in self.network.ran.stations:
                        if math.hypot(s.x - mx, s.y - my) < 20:
                            self.network.selected = s
                            break
                    else:
                        self.network.ran.add_user(User(mx, my))

                if event.button == 3:
                    self.network.ran.remove_user_near(mx, my)

            if event.type == pygame.MOUSEBUTTONUP:
                self.network.selected = None

    def update(self):

        if self.network.selected:
            self.network.selected.x, self.network.selected.y = pygame.mouse.get_pos()

        self.network.update()

    def draw(self):

        screen.fill((20, 30, 50))

        self.network.draw()

        self.architecture.draw(self.network.generation)

        self.stats.draw(self.network)

        self.instructions.draw()

        pygame.display.flip()

    def run(self):

        while True:

            CLOCK.tick(60)

            self.events()

            self.update()

            self.draw()


Simulation().run()