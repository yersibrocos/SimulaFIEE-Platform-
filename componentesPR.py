import pygame


class Node:
    def __init__(self, x=None, y=None):
        self.x = x
        self.y = y
        self.connected = []
        self.voltage = None

    def connect(self, other):
        if other not in self.connected:
            self.connected.append(other)
        if self not in other.connected:
            other.connected.append(self)

    def __hash__(self):
        return id(self)



class Hole(Node):
    def __init__(self, x, y,color=(50, 50, 50)):
        super().__init__(x, y)
        self.color=color

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (self.x, self.y), 4)




class Protoboard:
    def __init__(self, x, y):
        self.x = x
        self.y = y

        self.cell_size = 20
        self.middle_gap = 40

        self.rows_per_side = 5
        self.cols = 30

        self.holes = []

        self.create_power_rails()
        self.create_main_area()
        self.connect_internal_groups()



    def create_power_rails(self):
        self.top_rail = []
        self.bottom_rail = []

        for col in range(self.cols):
            hx = self.x + col * self.cell_size

            top_y = self.y - 60
            bottom_y = self.y + 5 * self.cell_size * 2 + self.middle_gap + 60
            
            top_hole = Hole(hx, top_y, (255, 0, 0))      # rojo (+)
            bottom_hole = Hole(hx, bottom_y, (0, 0, 255)) # azul (-)

            self.top_rail.append(top_hole)
            self.bottom_rail.append(bottom_hole)

            self.holes.append(top_hole)
            self.holes.append(bottom_hole)

        for rail in [self.top_rail, self.bottom_rail]:
            for hole in rail:
                for other in rail:
                    hole.connect(other)

    def create_main_area(self):
        self.main_top = []
        self.main_bottom = []

        for row in range(self.rows_per_side):
            row_list = []
            for col in range(self.cols):
                hx = self.x + col * self.cell_size
                hy = self.y + row * self.cell_size

                hole = Hole(hx, hy)
                row_list.append(hole)
                self.holes.append(hole)

            self.main_top.append(row_list)

        for row in range(self.rows_per_side):
            row_list = []
            for col in range(self.cols):
                hx = self.x + col * self.cell_size
                hy = (
                    self.y
                    + self.rows_per_side * self.cell_size
                    + self.middle_gap
                    + row * self.cell_size
                )

                hole = Hole(hx, hy)
                row_list.append(hole)
                self.holes.append(hole)

            self.main_bottom.append(row_list)

    def connect_internal_groups(self):
        for section in [self.main_top, self.main_bottom]:
            for row in section:
                for i in range(0, self.cols, 5):
                    group = row[i:i + 5]
                    for hole in group:
                        for other in group:
                            hole.connect(other)


    def draw(self, screen):
        for hole in self.holes:
            hole.draw(screen)

    def get_hole_at_position(self, x, y):
        for hole in self.holes:
            if (hole.x - x) ** 2 + (hole.y - y) ** 2 < 100:
                return hole
        return None

    def get_nearest_hole(self, x, y):
        min_dist = float("inf")
        nearest = None

        for hole in self.holes:
            dist = (hole.x - x) ** 2 + (hole.y - y) ** 2
            if dist < min_dist and dist < 400:
                min_dist = dist
                nearest = hole

        return nearest



class Component:
    def __init__(self, x, y):
        self.x = x
        self.y = y

        self.width = 60
        self.height = 30

        self.dragging = False
        self.offset_x = 0
        self.offset_y = 0

        self.pin1 = Node()
        self.pin2 = Node()
        
        self.label=""


    def handle_event(self, event, board=None):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if self.is_mouse_over(mx, my):
                self.dragging = True
                self.offset_x = self.x - mx
                self.offset_y = self.y - my

        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
            if board:
                self.snap_to_board(board)

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            mx, my = event.pos
            self.x = mx + self.offset_x
            self.y = my + self.offset_y

    def is_mouse_over(self, mx, my):
        return (
            self.x - self.width // 2 < mx < self.x + self.width // 2
            and self.y - self.height // 2 < my < self.y + self.height // 2
        )



    def snap_to_board(self, board):
        self.update_leads()

        h1 = board.get_nearest_hole(*self.lead1)
        h2 = board.get_nearest_hole(*self.lead2)

        if h1:
            self.pin1.connect(h1)

        if h2:
            self.pin2.connect(h2)



    def get_pin_at_position(self, x, y):
        for pin in [self.pin1, self.pin2]:
            if pin.x is None or pin.y is None:
                continue

            if (pin.x - x) ** 2 + (pin.y - y) ** 2 < 100:
                return pin
        return None



    def update_leads(self):
        self.lead1 = (self.x - self.width // 2, self.y)
        self.lead2 = (self.x + self.width // 2, self.y)

        self.pin1.x, self.pin1.y = self.lead1
        self.pin2.x, self.pin2.y = self.lead2
        


    def draw(self, screen):
        pass




class Battery(Component):
    def __init__(self, x, y, voltage=9):
        super().__init__(x, y)
        self.voltage = voltage
        self.width = 40
        self.height = 160

    def update_leads(self):
        self.lead1 = (self.x, self.y - self.height // 2)
        self.lead2 = (self.x, self.y + self.height // 2)

        self.pin1.x, self.pin1.y = self.lead1
        self.pin2.x, self.pin2.y = self.lead2

    def draw(self, screen, font):
        self.update_leads()

        pygame.draw.rect(
            screen,
            (120, 120, 120),
            (self.x - self.width // 2,
             self.y - self.height // 2,
             self.width,
             self.height)
        )

        pygame.draw.circle(screen, (200, 0, 0), (self.pin1.x, self.pin1.y), 6)
        pygame.draw.circle(screen, (0, 0, 0), (self.pin2.x, self.pin2.y), 6)
        
        label = font.render("B", True, (0, 0, 0))
        label_rect = label.get_rect(center=(self.x, self.y))
        screen.blit(label, label_rect)
        
        



class Resistor(Component):
    def __init__(self, x, y, resistance=220):
        super().__init__(x, y)
        self.resistance = resistance
        self.width = 100

    def draw(self, screen, font):
        self.update_leads()

        pygame.draw.line(screen, (0, 0, 0),
                         (self.pin1.x, self.pin1.y),
                         (self.x - 20, self.y), 2)

        pygame.draw.line(screen, (0, 0, 0),
                         (self.x + 20, self.y),
                         (self.pin2.x, self.pin2.y), 2)

        pygame.draw.rect(
            screen,
            (200, 180, 120),
            (self.x - 20, self.y - 10, 40, 20)
        )
        
        label = font.render("R", True, (0, 0, 0))
        label_rect = label.get_rect(center=(self.x, self.y))
        screen.blit(label, label_rect)
        




class LED(Component):
    def __init__(self, x, y, forward_voltage=2.0):
        super().__init__(x, y)
        self.forward_voltage = forward_voltage
        self.is_on = False
        self.width = 60

    def draw(self, screen, font):
        self.update_leads()

        pygame.draw.line(screen, (0, 0, 0),
                         (self.pin1.x, self.pin1.y),
                         (self.x - 12, self.y), 2)

        pygame.draw.line(screen, (0, 0, 0),
                         (self.x + 12, self.y),
                         (self.pin2.x, self.pin2.y), 2)

        color = (255, 0, 0) if self.is_on else (100, 0, 0)

        pygame.draw.circle(screen, color, (self.x, self.y), 12)
        
        label = font.render("L", True, (255, 255, 255))
        label_rect = label.get_rect(center=(self.x, self.y))
        screen.blit(label, label_rect)
        




class Wire:
    def __init__(self, node1, node2):
        self.node1 = node1
        self.node2 = node2

        node1.connect(node2)

    def draw(self, screen):
        pygame.draw.line(
            screen,
            (0, 150, 0),
            (self.node1.x, self.node1.y),
            (self.node2.x, self.node2.y),
            3
        )
    
    def is_mouse_over(self, x, y):
        x1, y1 = self.node1.x, self.node1.y
        x2, y2 = self.node2.x, self.node2.y

        if x1 is None or x2 is None:
            return False

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return False

        t = ((x - x1) * dx + (y - y1) * dy) / (dx*dx + dy*dy)

        t = max(0, min(1, t))

        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        distance_sq = (x - closest_x)**2 + (y - closest_y)**2

        return distance_sq < 100  #sensibilidsd