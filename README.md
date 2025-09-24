# rootly Analytics Service

Este es el servicio de análisis avanzado para el sistema de monitoreo agrícola rootly. Proporciona métricas analíticas complejas basadas en datos de sensores para apoyar la toma de decisiones en agricultura.

## Características Principales

- **Análisis Agrícola Avanzado**: Implementa métricas especializadas como GDD, VPD, WDI, DLI y Punto de Rocío
- **Arquitectura Hexagonal**: Separación clara entre lógica de negocio e infraestructura
- **API REST Moderna**: Construida con FastAPI y documentación automática
- **Procesamiento Asíncrono**: Manejo eficiente de múltiples solicitudes concurrentes
- **Integración HTTP**: Consume datos del servicio de Go backend
- **Containerización**: Totalmente dockerizado para fácil despliegue

## Arquitectura

El servicio sigue los principios de **Arquitectura Hexagonal (Ports and Adapters)**:

```
src/
├── core/                    # Lógica de negocio (dominio puro)
│   ├── domain/             # Entidades y objetos de valor
│   ├── ports/              # Interfaces (contratos)
│   └── services/           # Lógica de negocio
├── adapters/               # Implementaciones de infraestructura
│   ├── handlers/           # Controladores FastAPI
│   └── http/              # Cliente HTTP para Go service
└── main.py                # Punto de entrada de la aplicación
```

## 📊 Métricas Analíticas Implementadas

### 1. **Growing Degree Days (GDD)**
- **Propósito**: Predice etapas de desarrollo vegetal
- **Fórmula**: `GDD = (T_max + T_min) / 2 - T_base`

### 2. **Punto de Rocío (Dew Point)**
- **Propósito**: Temperatura de condensación del vapor de agua
- **Fórmula**: `Td = 243.12 * (ln(RH/100) + (17.62 * T) / (243.12 + T)) / (17.62 - (ln(RH/100) + (17.62 * T) / (243.12 + T)))`

### 3. **Water Deficit Index (WDI)**
- **Propósito**: Indicador de estrés hídrico del cultivo
- **Fórmula**: `WDI = ((Moisture_Max - Moisture_Actual) / (Moisture_Max - Moisture_Min)) * 100`

### 4. **Daily Light Integral (DLI)**
- **Propósito**: Radiación fotosintética total diaria
- **Fórmula**: `DLI = (Average_Light_Reading * 3600 * 24) / 1000000`

### 5. **Vapor Pressure Deficit (VPD)**
- **Propósito**: Indicador clave de transpiración vegetal
- **Fórmulas**: 
  - `SVP = 0.6108 * exp((17.27 * T) / (T + 237.3))`
  - `AVP = (RH / 100) * SVP`
  - `VPD = SVP - AVP`

##  Endpoints de la API

### 1. Reporte de Métrica Individual
```
GET /api/v1/analytics/report/{metric_name}
```
**Parámetros de consulta:**
- `id_controlador` (requerido): ID del dispositivo controlador
- `start_time` (opcional): Tiempo de inicio (formato ISO)
- `end_time` (opcional): Tiempo de fin (formato ISO)
- `limit` (opcional): Número máximo de registros

### 2. Reporte Multi-Métrica
```
POST /api/v1/analytics/multi-report
```
**Cuerpo de la solicitud:**
```json
{
  "controllers": ["device-01", "device-02"],
  "metrics": ["temperatura", "humedad_tierra"],
  "filters": {
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-02T00:00:00Z",
    "limit": 1000
  }
}
```

### 3. Análisis de Tendencias
```
GET /api/v1/analytics/trends/{metric_name}
```
**Parámetros de consulta:**
- `id_controlador` (requerido): ID del dispositivo
- `start_time` (requerido): Tiempo de inicio
- `end_time` (requerido): Tiempo de fin
- `interval` (opcional): Intervalo de agregación (ej: "1h", "1d")

### 4. Métricas Soportadas
```
GET /api/v1/analytics/metrics
```
Retorna la lista de métricas disponibles: `["temperatura", "humedad_aire", "humedad_tierra", "luminosidad"]`

##  Instalación y Ejecución

### Prerrequisitos
- Docker

### Desarrollo Local

1. **Configurar variables de entorno:**
```bash
cp config.py .env
# Editar .env con las configuraciones apropiadas
```

2. **Ejecutar con Docker Compose (en la carpeta rootly-deployment):**
```bash
docker-compose up -d
```

El servicio estará disponible en:
- **API**: http://localhost:8000
- **Documentación Swagger**: http://localhost:8000/docs
- **Documentación ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Configuración

El servicio se configura mediante variables de entorno:

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `INFLUXDB_URL` | URL del servidor InfluxDB | `http://influxdb:8086` |
| `INFLUXDB_TOKEN` | Token de autenticación InfluxDB | `super-secret-influx-token` |
| `INFLUXDB_BUCKET` | Bucket de datos en InfluxDB | `agricultural_data` |
| `INFLUXDB_ORG` | Organización en InfluxDB | `rootly` |
| `CORS_ORIGINS` | Orígenes permitidos para CORS | `*` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |

## Pruebas

```bash
# Ejecutar pruebas unitarias
pytest

# Con cobertura
pytest --cov=src

# Ejecutar pruebas unitarias

pytest tests/unit

# Pruebas específicas
pytest tests/test_analytics_calculations.py

# Ejecutar pruebas de integracion ( con el servicio y dependencias encendidas)
pytest -m integration
```

## Documentación API

Una vez ejecutado el servicio, la documentación interactiva está disponible en:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Monitoreo y Salud

### Health Check
```
GET /health
```
Verifica el estado del servicio y la conectividad con InfluxDB.

### Logs
El servicio implementa un sistema de logging estructurado siguiendo el patrón de interfaz/puerto:

- **Interfaz Logger**: Define el contrato para operaciones de logging
- **Implementación StandardLogger**: Usa el módulo `logging` de Python
- **Características**:
  - Logs estructurados con información contextual
  - Niveles: DEBUG, INFO, WARNING, ERROR
  - Formato consistente: timestamp, nombre, nivel, mensaje
  - Información detallada sobre:
    - Solicitudes HTTP entrantes
    - Comunicación con InfluxDB
    - Cálculos de métricas analíticas
    - Errores y excepciones

## Integración con el Ecosistema rootly

Este servicio funciona como parte del ecosistema rootly:

1. **Servicio de Data Management** (rootly-data-management-backend):
   - Maneja ingesta y gestión de datos de sensores
   - Almacena datos en InfluxDB y MinIO
   - Proporciona APIs GraphQL para gestión de datos

2. **Servicio de Analytics** (este servicio):
   - Se conecta directamente a InfluxDB para análisis
   - Aplica algoritmos agrícolas avanzados
   - Proporciona APIs REST con documentación automática

3. **Frontend** (rootly-frontend):
   - Consume APIs de analytics
   - Presenta visualizaciones de datos
   - Interfaz de usuario para agricultores

## Solución de Problemas

### Error de Conexión a InfluxDB
```
RepositoryError: Failed to fetch measurements from InfluxDB
```
**Solución**: Verificar que InfluxDB esté ejecutándose y accesible en la URL configurada.

### Error de Métrica No Soportada
```
InvalidMetricError: Metric 'xxx' is not supported
```
**Solución**: Usar `/api/v1/analytics/metrics` para obtener métricas válidas.

### Error de Datos Insuficientes
```
InsufficientDataError: No data found
```
**Solución**: Verificar que existen datos para el controlador y rango de tiempo especificado.