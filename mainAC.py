import pygame
import sys
from componentesAC import GestorComponentes

class Boton:
    def __init__(self, texto, x, y, ancho, alto, accion):
        self.texto = texto
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.color_normal = (60, 60, 60)
        self.color_hover = (100, 100, 100)
        self.color_actual = self.color_normal
        self.accion = accion
        self.fuente = pygame.font.SysFont("arial", 24)

    def dibujar(self, pantalla):
        pygame.draw.rect(pantalla, self.color_actual, self.rect)
        pygame.draw.rect(pantalla, (255, 255, 255), self.rect, 2)
        texto_render = self.fuente.render(self.texto, True, (255, 255, 255))
        texto_rect = texto_render.get_rect(center=self.rect.center)
        pantalla.blit(texto_render, texto_rect)

    def actualizar(self, mouse_pos):
        self.color_actual = self.color_hover if self.rect.collidepoint(mouse_pos) else self.color_normal

    def manejar_evento(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(evento.pos):
            self.accion(self.texto)

class Juego:
    def __init__(self):
        pygame.init()
        self.pantalla = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.ancho, self.alto = self.pantalla.get_size()
        pygame.display.set_caption("Adivina el componente")
        self.clock = pygame.time.Clock()

        self.fuente_titulo = pygame.font.SysFont("arial", 50)
        self.fuente_subtitulo = pygame.font.SysFont("arial", 30)
        self.fuente_instrucciones = pygame.font.SysFont("arial", 20)
        self.fuente_feedback = pygame.font.SysFont("arial", 40)

        self.gestor = GestorComponentes()
        self.componente_actual = None
        self.botones = []
        self.feedback = ""
        self.color_feedback = (255, 255, 255)
        self.estado = "jugando"
        self.mostrar_correcto_hasta = 0
        self.siguiente_componente()

    def siguiente_componente(self):
        self.componente_actual = self.gestor.obtener_siguiente()
        if self.componente_actual is None:
            self.estado = "fin"
            return

        opciones = self.gestor.generar_opciones(self.componente_actual)
        self.botones = []

        ancho_boton = 300
        alto_boton = 60
        espacio = 20
        inicio_y = self.alto // 3

        for i, opcion in enumerate(opciones):
            x = self.ancho - 400
            y = inicio_y + i * (alto_boton + espacio)
            self.botones.append(Boton(opcion, x, y, ancho_boton, alto_boton, self.verificar_respuesta))
        self.feedback = ""

    def verificar_respuesta(self, texto_boton):
        if texto_boton == self.componente_actual.get_nombre():
            self.feedback = "Correcto! :D"
            self.color_feedback = (0, 200, 0)
            self.mostrar_correcto_hasta = pygame.time.get_ticks() + 3000
        else:
            self.feedback = "Incorrecto, inténtelo de nuevo"
            self.color_feedback = (200, 0, 0)

    def manejar_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            for boton in self.botones:
                boton.manejar_evento(evento)

    def actualizar(self):
        mouse_pos = pygame.mouse.get_pos()
        for boton in self.botones:
            boton.actualizar(mouse_pos)
            
        if self.mostrar_correcto_hasta != 0 and pygame.time.get_ticks() > self.mostrar_correcto_hasta:
            self.mostrar_correcto_hasta = 0
            self.siguiente_componente()

    def dibujar(self):
        self.pantalla.fill((0, 0, 0))
        if self.estado == "fin":
            texto = self.fuente_feedback.render("¡Terminaste!", True, (0, 255, 0))
            rect = texto.get_rect(center=(self.ancho // 2, self.alto // 2))
            self.pantalla.blit(texto, rect)
            
            instruccion_fin = self.fuente_subtitulo.render("Presione ESC para salir", True, (255, 255, 255))
            rect_instr = instruccion_fin.get_rect(center=(self.ancho // 2, self.alto // 2 + 50))
            self.pantalla.blit(instruccion_fin, rect_instr)
            
            pygame.display.flip()
            return

        titulo = self.fuente_titulo.render("¿Qué componente es?", True, (255, 255, 255))
        self.pantalla.blit(titulo, titulo.get_rect(center=(self.ancho // 3, 200)))

        subtitulo = self.fuente_subtitulo.render("Elija una opción:", True, (255, 255, 255))
        self.pantalla.blit(subtitulo, subtitulo.get_rect(center=(self.ancho - 250, 200)))

        imagen = self.componente_actual.get_imagen()
        imagen_rect = imagen.get_rect(center=(self.ancho // 3, self.alto // 2))
        self.pantalla.blit(imagen, imagen_rect)

        for boton in self.botones:
            boton.dibujar(self.pantalla)

        if self.feedback:
            texto_render = self.fuente_feedback.render(self.feedback, True, self.color_feedback)
            self.pantalla.blit(texto_render, texto_render.get_rect(center=(self.ancho // 2, 80)))

            if self.feedback == "Correcto! :D":
                descripcion_texto = self.componente_actual.get_descripcion()
                descripcion_render = self.fuente_subtitulo.render(descripcion_texto, True, (255, 255, 255))
                self.pantalla.blit(descripcion_render, descripcion_render.get_rect(center=(self.ancho // 2, 130)))

        instrucciones = self.fuente_instrucciones.render(
            "- Presione ESC para salir     - Escoja la opción correcta con click izquierdo", True, (180, 180, 180))
        self.pantalla.blit(instrucciones, instrucciones.get_rect(bottomleft=(20, self.alto - 20)))

        pygame.display.flip()

    def ejecutar(self):
        while True:
            self.clock.tick(60)
            self.manejar_eventos()
            self.actualizar()
            self.dibujar()

if __name__ == "__main__":
    juego = Juego()
    juego.ejecutar()