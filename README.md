# Sistema de Logistica

Aplicacion de escritorio en Python con Tkinter para la base del sistema de logistica del proyecto. La app toma su configuracion desde un archivo `.env` en la raiz del repositorio y usa MySQL como base de datos.

## Pre requisitos

- Python 3.12 o superior
- `uv` instalado para gestionar dependencias y ejecutar el proyecto
- MySQL disponible localmente o en una instancia accesible desde tu equipo
- Una instalacion de Python con soporte para Tkinter

## Inicio rapido

1. Clona el repositorio y entra al proyecto.
2. Crea tu archivo `.env` a partir del ejemplo incluido.
3. Crea la base de datos y aplica el esquema.
4. Instala dependencias.
5. Ejecuta la app.

## Configurar `.env`

Este proyecto incluye un archivo `.env.example` con las variables necesarias para la app.

Primero crea tu archivo local:

```bash
cp .env.example .env
```

Despues revisa y ajusta estas variables:

- `MYSQL_HOST`: host del servidor MySQL
- `MYSQL_PORT`: puerto del servidor MySQL
- `MYSQL_DATABASE`: nombre de la base de datos
- `MYSQL_USER`: usuario con permisos sobre la base
- `MYSQL_PASSWORD`: password del usuario

Las variables `APP_TITLE`, `APP_WIDTH` y `APP_HEIGHT` controlan el titulo y el tamano inicial de la ventana.

## Por que `.env` es necesario

La aplicacion carga automaticamente el archivo `.env` desde la raiz del proyecto. Sin esa configuracion:

- la app puede iniciar con valores por defecto de interfaz,
- pero cualquier acceso real a MySQL fallara si `MYSQL_DATABASE` o `MYSQL_USER` no estan definidos,
- y el comportamiento local dejara de ser consistente con el entorno esperado del proyecto.
  En otras palabras: si quieres ejecutar la app de forma local y sin problemas al trabajar con base de datos, debes tener un `.env` valido.

## Preparar la base de datos

Crea la base de datos y aplica el esquema SQL incluido en el repositorio.

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS logistics_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p logistics_db < sql/schema.sql
```

Si cambias el nombre de la base, recuerda usar el mismo valor en `MYSQL_DATABASE` dentro de `.env`.

## Instalar dependencias

La forma recomendada en este proyecto es usar `uv`:

```bash
uv sync
```

Si no usas `uv`, tambien puedes trabajar con `venv`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Ejecutar la aplicacion en local

Comando recomendado:

```bash
uv run python main.py
```

Si quieres preparar e iniciar en una sola linea:

```bash
uv sync && uv run python main.py
```

Si estas usando `venv`, ejecuta:

```bash
python main.py
```

## Resultado esperado

Al iniciar deberias ver la ventana `Sistema de Logistica` sin errores de dependencias. La configuracion de la interfaz se carga desde `.env`, y cualquier funcionalidad que use MySQL tomara sus credenciales desde ese mismo archivo.

## Resumen minimo

Si ya tienes Python, MySQL y `uv` instalados, este es el flujo minimo para correr la app localmente:

```bash
cp .env.example .env
uv sync
uv run python main.py
```
