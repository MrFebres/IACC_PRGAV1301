# Sistema de Logistica

App de escritorio en Python + Tkinter para gestionar envios logisticos. Usa MySQL como base de datos y se configura mediante un archivo `.env`.

## Pre-requisitos

| Herramienta | Version minima | Notas                                    |
| ----------- | -------------- | ---------------------------------------- |
| **Python**  | 3.12           | Debe incluir soporte para Tkinter        |
| **uv**      | —              | Gestor de dependencias recomendado       |
| **MySQL**   | 8.x            | Local o remoto accesible desde tu equipo |

## Configuracion del `.env`

El repositorio incluye un `.env.example` con **todas** las variables que la app necesita. Copia el archivo y ajusta los valores a tu entorno:

```bash
cp .env.example .env
```

### Variables de base de datos

| Variable         | Descripcion                        | Valor por defecto |
| ---------------- | ---------------------------------- | ----------------- |
| `MYSQL_HOST`     | Host del servidor MySQL            | `127.0.0.1`       |
| `MYSQL_PORT`     | Puerto del servidor                | `3306`            |
| `MYSQL_DATABASE` | Nombre de la base de datos         | `logistics_db`    |
| `MYSQL_USER`     | Usuario con permisos sobre la base | `root`            |
| `MYSQL_PASSWORD` | Contrasena del usuario             | _(vacio)_         |

### Variables de interfaz

| Variable     | Descripcion          | Valor por defecto      |
| ------------ | -------------------- | ---------------------- |
| `APP_TITLE`  | Titulo de la ventana | `Sistema de Logistica` |
| `APP_WIDTH`  | Ancho inicial (px)   | `800`                  |
| `APP_HEIGHT` | Alto inicial (px)    | `480`                  |

> **Importante:** Sin un `.env` valido la ventana puede abrirse con valores por defecto, pero cualquier operacion contra MySQL fallara. Asegurate de tener este archivo antes de ejecutar la app.

## Preparar la base de datos

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS logistics_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p logistics_db < sql/schema.sql
```

Si usas un nombre de base distinto, actualiza `MYSQL_DATABASE` en tu `.env`.

## Ejecutar la app en local

```bash
# Instalar dependencias + iniciar
uv sync && uv run python main.py
```

<details>
<summary>Alternativa con <code>venv</code></summary>

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
python main.py
```

</details>

## Resumen rapido

```bash
cp .env.example .env   # 1. Configurar entorno
uv sync                # 2. Instalar dependencias
uv run python main.py  # 3. Iniciar la app
```

Al ejecutar deberias ver la ventana **Sistema de Logistica** sin errores.
