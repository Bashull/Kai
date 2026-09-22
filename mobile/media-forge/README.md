# Media Forge Omega en Termux

Estado: módulo de montaje local; no instala ni llama a modelos generativos.
Propósito: usar el Animatic Kernel existente desde Android para convertir referencias y clips aprobados en una secuencia reproducible.
Trigger: preparar un animatic, revisar continuidad, montar clips descargados de un generador o exportar una prueba con música.

## Uso

Requiere Termux, Node con soporte nativo de TypeScript (probado en Node 26.4), FFmpeg con libx264 y ffprobe.
Se ejecuta en almacenamiento privado de Termux. Las imágenes, clips, música y exportaciones pueden estar en almacenamiento compartido con permiso.

Desde la raíz de este checkout:

    node mobile/media-forge/install-termux.mjs

    node mobile/media-forge/kai-media.mjs doctor
    node mobile/media-forge/kai-media.mjs doctor --benchmark
    node --test mobile/media-forge/kai-media.test.mjs
    node mobile/media-forge/kai-media.mjs validate /ruta/plan.json
    node mobile/media-forge/kai-media.mjs render /ruta/plan.json /ruta/salida.mp4

La instalación de usuario añade un lanzador en $PREFIX/bin/kai-media. No requiere root ni cambios del sistema Android.

Plan mínimo:

    {
      "schemaVersion": 1,
      "profile": "preview",
      "shots": [
        {
          "id": "plano_01",
          "kind": "still",
          "source": "/ruta/imagen.jpg",
          "durationSeconds": 4,
          "motion": "push",
          "crop": null
        }
      ],
      "audio": {
        "source": "/ruta/cancion.mp3",
        "startSeconds": 0
      }
    }

Para incorporar un clip aprobado, usar kind="video", motion="hold" y startSeconds.
La música es opcional. La fuente debe cubrir toda la duración solicitada.
El recorte es opcional y normalizado: x,y,w,h en 0..1, totalmente contenido en la imagen.
No admite URLs en el plan. Primero se descarga el archivo mediante el proveedor autorizado.

## Perfiles y funcionamiento

small = 640×360, preview = 1280×720, master = 1920×1080. Todos a 24 fps y dos hilos de codificación.
Planos de 0,25 a 30 segundos; hasta 500 planos. Se procesan secuencialmente.
hold mantiene la composición; push añade un acercamiento digital discreto. No anima el cuerpo ni inventa partes de la referencia.
El render usa libx264. El benchmark de MediaCodec es diagnóstico; que pase una muestra corta no convierte todos los dispositivos y formatos en compatibles.
No hace falta instalar un modelo de IA para este montaje.

La interfaz reutiliza buildAnimaticSegmentArgs y buildAnimaticConcatArgs de src/media/animaticKernel.ts.
Añade validación, control de hilos, límite de tiempo con terminación del proceso, comprobación de formato/duración/decodificación y recibos SHA-256.
Los originales no se modifican; no se sustituye un archivo de salida existente que no coincida con su recibo.
Las rutas pasan como argumentos de procesos, sin shell. La lista concat usa nombres internos y modo seguro.
No accede a claves, cuentas de Google, cookies, puertos públicos ni APIs de pago.

## Reanudación y rutas

Estado: ~/.local/share/kai/media-forge, o KAI_MEDIA_STATE_DIR si se configura una ruta concreta.
Jobs: jobs/<hash>/ con segmentos, configuración implícita en hash y recibos.
El hash incluye plan, bytes de todas las fuentes, código del módulo, kernel y versión de FFmpeg.
Una ejecución repetida reutiliza segmentos cuyo hash coincide. Una salida completa con recibo válido se devuelve sin renderizar.
El archivo final lleva un recibo .mp4.kai.json. Conservar ambos para trazabilidad.
Los perfiles generan tamaños finales constantes y píxeles cuadrados; el audio se ajusta al montaje.

## Fallos y recuperación

- SOURCE_MUST_BE_LOCAL_FILE / permiso: comprobar ruta y permiso de archivos de Termux. No cambiar a otra referencia silenciosamente.
- INVALID_*: corregir el plan. No ajustar un recorte fuera de rango de forma oculta.
- AUDIO_TOO_SHORT / VIDEO_TOO_SHORT: reducir la duración o usar el tramo correcto. No alargar con silencio/congelados sin decisión creativa.
- OUTPUT_EXISTS_PRESERVED: elegir otro nombre o revisar el resultado existente. No se sobrescribe automáticamente.
- JOB_LOCKED: otro render o una interrupción dejó render.lock. Leer pid y started, comprobar si ese proceso sigue siendo el render y no eliminar el bloqueo mientras esté activo. Después de una interrupción confirmada, archivar ese bloqueo y repetir el comando; los segmentos verificados se reutilizan.
- ETIMEDOUT: el proceso de esa operación recibe SIGKILL; conservar recibos anteriores. Probar perfil small o un plano más corto.
- Android mata procesos o suspende la sesión: abrir Termux, revisar estado y repetir. No instalar vigilantes permanentes ni modificar políticas de batería sin necesidad.
- termux-battery-status no responde: registrar telemetría desconocida. Este módulo no depende de Termux:API.
- Archivo final sin recibo tras interrupción de copia: preservarlo como incompleto y usar otra salida. El job permite reutilizar los segmentos.

Rollback: retirar únicamente el lanzador $PREFIX/bin/kai-media si apunta a este módulo. Checkout, fuentes y exportaciones permanecen. No se instalaron paquetes del sistema ni se editaron archivos de inicio.

## Genealogía y fuentes

Autoridad de producto: KAI MEDIA FORGE OMEGA. No es un nuevo producto paralelo.
Antecesor directo: Animatic Kernel, commit local 21c2436; copia remota sync/animatic-kernel-20260828, b1b781ab29643ee0b15b717f5b31637968a7fabc.
Base local auditada: b0648564c2d15580db3ea4bf6389518a9a57f5c2. El kernel local y remoto se compararon iguales.
La publicación añade solo este adaptador, sus pruebas y su runbook a la rama remota del kernel; no mezcla otros cambios locales.
Transferencia directa: reutilizar render y concat. Transversal: hashes, recuperación y protección de fuentes. Emergente: un montaje puede empezar con ilustraciones y sustituir planos por clips sin cambiar de herramienta.

Referencias oficiales consultadas el 22/09/2026:
- https://github.com/termux/termux-packages/wiki/Termux-file-system-layout
- https://github.com/termux/termux-packages/blob/master/packages/ffmpeg/build.sh
- https://ffmpeg.org/ffmpeg-filters.html
- https://github.com/leejet/stable-diffusion.cpp

stable-diffusion.cpp documenta Android/Termux y motores Vulkan, además de modelos de vídeo. No demuestra que un modelo concreto quepa o sea práctico en este móvil. La inferencia generativa local queda EXPERIMENTAL/NOT_TESTED; no se descargaron pesos.
Para producción: preparar referencias aquí, generar movimiento con una cuota disponible del proveedor y montar el material aprobado en Termux.

## Evidencia de la puesta en marcha · 2026-09-22

Android ARM64, Node 26.4.0 y FFmpeg 8.1.2. Cuatro pruebas de contrato PASS. Muestra sintética codificada y decodificada tanto con libx264 como con h264_mediacodec. Prueba de dos planos con música: 8 s, 1280×720, 24 fps; proceso de render medido 5,457 s. Repetición completa idempotente, recuperación de ambos segmentos, importación/recorte de vídeo y preservación de una salida previa: PASS. Este alcance valida montaje local; no valida inferencia generativa ni el perfil master a 1080p.
