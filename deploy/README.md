# MarketMind en una sola máquina

Levanta todo el sistema con Docker Compose: una base de datos Postgres (una
base por servicio), los cuatro colectores, el servicio de scoring, el
orquestador (el agente LangGraph con el que habla el navegador) y el frontend.
El gateway opcional a un Ollama local va bajo el perfil `local-llm`.

Los repositorios hermanos no se modifican: cada servicio se construye con su
propio `Dockerfile`; `deploy/docker-compose.yml` sólo los conecta.

## Requisitos

- Docker Desktop (o Docker Engine) con Compose v2: `docker compose version`.
  Probado en macOS arm64 con Compose v5.
- `make`, `curl` y `python3` (sólo para el formateo en `bootstrap.sh`).
- Credenciales: una clave de Anthropic y una cuenta de DataForSEO (login y
  *API password*). Voyage AI es recomendable (búsqueda semántica del catálogo);
  OpenAI, Langfuse y el juez de alucinaciones son opcionales.
- Puertos libres en el host: 8000-8004, 8080, 8081 y 5440 por defecto (8005 con
  el perfil `local-llm`). Todos se cambian en `deploy/.env`.

## 1. Clonar los repositorios como hermanos

Los contextos de build son rutas relativas (`../../marketmind-<nombre>`), así
que los ocho repositorios tienen que estar en el mismo directorio padre:

```
Mestrado/
├── marketmind-ai/                    # este repo: frontend + deploy/
├── marketmind-orchestrator/
├── marketmind-scoring/
├── marketmind-pytrends/
├── marketmind-worldbank/
├── marketmind-oecd/
├── marketmind-united-nations-data/
└── marketmind-ollma-llm/             # opcional (perfil local-llm)
```

## 2. Configurar

```bash
cd marketmind-ai
cp deploy/.env.example deploy/.env
```

Rellenar los valores marcados `REQUIRED` en `deploy/.env`:
`POSTGRES_PASSWORD`, `INTERNAL_API_TOKEN` (cualquier cadena aleatoria larga,
compartida entre scoring y orquestador), `ANTHROPIC_API_KEY`,
`DATAFORSEO_LOGIN` y `DATAFORSEO_PASSWORD`. El resto tiene valores por defecto
que funcionan. `deploy/.env` está en `.gitignore`: nunca se sube.

## 3. Levantar

```bash
make up          # docker compose ... up -d --build  (la primera vez tarda varios minutos)
make bootstrap   # espera a los servicios, calibra los pesos del MOS, imprime el health
```

`make bootstrap` es idempotente: se puede repetir en cualquier momento. Al
terminar imprime el `GET /health` del scoring, que debe mostrar `database:
connected` y las cuatro fuentes (`pytrends`, `worldbank`, `oecd`, `undata`) en
`connected`.

Otros objetivos: `make ps`, `make logs` (`make logs S=scoring` para uno solo),
`make down` (conserva los datos; `make down V=1` borra también el volumen de
Postgres).

## Puertos

| Servicio                 | Host (defecto)   | Variable            | Salud                |
|--------------------------|------------------|---------------------|----------------------|
| Web (frontend)           | `localhost:8080` | `WEB_PORT`          | `/healthz`           |
| Orquestador              | `localhost:8081` | `ORCHESTRATOR_PORT` | `/healthz`, `/docs`  |
| Scoring                  | `localhost:8004` | `SCORING_PORT`      | `/health`, `/docs`   |
| PyTrends (DataForSEO)    | `localhost:8000` | `PYTRENDS_PORT`     | `/healthz`           |
| OECD                     | `localhost:8001` | `OECD_PORT`         | `/healthz`           |
| UN Data                  | `localhost:8002` | `UNDATA_PORT`       | `/healthz`           |
| World Bank               | `localhost:8003` | `WORLDBANK_PORT`    | `/healthz`           |
| Ollama gateway (perfil)  | `localhost:8005` | `OLLMA_PORT`        | `/health`            |
| Postgres                 | `localhost:5440` | `POSTGRES_PORT`     | —                    |

Dentro de la red de Compose los servicios se llaman por su nombre
(`http://scoring:8000`, `http://orchestrator:8000`, `postgres:5432`); los
puertos del host sólo importan desde fuera.

Bases de datos (mismo usuario y contraseña, creadas por
`deploy/postgres/init.sh` en el primer arranque): `marketmind_core`,
`marketmind_orchestrator`, `marketmind_pytrends`, `marketmind_worldbank`,
`marketmind_oecd`, `marketmind_undata`.

## Cómo llega el navegador a la API

El bundle del frontend se construye con `PUBLIC_API_BASE=/api`. El nginx del
contenedor web (`deploy/nginx/default.conf`) reenvía `/api/` al orquestador, de
modo que el navegador siempre habla con su propio origen y no hay CORS que
configurar; es el mismo esquema que el despliegue en la nube. Si se cambia
`WEB_API_BASE` o `WEB_PORT` hay que volver a ejecutar `make up` (la imagen del
web se reconstruye).

## Primer análisis

1. Abrir `http://localhost:8080`.
2. Subir una foto del producto (o escribir su nombre). El orquestador llama al
   scoring, que identifica el producto y propone los términos de búsqueda por
   país; se pueden corregir antes de seguir.
3. Elegir los países y lanzar el análisis. El progreso llega por SSE; al
   terminar se abre el informe con el MOS de cada mercado.

Por API, el mismo flujo contra el orquestador:

```bash
curl -s http://localhost:8081/countries | python3 -m json.tool | head   # mercados disponibles
curl -s http://localhost:8081/docs                                      # OpenAPI
```

Con `DATAFORSEO_USE_SANDBOX=true` la demanda viene de datos simulados (no se
factura, pero el resultado no vale); un análisis real requiere `false`.

## Perfil `local-llm` (Ollama)

Para que algún sitio de llamada use un modelo local en vez de Claude:

1. Tener Ollama corriendo en el host (`http://localhost:11434`) con el modelo
   descargado (`ollama pull qwen3:14b`).
2. En `deploy/.env`, poner `*_LLM_PROVIDER=ollama` y `*_LLM_MODEL=<modelo>` en
   los sitios deseados (por ejemplo `EXPLANATION_LLM_PROVIDER=ollama`). El de
   visión y el de mercado de referencia conviene dejarlos en Claude.
3. Levantar con el perfil:

```bash
make up PROFILE=local-llm
```

El scoring llega al gateway como `http://ollma-llm:8005`; el gateway llega al
Ollama del host como `http://host.docker.internal:11434` (`OLLAMA_BASE_URL`).
`make down` detiene también los servicios del perfil.

## Problemas habituales

- **Un puerto está ocupado**: cambiar la variable correspondiente en
  `deploy/.env` y `make up`. Los servicios no dependen de los puertos del host.
- **`bootstrap` espera y no termina**: `make logs S=<servicio>`. El scoring y
  los colectores ejecutan `alembic upgrade head` al arrancar; si Postgres aún
  no estaba listo, Compose los reinicia solos.
- **Cambié la contraseña de Postgres después del primer arranque**: la base ya
  existe con la anterior. `make down V=1` y `make up` la recrean desde cero.
- **El web muestra errores de red**: comprobar `curl localhost:8080/api/healthz`
  (pasa por nginx hasta el orquestador) y `curl localhost:8081/healthz`.
