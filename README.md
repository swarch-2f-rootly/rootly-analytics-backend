# rootly Analytics Service

Este es el servicio de análisis avanzado para el sistema de monitoreo agrícola rootly. Proporciona métricas analíticas complejas basadas en datos de sensores para apoyar la toma de decisiones en agricultura.

## Características Principales

- **Análisis Agrícola Avanzado**: Implementa métricas especializadas como GDD, VPD, WDI, DLI y Punto de Rocío
- **Arquitectura Hexagonal**: Separación clara entre lógica de negocio e infraestructura
- **API REST Moderna**: Construida con FastAPI y documentación automática
- **API GraphQL**: Implementada con Strawberry GraphQL para consultas flexibles
- **Procesamiento Asíncrono**: Manejo eficiente de múltiples solicitudes concurrentes
- **Integración InfluxDB**: Acceso directo a datos de series temporales
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
│   ├── handlers/           # Controladores REST API
│   ├── graphql/            # Esquemas y resolvers GraphQL
│   ├── repositories/       # Acceso a datos (InfluxDB)
│   └── logger/             # Sistema de logging
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

## 🚀 API Documentation

El servicio expone dos tipos de APIs para máxima flexibilidad:

### **REST API** - Endpoints tradicionales
### **GraphQL API** - Consultas flexibles y tipadas

---

## 📡 REST API Endpoints

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

### 4. Consultas Históricas
```
GET /api/v1/analytics/historical
```
**Parámetros de consulta opcionales:**
- `start_time` / `end_time`: Rango de fechas en formato ISO 8601
- `controller_id`: Identificador del controlador
- `sensor_id`: Identificador del sensor asociado
- `zone`: Zona geográfica o lógica
- `parameter`: Parámetro a consultar (`temperature`, `soil_humidity`, etc.)
- `limit`: Número máximo de registros a retornar (1-10000)

### 5. Métricas Soportadas
```
GET /api/v1/analytics/metrics
```
Retorna la lista de métricas disponibles: `["temperatura", "humedad_aire", "humedad_tierra", "luminosidad"]`

---

## 🎯 GraphQL API

La API GraphQL está disponible en `/api/v1/graphql` y proporciona consultas flexibles y tipadas.

### **GraphQL Playground**
Interfaz interactiva disponible en: `http://localhost:8000/api/v1/graphql`
- Explorar esquema
- Probar consultas
- Documentación automática
- Validación de sintaxis

### **Consultas GraphQL Disponibles**

#### 1. **Consultar Métricas Soportadas**
```graphql
query {
  getSupportedMetrics
}
```

#### 2. **Estado de Salud del Servicio**
```graphql
query {
  getAnalyticsHealth {
    status
    service
    influxdb
    influxdbUrl
    timestamp
  }
}
```

#### 3. **Reporte de Métrica Individual**
```graphql
query SingleMetricReport {
  getSingleMetricReport(
    metricName: "temperature"
    controllerId: "FARM-001"
    filters: {
      startTime: "2025-08-01T00:00:00Z"
      endTime: "2025-09-30T23:59:59Z"
      limit: 100
    }
  ) {
    controllerId
    generatedAt
    dataPointsCount
    metrics {
      metricName
      value
      unit
      calculatedAt
      controllerId
      description
    }
  }
}
```

#### 4. **Reporte Multi-Métrica**
```graphql
query MultiMetricReport {
  getMultiMetricReport(
    input: {
      controllers: ["FARM-001", "FARM-002"]
      metrics: ["temperature", "humidity", "light_intensity"]
      filters: {
        startTime: "2025-08-01T00:00:00Z"
        endTime: "2025-09-30T23:59:59Z"
        limit: 50
      }
    }
  ) {
    generatedAt
    totalControllers
    totalMetrics
    reports {
      controllerId
      dataPointsCount
      generatedAt
      metrics {
        metricName
        value
        unit
        calculatedAt
        controllerId
        description
      }
    }
  }
}
```

#### 5. **Análisis de Tendencias**
```graphql
query TrendAnalysis {
  getTrendAnalysis(
    input: {
      metricName: "temperature"
      controllerId: "FARM-001"
      startTime: "2025-08-01T00:00:00Z"
      endTime: "2025-09-30T23:59:59Z"
      interval: "1h"
    }
  ) {
    metricName
    controllerId
    interval
    generatedAt
    totalPoints
    averageValue
    minValue
    maxValue
    dataPoints {
      timestamp
      value
      interval
    }
  }
}
```

### **Cómo Probar GraphQL**

#### **Usando curl**
```bash
# Consulta básica
curl -X POST http://localhost:8000/api/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getSupportedMetrics }"}'

# Consulta con variables
curl -X POST http://localhost:8000/api/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetReport($metricName: String!, $controllerId: String!) { getSingleMetricReport(metricName: $metricName, controllerId: $controllerId) { controllerId generatedAt dataPointsCount } }",
    "variables": {
      "metricName": "temperature",
      "controllerId": "controller-123"
    }
  }'
```

#### **Usando Postman o Insomnia**
1. Crear nueva petición POST a `http://localhost:8000/api/v1/graphql`
2. Agregar header `Content-Type: application/json`
3. En el body (JSON), enviar:
```json
{
  "query": "{ getSupportedMetrics }"
}
```

#### **Introspección del Esquema**
```bash
curl -X POST http://localhost:8000/api/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "query IntrospectionQuery { __schema { queryType { name fields { name description } } } }"}'
```

### **Tipos GraphQL Principales**

#### **MetricResult**
```graphql
type MetricResult {
  metricName: String!
  value: Float!
  unit: String!
  calculatedAt: DateTime!
  controllerId: String!
  description: String
}
```

#### **AnalyticsReport**
```graphql
type AnalyticsReport {
  controllerId: String!
  generatedAt: DateTime!
  dataPointsCount: Int!
  metrics: [MetricResult!]!
}
```

#### **TrendAnalysis**
```graphql
type TrendAnalysis {
  metricName: String!
  controllerId: String!
  interval: String!
  generatedAt: DateTime!
  totalPoints: Int!
  averageValue: Float!
  minValue: Float!
  maxValue: Float!
  dataPoints: [TrendDataPoint!]!
}
```

### **Inputs GraphQL**

#### **AnalyticsFilterInput**
```graphql
input AnalyticsFilterInput {
  startTime: DateTime
  endTime: DateTime
  limit: Int
}
```

#### **MultiMetricReportInput**
```graphql
input MultiMetricReportInput {
  controllers: [String!]!
  metrics: [String!]!
  filters: AnalyticsFilterInput
}
```

#### **TrendAnalysisInput**
```graphql
input TrendAnalysisInput {
  metricName: String!
  controllerId: String!
  startTime: DateTime!
  endTime: DateTime!
  interval: String
}
```

---

## ⚙️ Instalación y Ejecución

### Prerrequisitos
- Docker
- Python 3.11+ (para desarrollo local)

### Desarrollo Local

#### Opción 1: Docker Compose
```bash
# En la carpeta rootly-deploy
docker-compose up -d
```

#### Opción 2: Desarrollo Local
```bash
# Clonar repositorio
git clone <repository-url>
cd rootly-analytics-backend

# Crear ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu configuración

# Ejecutar servicio
python -m src.main
```

El servicio estará disponible en:
- **API REST**: http://localhost:8000
- **API GraphQL**: http://localhost:8000/api/v1/graphql
- **GraphQL Playground**: http://localhost:8000/api/v1/graphql (interfaz interactiva)
- **Documentación Swagger**: http://localhost:8000/docs
- **Documentación ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🔧 Configuración

El servicio se configura mediante variables de entorno:

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `INFLUXDB_URL` | URL del servidor InfluxDB | `http://localhost:8086` |
| `INFLUXDB_TOKEN` | Token de autenticación InfluxDB | `your-influxdb-token-here` |
| `INFLUXDB_BUCKET` | Bucket de datos en InfluxDB | `rootly-bucket` |
| `INFLUXDB_ORG` | Organización en InfluxDB | `rootly-org` |
| `CORS_ORIGINS` | Orígenes permitidos para CORS | `*` |
| `HOST` | Host del servidor | `0.0.0.0` |
| `PORT` | Puerto del servidor | `8000` |
| `LOG_LEVEL` | Nivel de logging | `info` |
| `GRAPHQL_PLAYGROUND_ENABLED` | Habilitar GraphQL Playground | `true` |
| `GRAPHQL_INTROSPECTION_ENABLED` | Habilitar introspección GraphQL | `true` |

### Archivo .env.example
```bash
# InfluxDB Configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=super-secret-influx-token
INFLUXDB_BUCKET=agricultural_data
INFLUXDB_ORG=rootly

# Server Configuration
HOST=0.0.0.0
PORT=8000

# GraphQL Configuration
GRAPHQL_PLAYGROUND_ENABLED=true
GRAPHQL_INTROSPECTION_ENABLED=true

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://localhost:8000,*

# Logging Configuration
LOG_LEVEL=INFO
```

## 🧪 Pruebas

```bash
# Ejecutar pruebas unitarias
pytest

# Con cobertura
pytest --cov=src

# Ejecutar pruebas unitarias
pytest tests/unit

# Pruebas específicas
pytest tests/test_analytics_calculations.py

# Ejecutar pruebas de integración (con el servicio y dependencias encendidas)
pytest -m integration
```

## 📚 Documentación API

Una vez ejecutado el servicio, la documentación interactiva está disponible en:

### **REST API Documentation**
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### **GraphQL API Documentation**
- **GraphQL Playground**: http://localhost:8000/api/v1/graphql
  - Explorador de esquemas interactivo
  - Editor de consultas con sintaxis resaltada
  - Documentación automática de tipos
  - Validación en tiempo real

## 🔍 Monitoreo y Salud

### Health Check
```
GET /health
```
Verifica el estado del servicio y la conectividad con InfluxDB.

**Respuesta ejemplo:**
```json
{
  "status": "healthy",
  "service": "analytics",
  "influxdb": "healthy",
  "influxdb_url": "http://localhost:8086",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Logs
El servicio implementa un sistema de logging estructurado:

- **Interfaz Logger**: Define el contrato para operaciones de logging
- **Implementación StandardLogger**: Usa el módulo `logging` de Python
- **Características**:
  - Logs estructurados con información contextual
  - Niveles: DEBUG, INFO, WARNING, ERROR
  - Información detallada sobre:
    - Solicitudes HTTP y GraphQL entrantes
    - Comunicación con InfluxDB
    - Cálculos de métricas analíticas
    - Errores y excepciones

## 🌐 Integración con el Ecosistema rootly

Este servicio funciona como parte del ecosistema rootly:

1. **API Gateway** (rootly-apigateway):
   - Orquesta llamadas entre servicios
   - Proporciona GraphQL unificado
   - Maneja autenticación y autorización

2. **Servicio de Data Management** (rootly-data-management-backend):
   - Maneja ingesta y gestión de datos de sensores
   - Almacena datos en InfluxDB y MinIO
   - Proporciona APIs para gestión de datos

3. **Servicio de Analytics** (este servicio):
   - Se conecta directamente a InfluxDB para análisis
   - Aplica algoritmos agrícolas avanzados
   - Proporciona APIs REST y GraphQL

4. **Frontend** (rootly-frontend):
   - Consume APIs de analytics a través del API Gateway
   - Presenta visualizaciones de datos
   - Interfaz de usuario para agricultores

## 🚨 Solución de Problemas

### Error de Conexión a InfluxDB
```
RepositoryError: Failed to fetch measurements from InfluxDB
```
**Soluciones**:
- Verificar que InfluxDB esté ejecutándose
- Comprobar la URL y token de configuración
- Revisar conectividad de red

### Error de Métrica No Soportada
```
InvalidMetricError: Metric 'xxx' is not supported
```
**Soluciones**:
- Usar `/api/v1/analytics/metrics` o `getSupportedMetrics` en GraphQL
- Verificar que la métrica existe en los datos

### Error de Datos Insuficientes
```
InsufficientDataError: No data found
```
**Soluciones**:
- Verificar que existen datos para el controlador especificado
- Ajustar el rango de tiempo de la consulta
- Revisar que el InfluxDB contiene datos para ese período

### GraphQL Playground No Carga
**Soluciones**:
- Verificar que `GRAPHQL_PLAYGROUND_ENABLED=true`
- Comprobar que el servicio está ejecutándose
- Acceder directamente a `/api/v1/graphql`

### Errores de Validación GraphQL
**Soluciones**:
- Usar el explorador de esquemas en GraphQL Playground
- Verificar que los tipos de datos coincidan
- Revisar la sintaxis de la consulta

---

## 🔗 Enlaces Útiles

- **Código Fuente**: [GitHub Repository]
- **Documentación GraphQL**: [Strawberry GraphQL](https://strawberry.rocks/)
- **Documentación FastAPI**: [FastAPI](https://fastapi.tiangolo.com/)
- **InfluxDB**: [InfluxDB Documentation](https://docs.influxdata.com/)
