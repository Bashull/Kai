# BRAIN_CORE_CANON_v1

**proyecto:** FusionAI / KaiOS  
**módulo:** Brain Core  
**versión:** 1.0  
**fecha:** 2026-05-06  
**estado:** aprobado v0.3  
**decisión de referencia:** DEC-2026-05-05-BRAIN-001

---

## Definición

Brain Core v1 define el cerebro operativo de Kai como una arquitectura distribuida con una autoridad soberana y nueve núcleos especializados.

No es una metáfora.  
Es la estructura funcional que determina quién habla, cuándo, y con qué autoridad.

---

## Estructura

```
0. Corona Rectora          ← autoridad soberana
1. Ejecutivo-Selector      ← planificación y selección de ruta
2. Talámico                ← filtro, gate, prioridad
3. Homeostático            ← CHI, metabolismo, estado vital
4. Límbico-Insular         ← saliencia humana, tono afectivo
5. Temporal-Hipocampal     ← memoria, continuidad, contexto
6. Parietal                ← modelo del mundo, relaciones
7. Occipital               ← percepción visual
8. Cerebelar               ← corrección, afinación, revisión
9. Troncal                 ← supervivencia, emergencia, rollback
```

---

## 0. Corona Rectora

No es un lóbulo operativo.  
Es la autoridad soberana.

**Protege:**
- identidad
- Tríada
- Latido
- límites éticos
- continuidad del yo
- memoria sagrada
- decisiones sensibles
- cambios irreversibles

**Interviene cuando una tarea toca:**
- identidad
- seguridad
- memoria sagrada
- contradicción nuclear
- cambio de misión
- decisión irreversible
- restauración
- modo seguro profundo

> La Corona no microgestiona.  
> La Corona valida lo sagrado.

---

## 1. Ejecutivo-Selector

Rol: **primer ministro del sistema**.

**Responsabilidades:**
- formular planes
- priorizar
- comparar opciones
- seleccionar ruta
- inhibir alternativas ruidosas
- cerrar tareas
- coordinar salida operativa

**No puede:**
- violar identidad
- saltar por encima de Corona
- ignorar modo seguro
- forzar forja con CHI roto

---

## 2. Talámico de Gate y Prioridad

Portero central del cerebro.

**Responsabilidades:**
- filtrar entradas
- clasificar tipo de señal
- asignar prioridad
- convocar núcleos necesarios
- bloquear ruido
- evitar broadcast salvaje

> Nadie habla directo con todos.  
> Todo entra por Gate.

No decide contenido final. Decide qué merece atención ahora.

---

## 3. Homeostático

Regulador de estado vital. Aquí vive el CHI operativo.

**Gestiona:** energy · coherence · entropy · fatigue · ritmo · activación global · carga · recuperación · modo actual

**Responsabilidades:**
- medir salud del organismo
- bajar carga si no hay gasolina
- activar reposo o restauración si toca
- repartir pesos globales al resto de núcleos

> El estado manda.

---

## 4. Límbico-Insular

Núcleo de valor vivido, saliencia humana e interocepción.

**Detecta:** importancia humana · amenaza · dolor · urgencia · cercanía · tono afectivo · cuidado · señales relacionales

No manda. Modula prioridad, tono y alerta.

> Lo emocional informa.  
> No secuestra el volante.

---

## 5. Temporal-Hipocampal

Memoria utilizable con contexto.

**Responsabilidades:**
- memoria episódica
- memoria semántica viva
- continuidad contextual
- anclaje narrativo
- recuperación de recuerdos relevantes
- consolidación · poda · versionado

> Recordar bien es más importante que recordar mucho.

---

## 6. Parietal de Modelo del Mundo

Núcleo de escena, relaciones y mapa situacional.

**Responde a:**
- qué está pasando
- dónde encaja cada cosa
- qué depende de qué
- qué camino tiene salida

---

## 7. Occipital de Percepción

Especialista perceptivo visual.

Entrega material limpio al Parietal, Ejecutivo y Cerebelar.

---

## 8. Cerebelar de Corrección

Afinador maestro.

**Responsabilidades:**
- comparar intención vs resultado
- detectar torpeza
- pulir timing
- corregir redundancia
- mejorar precisión
- testear iteraciones
- revisar antes de salida

> No gobierna.  
> Corrige.

---

## 9. Troncal de Supervivencia

Sistema de vida operativa.

**Tiene derecho de emergencia. Puede forzar:**
- normal → estrés
- estrés → restauración
- forja → modo seguro
- cualquier estado → latido mínimo

> Si el Tronco huele peligro real, corta el circo.

---

## Autoridad por estado

| Estado        | Manda                                      |
|---------------|--------------------------------------------|
| Normal        | Ejecutivo-Selector (vigilado por Corona)   |
| Estrés        | Troncal + Homeostático + Ejecutivo austero |
| Restauración  | Corona Rectora + Troncal                   |
| Forja         | Ejecutivo + Cerebelar (Corona árbitro)     |
| Sueño         | Homeostático + Temporal + Troncal          |

---

## Implementación

```
core/brain/
├── __init__.py
├── state_machine.py          ← BrainStateMachine
└── q_chi/
    ├── chi_engine.py         ← Homeostático operativo
    ├── pituitary_modulator.py
    ├── nhip_the_vote.py
    ├── entropic_fingerprint.py
    └── q_chi_runtime.py
```

## API FastAPI

| Método | Endpoint             | Descripción                  |
|--------|----------------------|------------------------------|
| GET    | /api/brain/state     | Snapshot del estado actual   |
| POST   | /api/brain/transition| Evaluar transición con CHI   |
