# 📜 Análisis de Compatibilidad de Licencias - Proyecto Kai

Este documento analiza la compatibilidad de licencias de todas las dependencias integradas en Kai.

## Resumen Ejecutivo

✅ **Todas las dependencias principales son compatibles con uso comercial y código abierto.**

La mayoría de dependencias usan licencias permisivas (MIT, Apache 2.0) que permiten:
- Uso comercial
- Modificación del código
- Distribución
- Uso privado

---

## Dependencias Principales

### 1. LangChain

**Licencia**: MIT  
**Repositorio**: https://github.com/langchain-ai/langchain  
**Versión evaluada**: 0.1.x

#### Términos Clave
- ✅ Uso comercial permitido
- ✅ Modificación permitida
- ✅ Distribución permitida
- ✅ Uso privado permitido
- ⚠️ Sin garantías

#### Compatibilidad
Compatible con cualquier uso. Requiere mantener aviso de copyright y licencia en distribuciones.

#### Recomendación
**APROBADA** ✅ - Totalmente compatible con Kai.

---

### 2. Coqui TTS

**Licencia**: Mozilla Public License 2.0 (MPL 2.0)  
**Repositorio**: https://github.com/coqui-ai/TTS  
**Versión evaluada**: 0.20.x

#### Términos Clave
- ✅ Uso comercial permitido
- ✅ Modificación permitida
- ✅ Distribución permitida
- ⚠️ Copyleft débil (solo para archivos modificados)
- ✅ Compatibilidad con código propietario

#### Compatibilidad
MPL 2.0 es una licencia copyleft "débil":
- Modificaciones a archivos de Coqui TTS deben compartirse bajo MPL 2.0
- Código nuevo que usa Coqui TTS puede tener cualquier licencia
- Puede combinarse con código propietario

#### Recomendación
**APROBADA** ✅ - Compatible siempre que:
1. No modifiquemos el código fuente de Coqui TTS directamente
2. Usemos Coqui TTS como biblioteca/dependencia (nuestro caso)
3. Incluyamos aviso de licencia MPL 2.0 para Coqui TTS

---

### 3. OpenAI Whisper

**Licencia**: MIT  
**Repositorio**: https://github.com/openai/whisper  
**Versión evaluada**: 20231117

#### Términos Clave
- ✅ Uso comercial permitido
- ✅ Modificación permitida
- ✅ Distribución permitida
- ✅ Uso privado permitido

#### Compatibilidad
Totalmente permisiva. Solo requiere mantener aviso de copyright.

#### Recomendación
**APROBADA** ✅ - Totalmente compatible con Kai.

---

### 4. Autotrain Advanced (Hugging Face)

**Licencia**: Apache License 2.0  
**Repositorio**: https://github.com/huggingface/autotrain-advanced  
**Versión evaluada**: 0.6.x

#### Términos Clave
- ✅ Uso comercial permitido
- ✅ Modificación permitida
- ✅ Distribución permitida
- ✅ Uso de patentes otorgadas
- ⚠️ Debe incluir NOTICE si existe

#### Compatibilidad
Apache 2.0 es muy permisiva y compatible con código propietario.
Incluye cláusula de patentes que protege a usuarios.

#### Recomendación
**APROBADA** ✅ - Totalmente compatible con Kai.

---

### 5. FAISS (Facebook Research)

**Licencia**: MIT  
**Repositorio**: https://github.com/facebookresearch/faiss  
**Versión evaluada**: 1.7.x

#### Términos Clave
- ✅ Uso comercial permitido
- ✅ Modificación permitida
- ✅ Distribución permitida
- ✅ Uso privado permitido

#### Compatibilidad
MIT es la licencia más permisiva. Sin restricciones significativas.

#### Recomendación
**APROBADA** ✅ - Totalmente compatible con Kai.

---

### 6. Terraform Google Modules

**Licencia**: Apache License 2.0  
**Repositorio**: https://github.com/terraform-google-modules  
**Versión evaluada**: v18.0.0, v13.1.0, v26.2.1

#### Términos Clave
- ✅ Uso comercial permitido
- ✅ Modificación permitida
- ✅ Distribución permitida
- ✅ Uso de patentes otorgadas

#### Compatibilidad
Apache 2.0 compatible con cualquier uso.

#### Recomendación
**APROBADA** ✅ - Totalmente compatible con Kai.

---

### 7. Google Cloud Terraform Modules

**Licencia**: Apache License 2.0  
**Repositorio**: https://github.com/GoogleCloudPlatform/terraform-google-*  
**Versión evaluada**: v0.9.0, v0.21.2

#### Términos Clave
- ✅ Uso comercial permitido
- ✅ Modificación permitida
- ✅ Distribución permitida

#### Compatibilidad
Apache 2.0 compatible con cualquier uso.

#### Recomendación
**APROBADA** ✅ - Totalmente compatible con Kai.

---

## Dependencias Opcionales Evaluadas

### 8. ChromaDB

**Licencia**: Apache License 2.0  
**Repositorio**: https://github.com/chroma-core/chroma  
**Estado**: Recomendada para implementación futura

#### Recomendación
**APROBADA** ✅ - Totalmente compatible con Kai.

---

### 9. Rasa

**Licencia**: Apache License 2.0  
**Repositorio**: https://github.com/RasaHQ/rasa  
**Estado**: En evaluación

#### Recomendación
**APROBADA** ✅ - Totalmente compatible con Kai.

---

### 10. Microsoft Semantic Kernel

**Licencia**: MIT  
**Repositorio**: https://github.com/microsoft/semantic-kernel  
**Estado**: En evaluación

#### Recomendación
**APROBADA** ✅ - Totalmente compatible con Kai.

---

### 11. pgvector

**Licencia**: PostgreSQL License  
**Repositorio**: https://github.com/pgvector/pgvector  
**Estado**: Alta prioridad

#### Términos Clave
- ✅ Permisiva similar a MIT/BSD
- ✅ Uso comercial permitido
- ✅ Modificación permitida

#### Recomendación
**APROBADA** ✅ - Totalmente compatible con Kai.

---

### 12. Oobabooga Text Generation WebUI

**Licencia**: GNU Affero General Public License 3.0 (AGPL 3.0)  
**Repositorio**: https://github.com/oobabooga/text-generation-webui  
**Estado**: Evaluación de licencia

#### Términos Clave
- ⚠️ Copyleft fuerte
- ⚠️ Si se usa como servicio web, código debe liberarse
- ❌ No compatible con código propietario en servicios

#### Compatibilidad
AGPL 3.0 es muy restrictiva:
- Requiere liberar TODO el código si se usa como servicio
- Infecta a código que lo usa en red
- NO compatible con código propietario en servicios SaaS

#### Recomendación
**NO APROBADA** ❌ - Solo usar si:
1. No se despliega como servicio
2. Se usa solo localmente
3. Todo el código de Kai se libera bajo AGPL

**Alternativa**: Usar otros frameworks de LLM con licencias permisivas.

---

## Matriz de Compatibilidad

| Dependencia | Licencia | Comercial | Propietario | SaaS | Distribución | Estado |
|------------|----------|-----------|-------------|------|--------------|--------|
| langchain | MIT | ✅ | ✅ | ✅ | ✅ | ✅ |
| coqui-ai/TTS | MPL 2.0 | ✅ | ✅ | ✅ | ✅ | ✅ |
| whisper | MIT | ✅ | ✅ | ✅ | ✅ | ✅ |
| autotrain | Apache 2.0 | ✅ | ✅ | ✅ | ✅ | ✅ |
| faiss | MIT | ✅ | ✅ | ✅ | ✅ | ✅ |
| terraform-google-* | Apache 2.0 | ✅ | ✅ | ✅ | ✅ | ✅ |
| chromadb | Apache 2.0 | ✅ | ✅ | ✅ | ✅ | ✅ |
| rasa | Apache 2.0 | ✅ | ✅ | ✅ | ✅ | ✅ |
| semantic-kernel | MIT | ✅ | ✅ | ✅ | ✅ | ✅ |
| pgvector | PostgreSQL | ✅ | ✅ | ✅ | ✅ | ✅ |
| text-gen-webui | AGPL 3.0 | ⚠️ | ❌ | ❌ | ⚠️ | ❌ |

---

## Tipos de Licencias Explicadas

### MIT License
**Tipo**: Permisiva  
**Resumen**: La más permisiva. Permite cualquier uso con mínimos requisitos.

**Requisitos**:
- Incluir aviso de copyright y licencia

**Permite**:
- Uso comercial
- Modificación
- Distribución
- Uso privado
- Código propietario

---

### Apache License 2.0
**Tipo**: Permisiva  
**Resumen**: Similar a MIT pero con cláusula de patentes.

**Requisitos**:
- Incluir aviso de copyright y licencia
- Incluir archivo NOTICE si existe
- Indicar cambios realizados

**Permite**:
- Uso comercial
- Modificación
- Distribución
- Uso privado
- Código propietario

**Ventaja adicional**: Protección de patentes

---

### Mozilla Public License 2.0 (MPL)
**Tipo**: Copyleft débil  
**Resumen**: Requiere compartir modificaciones, pero solo de archivos MPL.

**Requisitos**:
- Modificaciones a archivos MPL deben compartirse bajo MPL
- Incluir aviso de licencia

**Permite**:
- Uso comercial
- Combinar con código propietario
- Nuevo código con cualquier licencia

**Restricción**: Solo afecta a archivos modificados del proyecto MPL

---

### PostgreSQL License
**Tipo**: Permisiva  
**Resumen**: Similar a MIT/BSD.

**Requisitos**:
- Incluir aviso de copyright y licencia

**Permite**:
- Uso comercial
- Modificación
- Distribución
- Uso privado

---

### GNU AGPL 3.0
**Tipo**: Copyleft fuerte  
**Resumen**: Versión más restrictiva de GPL para servicios en red.

**Requisitos**:
- TODO código que usa AGPL debe liberarse bajo AGPL
- Incluir si se ofrece como servicio (SaaS)
- Proporcionar código fuente a usuarios del servicio

**Restricciones**:
- ❌ No compatible con código propietario
- ❌ Infecta todo el código del servicio
- ❌ Requiere liberar backend si es servicio web

---

## Recomendaciones Legales

### Para Uso Comercial de Kai

1. **Dependencias Aprobadas** (MIT, Apache 2.0, MPL 2.0):
   - Usar sin preocupaciones
   - Incluir avisos de copyright en distribuciones
   - Mantener archivo NOTICE con todas las licencias

2. **Dependencias MPL 2.0** (Coqui TTS):
   - ✅ Usar como biblioteca (sin modificar)
   - ⚠️ Si modificamos código de Coqui TTS, compartir cambios
   - ✅ Nuestro código puede ser propietario

3. **Dependencias AGPL 3.0** (text-generation-webui):
   - ❌ NO usar en producción SaaS
   - ✅ OK para desarrollo local
   - ✅ Buscar alternativas con licencias permisivas

### Archivo NOTICE Sugerido

Crear `/NOTICE` con:

```
Kai - Compañero Virtual Avanzado
Copyright 2024-2025 Bashull

Este proyecto incorpora componentes de los siguientes proyectos:

1. LangChain (MIT License)
   Copyright (c) LangChain, Inc.
   https://github.com/langchain-ai/langchain

2. Coqui TTS (Mozilla Public License 2.0)
   Copyright (c) Coqui GmbH
   https://github.com/coqui-ai/TTS

3. OpenAI Whisper (MIT License)
   Copyright (c) OpenAI
   https://github.com/openai/whisper

4. Autotrain Advanced (Apache License 2.0)
   Copyright (c) Hugging Face
   https://github.com/huggingface/autotrain-advanced

5. FAISS (MIT License)
   Copyright (c) Facebook, Inc.
   https://github.com/facebookresearch/faiss

6. Terraform Google Modules (Apache License 2.0)
   Copyright (c) Google LLC
   https://github.com/terraform-google-modules

Las licencias completas se encuentran en el directorio /licenses/
```

---

## Verificación de Cumplimiento

### Checklist

- [ ] Crear archivo `/NOTICE` con todas las atribuciones
- [ ] Incluir copias de licencias en `/licenses/`
- [ ] Documentar modificaciones a código MPL 2.0
- [ ] Verificar que no se use código AGPL en producción
- [ ] Incluir avisos de copyright en distribuciones binarias
- [ ] Revisar licencias de nuevas dependencias antes de integrar

### Herramientas de Verificación

```bash
# Python: liccheck
pip install liccheck
liccheck -r requirements.txt

# Node.js: license-checker
npm install -g license-checker
license-checker --summary

# Terraform: manual review
grep -r "source.*github.com" *.tf
```

---

## Conclusión

✅ **Kai puede usarse comercialmente con las dependencias actuales**

**Únicas consideraciones**:
1. Incluir avisos de copyright (archivo NOTICE)
2. No modificar directamente código de Coqui TTS (o compartir si modificamos)
3. NO usar `text-generation-webui` en producción SaaS

**Todo lo demás**: Totalmente libre y compatible con uso comercial y código propietario.

---

**Descargo de responsabilidad legal**: Este documento es un análisis informativo y no constituye asesoría legal. Para decisiones legales críticas, consultar con un abogado especializado en propiedad intelectual.

---

**Última revisión**: 2025-10-14  
**Revisado por**: Equipo Kai  
**Próxima revisión**: Al añadir nuevas dependencias
