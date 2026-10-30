# YouTube Studio Downloader

Aplicación de escritorio en Python para descargar videos, audios y listas de reproducción (playlists) de YouTube en múltiples formatos y resoluciones (hasta 4K), con una interfaz gráfica moderna basada en la paleta **Crimson Studio**.

---

## Características Principales

- **Vista previa del contenido:** Muestra miniatura en alta calidad, título, canal y duración antes de iniciar cualquier descarga.
- **Resoluciones reales dinámicas:** Analiza los streams disponibles del video y lista automáticamente las resoluciones soportadas (`2160p (4K)`, `1440p (2K)`, `1080p`, `720p`, `480p`, `360p`, etc.).
- **Múltiples formatos:**
  - **Video:** `MP4`, `MKV`, `WEBM`
  - **Solo Audio:** `MP3`, `M4A`, `WAV` con selección de bitrate (`320 kbps`, `192 kbps`, `128 kbps`).
- **Soporte de Playlists:** Permite analizar listas de reproducción completas y abrir un selector interactivo para elegir todos o únicamente los videos deseados.
- **Cola de descargas concurrente:** Descarga hasta 2 archivos en paralelo sin bloquear la interfaz gráfica, mostrando progreso en tiempo real (`%`), velocidad (`MB/s` o `KB/s`), tiempo estimado (`ETA`), botón para cancelar y acceso directo a la carpeta de destino al finalizar.
- **FFmpeg integrado automáticamente:** Detecta `ffmpeg` en el sistema o utiliza el binario integrado de `imageio-ffmpeg` automáticamente para unir pistas de video en alta definición (1080p/4K DASH) con el audio y convertir formatos sin configuraciones manuales.

---

## Especificaciones Técnicas

| Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Lenguaje** | Python 3.10+ | Tipado moderno y concurrencia con `ThreadPoolExecutor` |
| **Interfaz Gráfica (GUI)** | `CustomTkinter` + `Pillow` | Interfaz oscura moderna, componentes personalizados y renderizado de miniaturas |
| **Motor de Extracción** | `yt-dlp` | Análisis de metadatos, formatos, playlists y descarga de streams |
| **Procesamiento Multimedia** | `imageio-ffmpeg` / `FFmpeg` | Multiplexado de video+audio (1080p/4K) y conversión de audio (`MP3`/`M4A`/`WAV`) |
| **Red** | `requests` | Descarga asíncrona de miniaturas para la vista previa |

---

## Paleta de Diseño (Crimson Studio)

| Elemento | Color Hex | Uso |
| :--- | :--- | :--- |
| **Fondo Principal** | `#0F0F0F` | Ventana base estilo estudio oscuro |
| **Superficie / Tarjetas** | `#1E1E1E` | Paneles de entrada, vista previa y cola de descargas |
| **Campos / Inputs** | `#141414` | Cajas de texto, selectores y tarjetas individuales |
| **Bordes** | `#2D2D2D` | Delimitación sutil de contenedores |
| **Acento Primario** | `#E11D48` | Botones principales, selectores activos y barra de progreso (`#BE123C` en hover) |
| **Estado Éxito** | `#10B981` | Indicador de FFmpeg activo y descargas completadas |
| **Estado Peligro / Error** | `#EF4444` | Errores de análisis y cancelación de descargas |
| **Texto Primario / Secundario** | `#F8FAFC` / `#94A3B8` | Jerarquía tipográfica de alta legibilidad |

---

## Estructura del Proyecto

```text
youtube-downloader/
├── main.py                  # Punto de entrada de la aplicación
├── requirements.txt         # Dependencias del proyecto
├── src/
│   ├── config.py            # Paleta de colores, formatos y detección automática de FFmpeg
│   ├── core/
│   │   ├── analyzer.py      # Extracción de metadatos, resoluciones y playlists con yt-dlp
│   │   └── downloader.py    # Gestor de cola concurrente, hooks de progreso y cancelación
│   └── ui/
│       ├── app.py           # Ventana principal y coordinación de eventos asíncronos
│       ├── preview_panel.py # Panel de vista previa, selectores de formato y modal de playlists
│       └── queue_panel.py   # Panel de cola de descargas y tarjetas de progreso en vivo
└── tests/
    └── test_core.py         # Pruebas unitarias de análisis, formatos y configuración de yt-dlp
```

---

## Instalación y Uso

### 1. Clonar el repositorio
```bash
git clone https://github.com/whoislaura/youtube-downloader.git
cd youtube-downloader
```

### 2. Instalar dependencias
```bash
python -m pip install -r requirements.txt
```

### 3. Ejecutar la aplicación
```bash
python main.py
```

### 4. Ejecutar pruebas unitarias
```bash
python -m unittest discover -s tests -v
```
