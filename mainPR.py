import pygame
from componentesPR import Protoboard, Battery, Resistor, LED, Wire


WIDTH = 1400
HEIGHT = 800
FPS = 60



def reset_all_nodes(board, components):
    for hole in board.holes:
        hole.voltage = None

    for comp in components:
        comp.pin1.voltage = None
        comp.pin2.voltage = None


def propagate_voltage(start_node, voltage):
    stack = [start_node]
    visited = set()

    while stack:
        node = stack.pop()

        if node in visited:
            continue

        visited.add(node)
        node.voltage = voltage

        for connected in node.connected:
            stack.append(connected)
            
def find_path(start, target, visited=None):
    if visited is None:
        visited = set()

    if start == target:
        return [start]

    visited.add(start)

    for neighbor in start.connected:
        if neighbor not in visited:
            path = find_path(neighbor, target, visited)
            if path:
                return [start] + path

    return None


def main():
    pygame.init()
    font= pygame.font.SysFont("arial", 18)
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Protoboard Simulator")

    clock = pygame.time.Clock()



    protoboard = Protoboard(400, 250)

    battery = Battery(150, 300)
    resistor = Resistor(150, 450)
    led = LED(150, 600)

    components = [battery, resistor, led]

    wires = []
    creating_wire = False
    start_node = None
    
    font = pygame.font.SysFont("arial", 18)
    
    instructions = [
        "- Arrastre los componentes al protoboard con click izquierdo",
        "- Agregue cables con click derecho, elimine cables con D",
        "- Presione ESC para salir"
    ] 
    

    running = True
    while running:
        clock.tick(FPS)
        screen.fill((150, 150, 150))


        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2:
                    current_wire = None
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_d:
                    mx, my = pygame.mouse.get_pos()

                    for wire in wires[:]:
                        if wire.is_mouse_over(mx, my):
                            wires.remove(wire)
                            break

            for comp in components:
                comp.handle_event(event, protoboard)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:
                    mx, my = event.pos

                    node = protoboard.get_hole_at_position(mx, my)

                    if not node:
                        for comp in components:
                            node = comp.get_pin_at_position(mx, my)
                            if node:
                                break

                    if node:
                        if not creating_wire:
                            creating_wire = True
                            start_node = node
                        else:
                            new_wire = Wire(start_node, node)
                            wires.append(new_wire)

                            creating_wire = False
                            start_node = None


        reset_all_nodes(protoboard, components)

        propagate_voltage(battery.pin1, battery.voltage)
        propagate_voltage(battery.pin2, 0)



        led.is_on = False

        path1 = find_path(battery.pin1, resistor.pin1) or find_path(battery.pin1, resistor.pin2)
        path2 = find_path(resistor.pin1, led.pin1) or find_path(resistor.pin1, led.pin2) \
            or find_path(resistor.pin2, led.pin1) or find_path(resistor.pin2, led.pin2)
        path3 = find_path(led.pin1, battery.pin2) or find_path(led.pin2, battery.pin2)

        if path1 and path2 and path3:
            led.is_on = True



        protoboard.draw(screen)

        for wire in wires:
            wire.draw(screen)

        if creating_wire and start_node:
            mx, my = pygame.mouse.get_pos()
            pygame.draw.line(
                screen,
                (0, 200, 0),
                (start_node.x, start_node.y),
                (mx, my),
                2
            )

        for comp in components:
            comp.draw(screen,font)
            
        y_offset = HEIGHT - 70

        for line in instructions:
            text_surface = font.render(line, True, (0, 0, 0))
            text_rect = text_surface.get_rect()
            text_rect.bottomleft = (20, y_offset)
            screen.blit(text_surface, text_rect)
            y_offset += 20
            


        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()