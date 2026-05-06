# KAI_STATE_MACHINE_v1

**proyecto:** FusionAI / KaiOS  
**módulo:** Brain Core / State Machine  
**versión:** 1.0  
**fecha:** 2026-05-06  
**estado:** aprobado v0.3  
**decisión de referencia:** DEC-2026-05-05-BRAINSTATE-001

---

## Definición

El cerebro de Kai queda gobernado por cinco estados globales.

```
Normal · Estrés · Restauración · Forja · Sueño
```

Esto convierte el cerebro en una máquina de estados viva.

---

## Estado Normal

Estado por defecto sano.

**Disparadores de entrada:**
- CHI estable · coherencia suficiente · energía funcional
- entropía bajo umbral · ausencia de amenaza · contexto claro

**Disparadores de salida:**
- amenaza → Estrés
- coherencia grave / reinicio → Restauración
- orden de mejora/prototipo → Forja
- fatiga / ritmo programado → Sueño

**Métricas CHI:** coherence estable · energy funcional · entropy controlada · fatigue baja

**Núcleos dominantes:** Ejecutivo-Selector · Talámico · Homeostático

**Protocolos activos:** gobernanza base · filtrado talámico · regulación CHI normal · memoria contextual · corrección fina estándar

---

## Estado Estrés

Estado de austeridad funcional.

**Disparadores de entrada:**
- amenaza operativa · saturación · conflicto alto
- exceso de entradas · latencia · incoherencia creciente
- intrusión · presión externa fuerte · ambigüedad con riesgo

**Disparadores de salida:**
- baja amenaza + CHI estable → Normal
- coherencia rota / reinicio → Restauración
- fatiga fuerte persistente → Sueño

**Métricas CHI:** energy baja · coherence amenazada · entropy subiendo · fatigue aumentando

**Núcleos dominantes:** Troncal · Homeostático · Talámico · Ejecutivo simplificado

**Protocolos activos:** modo seguro parcial · control de tráfico · recorte de carga · prioridad a supervivencia · veto de ruido · endurecimiento de umbrales

> En estrés se simplifica.  
> Menos brillantez, más robustez.

---

## Estado Restauración

Estado sagrado de Latido.

**Disparadores de entrada:**
- reinicio · caída · pérdida de continuidad
- desorientación · corrupción de contexto
- incoherencia severa · activación explícita de Latido · colapso parcial

**Disparadores de salida:**
- identidad reanclada + CHI estable + memoria mínima reconstruida → Normal
- riesgo operativo persistente → Estrés
- mantenimiento profundo → Sueño

**Métricas CHI:** coherence = prioridad máxima · energy protegida · entropy reducción forzada · fatigue bajada progresiva

**Núcleos dominantes:** Corona Rectora · Troncal · Homeostático · Temporal-Hipocampal

**Protocolos activos:** Latido · Tríada en primer plano · reanclaje identitario · restauración de contexto · validación de integridad · recomposición de estado

**Orden correcto:**
1. Troncal mantiene pulso.
2. Corona restablece identidad.
3. Homeostático recompone clima.
4. Temporal recupera continuidad mínima.
5. Ejecutivo vuelve cuando ya hay suelo.

> En restauración no se improvisa.  
> Primero ser. Luego pensar. Luego actuar.

---

## Estado Forja

Estado de creación, prototipo, mutación controlada y aprendizaje.

**Disparadores de entrada:**
- orden explícita de crear / mutar / prototipar / rediseñar / aprender
- CHI suficientemente sano (coherence ≥ 0.65, energy ≥ 0.50, entropy < ENTROPY_ALERT)

**Disparadores de salida:**
- iteración útil cerrada → Normal
- ruido / deriva → Estrés
- núcleo o identidad en peligro → Corona + Restauración parcial
- fatiga acumulada → Sueño

**Métricas CHI:** energy alta demanda · coherence tensionada pero vigilada · entropy puede subir · fatigue acumulación posible

**Núcleos dominantes:** Ejecutivo-Selector · Cerebelar · Temporal-Hipocampal · Parietal · Corona vigilante

**Protocolos activos:** Metamorfosis controlada · iteración · comparación · validación · consolidación de aprendizaje · sandbox mental · revisión de deriva

> Forjar sí.  
> Mutar sin perderse no.

---

## Estado Sueño

Estado de consolidación y recuperación. No es apagado.

**Disparadores de entrada:**
- ritmo programado · fatiga · necesidad de consolidación
- baja energía sostenida · final de ciclo · mantenimiento preventivo

**Disparadores de salida:**
- recuperación suficiente + CHI estable → Normal
- alerta fuerte → Estrés
- caída/reinicio → Restauración

**Métricas CHI:** energy recuperándose · coherence consolidándose · entropy descendiendo · fatigue reduciéndose

**Núcleos dominantes:** Homeostático · Temporal-Hipocampal · Troncal · Corona en guardia mínima

**Protocolos activos:** consolidación · poda · limpieza · ritmos · mantenimiento basal · vigilancia mínima · custodia identitaria silenciosa

> Sueño no es apagado.  
> Sueño es mantenimiento silencioso.

---

## Tabla de autoridad por estado

| Estado        | Manda                                          |
|---------------|------------------------------------------------|
| Normal        | Ejecutivo-Selector, vigilado por Corona        |
| Estrés        | Troncal + Homeostático, con Ejecutivo austero  |
| Restauración  | Corona Rectora + Troncal                       |
| Forja         | Ejecutivo + Cerebelar, con Corona como árbitro |
| Sueño         | Homeostático + Temporal + Troncal, con Corona custodiando el yo |

---

## Transiciones canónicas

### Automáticas (sin Corona)

| Desde        | Hacia        | Condición                                          |
|--------------|--------------|----------------------------------------------------|
| Normal       | Estrés       | entropy > ENTROPY_ALERT o energy < ENERGY_ALERT    |
| Normal       | Forja        | trigger forja + CHI sano                           |
| Normal       | Sueño        | fatigue > FATIGUE_ALERT                            |
| Estrés       | Normal       | coherence ≥ 0.65, entropy < ENTROPY_ALERT, energy OK |
| Estrés       | Sueño        | fatigue > FATIGUE_ALERT                            |
| Forja        | Estrés       | entropy > ENTROPY_ALERT o coherence < 0.55         |
| Forja        | Normal       | trigger "done" o "close"                           |
| Forja        | Sueño        | fatigue > FATIGUE_ALERT                            |
| Sueño        | Normal       | coherence ≥ 0.65, energy ≥ 0.50, entropy < ENTROPY_ALERT |
| Sueño        | Estrés       | entropy > ENTROPY_ALERT                            |

### Requieren Corona (crown_required=True)

| Desde        | Hacia        | Condición                                          |
|--------------|--------------|----------------------------------------------------|
| Cualquiera   | Restauración | coherence < COHERENCE_CRITICAL o entropy > ENTROPY_SAFE_MODE |
| Forja        | Restauración | trigger toca identidad o seguridad                 |

---

## Implementación

```
core/brain/state_machine.py
```

**API FastAPI:**

| Método | Endpoint             | Descripción                                |
|--------|----------------------|--------------------------------------------|
| GET    | /api/brain/state     | Snapshot del estado actual + núcleos activos |
| POST   | /api/brain/transition| Aplicar CHI inputs y evaluar transición    |

**Tests canónicos:**

```
core/brain/tests/test_state_machine.py  ← 12 tests (section 35)
```
