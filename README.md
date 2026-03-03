# 🧠 SimulaFIEE Platform — Simulador de Ingenierías de la Facultad de Ingeniería Eléctrica y Electrónica

---

## ⚙️ Descripción

*SimulaFIEE Platform* es una plataforma interactiva de simulación diseñada para apoyar el aprendizaje práctico en la Facultad de Ingeniería Eléctrica y Electrónica.

El sistema permite visualizar y experimentar de forma dinámica con conceptos fundamentales de:

* ⚡ Ingeniería Eléctrica
* 🔌 Ingeniería Electrónica
* 📡 Ingeniería de Telecomunicaciones
* 🛡️ Ciberseguridad

Su objetivo es reducir la brecha entre la teoría académica y la aplicación real mediante simulaciones visuales e interactivas.

---

## ✨ Características Principales

⚡ *Simulación Interactiva*
Representación visual de sistemas y procesos de ingeniería.

🔌 *Multidisciplinario*
Integra cuatro especialidades de la FIEE en una sola plataforma.

📊 *Aprendizaje Visual*
Comprensión intuitiva mediante simulaciones dinámicas.

🧪 *Modo Experimental*
Permite modificar parámetros y observar resultados en tiempo real.

🏫 *Enfoque Académico*
Diseñado específicamente para estudiantes universitarios.

🚀 *Escalable*
Arquitectura preparada para añadir nuevos módulos de simulación.

---

# 🛠️ Tecnologías Utilizadas

### 🐍 Lenguaje

* Python 3.12+

### 🎮 Motor Gráfico

* Pygame

  * Renderizado 2D
  * Gestión de eventos (teclado y mouse)
  * Loop principal de simulación

### 📦 Librerías estándar

* sys
* subprocess
* pathlib
* math
* random
* os
* collections.deque

### 🖼️ Recursos Multimedia

* Imágenes .png y .jpg
* Fondos y componentes gráficos
* Carpeta componentes/

---

# ⚙️ Instalación y Configuración

## 📌 Pre-requisitos

* Python 3.12+
* pip actualizado
* Sistema con entorno gráfico (necesario para ejecutar ventanas Pygame)

---

## 💻 Configuración Local

### 1️⃣ Clonar o descargar el proyecto

Ubicarse en la carpeta raíz del proyecto.

### 2️⃣ Crear entorno virtual

bash
```python -m venv .venv```


### 3️⃣ Activar entorno virtual

Windows (PowerShell):

```bash
.\.venv\Scripts\Activate.ps1
```


### 4️⃣ Instalar dependencia principal

```bash
pip install pygame
```


### 5️⃣ Ejecutar el menú principal

```bash
python main.py
```


---

# 🎛️ Uso de los Simuladores

## 🔄 Flujo Principal

main.py funciona como:

* Orquestador de navegación
* Gestor de estados de pantalla
* Lanzador de talleres mediante subprocess

Cada simulador corre en un proceso independiente.

---

# ⚡ Taller de Eléctrica

* electrica.py → Tablero eléctrico 2D
* maquina electrica.py → Motor trifásico estrella/triángulo
* control_industrial.py → Instrumentación + VFD
* energia_solar.py → Sistema fotovoltaico off-grid
* circuito electrico.py → Circuito DC básico

---

# 🔌 Taller de Electrónica

* mainAdvComp.py
  Juego interactivo “Adivina el componente” usando imágenes de componentes/.

---

# 📡 Taller de Telecomunicaciones

* teleco.py
  Simulación de red móvil:

  * 2G
  * 3G
  * 4G
  * 5G

Incluye comportamiento dinámico y visualización del sistema.

---

# 🛡️ Taller de Ciberseguridad

* ciber.py
  Terminal interactiva con:

  * Comandos simulados
  * Escenarios de defensa
  * Simulación de ataques controlados

---

# 🎮 Controles Generales

| Tecla / Acción  | Función                          |
| --------------- | -------------------------------- |
| ESC             | Salir del simulador actual       |
| R               | Cambiar modo de trazado de cable |
| C               | Limpiar cables                   |
| Backspace       | Deshacer último punto            |
| Click izquierdo | Conectar / Interactuar           |
| Click derecho   | Cancelar trazado / Borrar cable  |

---

# 🏗️ Arquitectura del Proyecto

* Arquitectura modular por scripts independientes
* main.py como controlador central
* Cada simulador posee:

  * Su propio loop de Pygame
  * Lógica de dominio independiente
* Lanzamiento desacoplado mediante subprocess
* Recursos gráficos compartidos en raíz y componentes/
* Diagramas incluidos:

  * classes_Proyecto.png
  * packages_Proyecto.png

---

# 🗺️ Roadmap

* Completar sección Opciones del menú principal
* Expandir taller de Electrónica
* Añadir más escenarios en Ciberseguridad (niveles progresivos)
* Incorporar más métricas pedagógicas en Telecom
* Unificar codificación de texto y limpieza de acentos en UI
* Agregar requirements.txt y guía de despliegue
* Incluir pruebas básicas de ejecución y validación de módulos

---

# 🚀 SimulaFIEE Platform — Transformando la educación en ingeniería mediante simulación interactiva ⚡🧠💻

---

# 📬 Contacto

*Universidad:* Universidad Nacional de Ingeniería

### 👨‍💻 Desarrolladores

* JIMÉNEZ OSTOS, GIACOMO RENATO
* BROCOS BARBARON, YERSI ALDAIR
* ACOSTA APARICIO, DAVID BRANDO
* TINCO SÁNCHEZ OTONIEL FERNANDO

### 📧 Email

* [giacomo.jimenez.o@uni.pe](mailto:giacomo.jimenez.o@uni.pe)
* [yersi.brocos.b@uni.pe](mailto:yersi.brocos.b@uni.pe)
* [david.acosta.a@uni.pe](mailto:david.acosta.a@uni.pe)
* [otoniel.tinco.s@uni.pe](mailto:otoniel.tinco.s@uni.pe)
