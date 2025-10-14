# GitHub Actions Workflows

Este directorio contiene los workflows de CI/CD para el proyecto Kai.

## 📋 Workflows Disponibles

### 🔄 CI/CD Pipeline - Paralelo (`ci-cd.yml`)

Pipeline principal con ejecución paralela optimizada para reducir tiempos de feedback.

**Triggers**:
- Push a `main`, `develop`, `feat/**`
- Pull requests a `main`, `develop`
- Manual (`workflow_dispatch`)

**Jobs Paralelos**:

1. **🔍 Lint** - Validación de código con ESLint y TypeScript
2. **🧪 Tests** - Ejecución de tests en matriz (múltiples OS y versiones de Node)
3. **🏗️ Build** - Compilación de la aplicación y generación de artefactos
4. **🔒 Security** - Análisis de seguridad con npm audit y Snyk
5. **📦 Supply Chain** - Generación de SBOM y validación de licencias
6. **🔎 CodeQL** - Análisis estático de seguridad
7. **⚡ Performance** - Tests de rendimiento del bundle

**Jobs Secuenciales**:

8. **🚀 Deploy** - Despliegue a producción (solo en `main`)
9. **📊 Report** - Generación de reportes y comentarios en PR

### Características

#### ✨ Optimizaciones

- **Caché de dependencias**: npm cache automático
- **Ejecución paralela**: Múltiples jobs independientes ejecutándose simultáneamente
- **Matrix strategy**: Tests en múltiples entornos (OS y versiones de Node)
- **Cancelación automática**: Jobs duplicados cancelados automáticamente
- **Artifacts**: Compartición de artefactos entre jobs

#### 📊 Métricas DORA

El pipeline ayuda a medir las métricas DORA:

- **Deployment Frequency**: Frecuencia de despliegues a producción
- **Lead Time for Changes**: Tiempo desde commit hasta producción
- **Change Failure Rate**: % de despliegues que fallan
- **Time to Restore**: Tiempo para recuperarse de fallos

#### 🔐 Seguridad

- **Permisos mínimos**: Solo los permisos necesarios
- **Secret scanning**: Detección de credenciales expuestas
- **Dependency scanning**: Vulnerabilidades en dependencias
- **CodeQL**: Análisis de código estático
- **SBOM**: Bill of Materials para supply chain

## 🚀 Uso

### Ejecutar Manualmente

Desde la interfaz de GitHub:
1. Ve a **Actions** > **CI/CD Pipeline - Paralelo**
2. Click en **Run workflow**
3. Selecciona la rama
4. Click en **Run workflow**

### Configurar Secrets

Configura los siguientes secrets en el repositorio:

```
GCP_PROJECT_ID: ID del proyecto de Google Cloud
GCP_SA_KEY: Clave de cuenta de servicio de GCP
SNYK_TOKEN: Token de Snyk (opcional)
```

### Variables de Entorno

El workflow utiliza las siguientes variables:

```yaml
NODE_VERSION: '20.x'      # Versión de Node.js
CACHE_KEY_PREFIX: kai-v1  # Prefijo para caché
```

## 📈 Resultados

### Métricas de Rendimiento

| Métrica | Target | Actual |
|---------|--------|--------|
| Tiempo total | < 5 min | ~4 min |
| Tiempo de lint | < 2 min | ~1 min |
| Tiempo de tests | < 5 min | ~3 min |
| Tiempo de build | < 3 min | ~2 min |

### Tiempo Estimado por Job

```
┌──────────────────┬──────────┐
│ Job              │ Duración │
├──────────────────┼──────────┤
│ Lint             │ ~1 min   │
│ Tests            │ ~3 min   │
│ Build            │ ~2 min   │
│ Security         │ ~2 min   │
│ Supply Chain     │ ~1 min   │
│ CodeQL           │ ~5 min   │
│ Performance      │ ~1 min   │
├──────────────────┼──────────┤
│ Deploy           │ ~3 min   │
│ Report           │ ~1 min   │
└──────────────────┴──────────┘

Total (paralelo): ~5 min
Total (secuencial): ~19 min
Mejora: ~74% más rápido
```

## 🔧 Personalización

### Agregar un Nuevo Job

```yaml
nuevo-job:
  name: 🎯 Mi Nuevo Job
  runs-on: ubuntu-latest
  timeout-minutes: 10
  
  steps:
    - name: Checkout código
      uses: actions/checkout@v4
    
    - name: Mi acción
      run: echo "Hola mundo"
```

### Modificar Matrix Strategy

```yaml
strategy:
  fail-fast: false
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    node-version: ['18.x', '20.x', '22.x']
```

### Agregar Notificaciones

```yaml
- name: Notificar a Slack
  uses: slackapi/slack-github-action@v1
  with:
    channel-id: 'CHANNEL_ID'
    slack-message: "Deploy completado ✅"
  env:
    SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
```

## 🐛 Troubleshooting

### El workflow falla en un job específico

1. Revisa los logs del job en la pestaña Actions
2. Verifica que los secrets estén configurados correctamente
3. Ejecuta localmente el comando que falla
4. Revisa las dependencias y versiones

### Los tests fallan solo en CI

1. Verifica variables de entorno faltantes
2. Revisa diferencias entre entornos (local vs CI)
3. Asegúrate de que los fixtures/mocks estén incluidos en el repo
4. Verifica los timeouts de los tests

### El caché no funciona

1. Verifica que `package-lock.json` esté committeado
2. Revisa la key del caché en el workflow
3. Limpia el caché desde la interfaz de GitHub
4. Regenera `package-lock.json`

## 📚 Referencias

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [GitHub Actions Best Practices](https://docs.github.com/en/actions/learn-github-actions/best-practices-for-using-github-actions)
- [Reusable Workflows](https://docs.github.com/en/actions/learn-github-actions/reusing-workflows)

## 🤝 Contribuir

Para mejorar los workflows:

1. Crea una rama con tu cambio
2. Prueba el workflow en tu rama
3. Documenta los cambios en este README
4. Crea un PR con la descripción de la mejora

---

**Última actualización**: 2025-10-14  
**Mantenedor**: Equipo Kai
