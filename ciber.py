import pygame
import random

pygame.init()
from display_mode import apply_display_mode

# ---------------- CONFIG ----------------
WIDTH, HEIGHT = 1280, 720
screen = apply_display_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulador de Ciberseguridad - Nivel 1")

FONT = pygame.font.SysFont("consolas", 18)
CLOCK = pygame.time.Clock()

# ---------------- COLORES ----------------
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
GRAY = (40, 40, 40)
RED = (200, 50, 50)
WHITE = (200, 200, 200)
YELLOW = (220, 180, 0)

# ---------------- UTILIDADES ----------------
PORT_NAMES = {
    22: "SSH",
    80: "HTTP",
    443: "HTTPS",
    3306: "DB"
}

ATTACK_LABELS = {
    "bruteforce": "fuerza bruta",
    "scan": "escaneo de puertos",
    "exploit": "exploit remoto",
    "phishing": "phishing",
    "malware": "malware",
    "ddos": "DDoS"
}

def is_valid_ip(ip):
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit():
            return False
        value = int(part)
        if value < 0 or value > 255:
            return False
    return True

def random_ip():
    return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

def pick_user(users):
    return random.choice(users)

# ---------------- SERVER ----------------
class Server:
    def __init__(self, max_logs=200):
        self.firewall = False
        self.ids = False
        self.rate_limit = False
        self.isolated = False
        self.compromised = False
        self.malware = False
        self.ddos_active = False
        self.health = 100
        self.logs = []
        self.max_logs = max_logs
        self.patches_until_ms = 0
        self.last_backup_ms = None
        self.next_recovery_ms = 0
        self.degraded_warned = False
        self.down_reported = False
        self.blocked_ips = set()
        self.allowed_ips = set()
        self.users = [
            {"name": "admin", "compromised": False},
            {"name": "dev", "compromised": False},
            {"name": "analyst", "compromised": False}
        ]
        self.open_ports = [22, 80, 443, 3306]
        self.counters = {
            "bruteforce": 0,
            "scan": 0,
            "exploit": 0,
            "phishing": 0,
            "malware": 0,
            "ddos": 0,
            "blocked": 0
        }

    def status(self):
        return "Firewall: ACTIVO" if self.firewall else "Firewall: INACTIVO"

    def add_log(self, message, severity="INFO", event_type="info", blocked=False):
        prefix = f"[{severity}] " if severity else ""
        entry = {
            "text": prefix + message,
            "severity": severity,
            "type": event_type,
            "ts": pygame.time.get_ticks()
        }
        self.logs.append(entry)
        if event_type in self.counters:
            self.counters[event_type] += 1
        if blocked:
            self.counters["blocked"] += 1
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]

    def apply_patch(self, now_ms, duration_ms=60000):
        self.patches_until_ms = max(self.patches_until_ms, now_ms + duration_ms)

    def risk_level(self, now_ms):
        score = len(self.open_ports)
        if not self.firewall:
            score += 1
        if now_ms >= self.patches_until_ms:
            score += 1
        if self.compromised or self.malware:
            score += 2
        if score <= 3:
            return "BAJO"
        if score <= 5:
            return "MEDIO"
        return "ALTO"

    def status_display(self, now_ms):
        patch_active = now_ms < self.patches_until_ms
        if patch_active:
            remaining = max(0, (self.patches_until_ms - now_ms) // 1000)
            patch_text = f"Parches: ACTIVOS ({remaining}s)"
        else:
            patch_text = "Parches: INACTIVOS"

        health_text = f"Salud servicio: {self.health}%"
        if self.ddos_active:
            health_text += " (DDoS)"

        if self.health >= 70:
            health_color = GREEN
        elif self.health >= 40:
            health_color = YELLOW
        else:
            health_color = RED

        return [
            (self.status(), GREEN if self.firewall else RED),
            (f"IDS: {'ACTIVO' if self.ids else 'INACTIVO'}", GREEN if self.ids else RED),
            (f"Rate-limit: {'ACTIVO' if self.rate_limit else 'INACTIVO'}", GREEN if self.rate_limit else RED),
            (patch_text, GREEN if patch_active else RED),
            (f"Aislamiento: {'ACTIVO' if self.isolated else 'INACTIVO'}", GREEN if self.isolated else RED),
            (f"Malware: {'SI' if self.malware else 'NO'}", RED if self.malware else GREEN),
            (f"Comprometido: {'SI' if self.compromised else 'NO'}", RED if self.compromised else GREEN),
            (health_text, health_color)
        ]

    def update(self, now_ms):
        if not self.ddos_active and self.health < 100 and now_ms >= self.next_recovery_ms:
            self.health = min(100, self.health + 1)
            self.next_recovery_ms = now_ms + 1000
            if self.health > 30:
                self.degraded_warned = False
            if self.health > 0:
                self.down_reported = False

# ---------------- ATTACKER ----------------
class Attacker:
    def __init__(self):
        self.next_check_ms = 0
        self.next_ddos_ms = 0

    def generate_event(self, server, now_ms):
        self._handle_ddos(server, now_ms)

        if now_ms < self.next_check_ms:
            return

        # Revisa una vez por segundo si ocurre un intento de ataque
        self.next_check_ms = now_ms + 1000
        if random.random() < 0.25:
            self.trigger_event(server, now_ms)

    def _handle_ddos(self, server, now_ms):
        if not server.ddos_active:
            return
        if now_ms < self.next_ddos_ms:
            return

        self.next_ddos_ms = now_ms + 1200
        server.add_log("Tráfico anómalo detectado (DDoS)", "ALTA", "ddos")

        impact = 0
        if not server.isolated:
            impact = 1 if server.rate_limit else 2

        if impact > 0:
            server.health = max(0, server.health - impact)

        if server.health <= 30 and not server.degraded_warned:
            server.add_log("⚠ Servicio degradado por DDoS", "ALTA", "ddos")
            server.degraded_warned = True

        if server.health <= 0 and not server.down_reported:
            server.add_log("⚠ Servicio fuera de linea", "ALTA", "ddos")
            server.down_reported = True

    def trigger_event(self, server, now_ms, forced_type=None):
        attack_types = ["bruteforce", "scan", "exploit", "phishing", "malware"]
        if forced_type in attack_types or forced_type == "ddos":
            attack_type = forced_type
        else:
            attack_type = random.choice(attack_types)

        label = ATTACK_LABELS.get(attack_type, attack_type)
        ip = random_ip()

        if server.allowed_ips and ip not in server.allowed_ips:
            server.add_log(f"Intento bloqueado por lista blanca: {ip}", "MEDIA", attack_type, blocked=True)
            return

        if ip in server.blocked_ips:
            server.add_log(f"IP bloqueada detectada: {ip}", "MEDIA", attack_type, blocked=True)
            return

        if attack_type == "ddos":
            if not server.ddos_active:
                server.ddos_active = True
                server.add_log("⚠ Ataque DDoS iniciado", "ALTA", "ddos")
            else:
                server.add_log("DDoS ya está activo", "MEDIA", "ddos")
            return

        if server.isolated:
            server.add_log("Aislamiento activo: intento bloqueado", "MEDIA", attack_type, blocked=True)
            return

        if attack_type in ["bruteforce", "scan", "exploit", "malware"] and server.firewall:
            server.add_log(f"Firewall bloqueó {label} desde {ip}", "MEDIA", attack_type, blocked=True)
            return

        if attack_type == "bruteforce":
            if server.rate_limit:
                server.add_log(f"Rate-limit bloqueó fuerza bruta desde {ip}", "MEDIA", "bruteforce", blocked=True)
                return

            if server.ids:
                server.add_log(f"IDS: patrón de fuerza bruta detectado ({ip})", "BAJA", "bruteforce")

            success_chance = 0.2 if not server.ids else 0.1
            if random.random() < success_chance:
                user = pick_user(server.users)
                user["compromised"] = True
                server.compromised = True
                server.add_log(f"⚠ Credenciales comprometidas ({user['name']}) desde {ip}", "ALTA", "bruteforce")
            else:
                server.add_log(f"Intento de fuerza bruta fallido desde {ip}", "MEDIA", "bruteforce")

        elif attack_type == "scan":
            if server.ids:
                server.add_log(f"IDS: escaneo detectado ({ip})", "MEDIA", "scan")

            ports = ", ".join(str(p) for p in server.open_ports)
            server.add_log(f"Escaneo de puertos desde {ip} (abiertos: {ports})", "BAJA", "scan")

        elif attack_type == "exploit":
            if now_ms < server.patches_until_ms:
                server.add_log(f"Exploit mitigado por parches desde {ip}", "MEDIA", "exploit", blocked=True)
                return

            if server.ids:
                server.add_log(f"IDS: intento de exploit detectado ({ip})", "MEDIA", "exploit")

            success_chance = 0.25 if not server.ids else 0.15
            if random.random() < success_chance:
                server.malware = True
                server.compromised = True
                server.add_log(f"⚠ Exploit exitoso: payload instalado desde {ip}", "ALTA", "exploit")
            else:
                server.add_log(f"Exploit fallido desde {ip}", "MEDIA", "exploit")

        elif attack_type == "phishing":
            if server.ids and random.random() < 0.6:
                server.add_log("Phishing detectado y bloqueado por IDS", "MEDIA", "phishing")
                return

            if random.random() < 0.25:
                user = pick_user(server.users)
                user["compromised"] = True
                server.compromised = True
                server.add_log(f"⚠ Usuario {user['name']} comprometido por phishing", "ALTA", "phishing")
            else:
                server.add_log("Campaña de phishing sin éxito", "BAJA", "phishing")

        elif attack_type == "malware":
            if now_ms < server.patches_until_ms:
                server.add_log(f"Malware bloqueado por parches desde {ip}", "MEDIA", "malware", blocked=True)
                return

            if random.random() < 0.3:
                server.malware = True
                server.add_log(f"⚠ Malware instalado desde {ip}", "ALTA", "malware")
            else:
                server.add_log(f"Intento de malware fallido desde {ip}", "MEDIA", "malware")

# ---------------- TERMINAL ----------------
class Terminal:
    def __init__(self, max_lines=200):
        self.max_lines = max_lines
        self.reset()
        self.input_text = ""

    def reset(self):
        self.lines = [
            "Bienvenido al Simulador de Ciberseguridad",
            "Escribe 'help' para ver los comandos"
        ]

    def add_line(self, text):
        self.lines.append(text)
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[-self.max_lines:]

    def execute(self, command, server, attacker, now_ms):
        cmd = command.strip()
        if not cmd:
            return

        lower = cmd.lower()
        parts = cmd.split()
        parts_lower = lower.split()

        if lower == "help":
            self.add_line("Comandos disponibles:")
            self.add_line("help | status | logs | clear")
            self.add_line("firewall on/off | ids on/off | rate-limit on/off | isolate on/off")
            self.add_line("patch | scan | netstat | users | threats | timeline")
            self.add_line("backup | restore | malware scan")
            self.add_line("block ip <x.x.x.x> | allow ip <x.x.x.x>")
            self.add_line("attack simulate [bruteforce|scan|exploit|phishing|ddos|malware]")
            self.add_line("ddos on | ddos off")

        elif lower == "status":
            for text, _ in server.status_display(now_ms):
                self.add_line(text)

        elif lower == "logs":
            if server.logs:
                for entry in server.logs[-5:]:
                    self.add_line(entry["text"])
            else:
                self.add_line("No hay eventos registrados")

        elif lower == "firewall on":
            server.firewall = True
            self.add_line("Firewall ACTIVADO")

        elif lower == "firewall off":
            server.firewall = False
            self.add_line("Firewall DESACTIVADO")

        elif lower == "ids on":
            server.ids = True
            self.add_line("IDS ACTIVADO")

        elif lower == "ids off":
            server.ids = False
            self.add_line("IDS DESACTIVADO")

        elif lower == "rate-limit on":
            server.rate_limit = True
            self.add_line("Rate-limit ACTIVADO")

        elif lower == "rate-limit off":
            server.rate_limit = False
            self.add_line("Rate-limit DESACTIVADO")

        elif lower == "isolate on":
            server.isolated = True
            self.add_line("Aislamiento ACTIVADO")
            server.add_log("Aislamiento de red activado", "MEDIA", "info")

        elif lower == "isolate off":
            server.isolated = False
            self.add_line("Aislamiento DESACTIVADO")
            server.add_log("Aislamiento de red desactivado", "MEDIA", "info")

        elif lower == "patch":
            server.apply_patch(now_ms)
            self.add_line("Parches aplicados (60s)")

        elif lower == "scan":
            ports = ", ".join(f"{p}/{PORT_NAMES.get(p, 'UNK')}" for p in server.open_ports)
            self.add_line("Escaneo local completado:")
            self.add_line(f"Puertos abiertos: {ports}")
            self.add_line(f"Riesgo estimado: {server.risk_level(now_ms)}")

        elif lower == "netstat":
            self.add_line("Conexiones activas:")
            for _ in range(3):
                ip = random_ip()
                port = random.choice([22, 80, 443, 3389, 3306])
                state = random.choice(["ESTABLISHED", "SYN_SENT", "TIME_WAIT"])
                self.add_line(f"{state} {ip}:{port}")

        elif lower == "users":
            for user in server.users:
                status = "COMPROMETIDO" if user["compromised"] else "OK"
                self.add_line(f"{user['name']}: {status}")

        elif lower == "threats":
            self.add_line("Resumen de amenazas:")
            self.add_line(f"fuerza bruta: {server.counters['bruteforce']}")
            self.add_line(f"escaneos: {server.counters['scan']}")
            self.add_line(f"exploits: {server.counters['exploit']}")
            self.add_line(f"phishing: {server.counters['phishing']}")
            self.add_line(f"malware: {server.counters['malware']}")
            self.add_line(f"ddos: {server.counters['ddos']}")
            self.add_line(f"bloqueados: {server.counters['blocked']}")

        elif lower == "timeline":
            critical = [log for log in server.logs if log["severity"] == "ALTA"]
            if critical:
                self.add_line("Eventos críticos recientes:")
                for entry in critical[-5:]:
                    self.add_line(entry["text"])
            else:
                self.add_line("No hay eventos críticos recientes")

        elif lower == "backup":
            server.last_backup_ms = now_ms
            self.add_line("Backup creado correctamente")

        elif lower == "restore":
            if server.last_backup_ms is None:
                self.add_line("No hay backup disponible")
            else:
                server.compromised = False
                server.malware = False
                server.health = 100
                for user in server.users:
                    user["compromised"] = False
                self.add_line("Sistema restaurado desde backup")
                server.add_log("Sistema restaurado desde backup", "MEDIA", "info")

        elif lower == "malware scan":
            if server.malware:
                server.malware = False
                self.add_line("Malware eliminado")
                server.add_log("Malware eliminado por escaneo", "MEDIA", "malware")
            else:
                self.add_line("No se detectó malware")

        elif parts_lower[:2] == ["block", "ip"]:
            if len(parts) >= 3 and is_valid_ip(parts[2]):
                ip = parts[2]
                server.blocked_ips.add(ip)
                server.allowed_ips.discard(ip)
                self.add_line(f"IP bloqueada: {ip}")
            else:
                self.add_line("Uso: block ip x.x.x.x")

        elif parts_lower[:2] == ["allow", "ip"]:
            if len(parts) >= 3 and is_valid_ip(parts[2]):
                ip = parts[2]
                server.allowed_ips.add(ip)
                server.blocked_ips.discard(ip)
                self.add_line(f"IP permitida: {ip}")
            else:
                self.add_line("Uso: allow ip x.x.x.x")

        elif parts_lower[:2] == ["attack", "simulate"]:
            attack_type = parts_lower[2] if len(parts_lower) >= 3 else None
            valid = ["bruteforce", "scan", "exploit", "phishing", "ddos", "malware"]
            if attack_type and attack_type not in valid:
                self.add_line("Tipo de ataque no válido")
            else:
                attacker.trigger_event(server, now_ms, attack_type)
                if attack_type:
                    self.add_line(f"Simulación de ataque: {attack_type}")
                else:
                    self.add_line("Simulación de ataque aleatoria")

        elif lower == "ddos on":
            if server.ddos_active:
                self.add_line("DDoS ya está activo")
            else:
                server.ddos_active = True
                server.add_log("⚠ Ataque DDoS iniciado (simulación)", "ALTA", "ddos")
                self.add_line("DDoS ACTIVADO")

        elif lower == "ddos off":
            if not server.ddos_active:
                self.add_line("DDoS ya estaba inactivo")
            else:
                server.ddos_active = False
                self.add_line("DDoS DESACTIVADO")
                server.add_log("Mitigación DDoS aplicada", "MEDIA", "ddos")

        elif lower == "clear":
            self.reset()

        else:
            self.add_line("Comando no reconocido")

# ---------------- GAME ----------------
server = Server()
attacker = Attacker()
terminal = Terminal()

running = True
while running:
    CLOCK.tick(60)
    screen.fill(BLACK)

    now_ms = pygame.time.get_ticks()
    server.update(now_ms)

    # ZONAS
    terminal_area = pygame.Rect(10, 10, 600, HEIGHT - 20)
    info_area = pygame.Rect(620, 10, WIDTH - 630, 200)
    attack_area = pygame.Rect(620, 220, WIDTH - 630, HEIGHT - 230)

    pygame.draw.rect(screen, GRAY, terminal_area, 2)
    pygame.draw.rect(screen, GRAY, info_area, 2)
    pygame.draw.rect(screen, GRAY, attack_area, 2)

    # EVENTOS
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            elif event.key == pygame.K_RETURN:
                terminal.add_line("> " + terminal.input_text)
                terminal.execute(terminal.input_text, server, attacker, now_ms)
                terminal.input_text = ""

            elif event.key == pygame.K_BACKSPACE:
                terminal.input_text = terminal.input_text[:-1]

            else:
                terminal.input_text += event.unicode

    # ATAQUES AUTOMÁTICOS
    attacker.generate_event(server, now_ms)

    # DIBUJAR TERMINAL
    y = terminal_area.y + 10
    for line in terminal.lines[-25:]:
        text = FONT.render(line, True, GREEN)
        screen.blit(text, (terminal_area.x + 10, y))
        y += 20

    input_render = FONT.render("> " + terminal.input_text, True, WHITE)
    screen.blit(input_render, (terminal_area.x + 10, terminal_area.bottom - 30))

    # INFO
    info_text = FONT.render("Estado del servidor", True, WHITE)
    screen.blit(info_text, (info_area.x + 10, info_area.y + 10))

    y = info_area.y + 40
    for text, color in server.status_display(now_ms):
        line = FONT.render(text, True, color)
        screen.blit(line, (info_area.x + 10, y))
        y += 20

    # ATAQUES
    attack_title = FONT.render("Actividad sospechosa", True, WHITE)
    screen.blit(attack_title, (attack_area.x + 10, attack_area.y + 10))

    y = attack_area.y + 40
    for log in server.logs[-5:]:
        if log["severity"] == "ALTA":
            color = RED
        elif log["severity"] == "MEDIA":
            color = YELLOW
        else:
            color = WHITE
        txt = FONT.render(log["text"], True, color)
        screen.blit(txt, (attack_area.x + 10, y))
        y += 20

    pygame.display.flip()

pygame.quit()
