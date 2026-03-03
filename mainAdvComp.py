import pygame
import os
import random

pygame.init()

class ComponenteSimulador:
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("Adivina el Componente")

        self.font = pygame.font.SysFont(None, 40)
        self.big_font = pygame.font.SysFont(None, 60)

        self.clock = pygame.time.Clock()

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_folder = os.path.join(self.base_dir, "componentes")

        self.images = self.cargar_imagenes()
        random.shuffle(self.images)

        self.current_index = 0
        self.user_text = ""
        self.feedback = ""
        self.finished = False
        self.running = True

    def cargar_imagenes(self):
        images = []
        for file in os.listdir(self.image_folder):
            if file.endswith(".png") or file.endswith(".jpg"):
                path = os.path.join(self.image_folder, file)
                image = pygame.image.load(path)
                image = pygame.transform.scale(image, (300, 300))
                name = os.path.splitext(file)[0].lower()
                images.append((image, name))
        return images

    def verificar_respuesta(self):
        correct_name = self.images[self.current_index][1]
        if self.user_text.lower() == correct_name:
            self.feedback = "Correcto!"
            self.current_index += 1
            self.user_text = ""
            if self.current_index >= len(self.images):
                self.finished = True
        else:
            self.feedback = "Incorrecto, intenta otra vez"
            self.user_text = ""

    def manejar_eventos(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.KEYDOWN and not self.finished:
                if event.key == pygame.K_RETURN:
                    self.verificar_respuesta()
                elif event.key == pygame.K_BACKSPACE:
                    self.user_text = self.user_text[:-1]
                else:
                    self.user_text += event.unicode

    def draw(self):
        self.screen.fill((30, 30, 30))

        if not self.finished:
            image, _ = self.images[self.current_index]
            self.screen.blit(image, (self.width//2 - 150, 100))

            label = self.font.render("Escribe el nombre (en minúscula):", True, (255, 255, 255))
            self.screen.blit(label, (self.width//2 - 150, 420))

            input_text = self.font.render(self.user_text, True, (0, 255, 0))
            self.screen.blit(input_text, (self.width//2 - 150, 460))

            feedback_text = self.font.render(self.feedback, True, (255, 100, 100))
            self.screen.blit(feedback_text, (self.width//2 - 150, 500))
        else:
            win_text = self.big_font.render("Terminaste!", True, (0, 255, 0))
            self.screen.blit(win_text, (self.width//2 - 150, self.height//2 - 30))

        pygame.display.flip()

    def run(self):
        while self.running:
            self.manejar_eventos()
            self.draw()
            self.clock.tick(60)

        pygame.quit()


if __name__ == "__main__":
    simulador = ComponenteSimulador()
    simulador.run()