# Sistema de Logistica

Aplicacion de escritorio en Python con Tkinter para la base del sistema de logistica del proyecto. El arranque carga configuracion desde un archivo `.env`, prepara la UI y deja la conexion a MySQL en modo diferido hasta que alguna funcionalidad de datos la necesite.

## Pre requisitos

- Python 3.12 o superior
- `uv` instalado para sincronizar dependencias y ejecutar el proyecto
- MySQL disponible localmente o en una instancia accesible desde tu equipo
- Una instalacion de Python con soporte para Tkinter

## Configuracion del entorno

Este proyecto incluye un archivo `.env.example` con las variables necesarias para la app.

1. Crea tu archivo local de entorno:

```bash
cp .env.example .env
```

2. Ajusta al menos estas variables segun tu ambiente:

- `MYSQL_HOST`: host del servidor MySQL
- `MYSQL_PORT`: puerto del servidor MySQL
- `MYSQL_DATABASE`: nombre de la base de datos
- `MYSQL_USER`: usuario con permisos sobre la base
- `MYSQL_PASSWORD`: password del usuario

Las variables `APP_TITLE`, `APP_WIDTH` y `APP_HEIGHT` controlan el titulo y el tamano inicial de la ventana.

## Por que `.env` es importante

La aplicacion carga automaticamente el archivo `.env` desde la raiz del proyecto. Sin esa configuracion:

- la app puede iniciar con valores por defecto de interfaz,
- pero cualquier acceso real a MySQL fallara si `MYSQL_DATABASE` o `MYSQL_USER` no estan definidos,
- y el comportamiento local dejara de ser consistente con el entorno esperado del proyecto.

En otras palabras: `.env` no es opcional si quieres trabajar con la app correctamente conectada a la base de datos.

## Preparar la base de datos

Crea la base de datos y aplica el esquema SQL incluido en el repositorio.

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS logistics_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p logistics_db < sql/schema.sql
```

Si cambias el nombre de la base, recuerda usar el mismo valor en `MYSQL_DATABASE` dentro de `.env`.

## Ejecutar el proyecto en local

Sincroniza dependencias y ejecuta la app con:

```bash
uv sync
uv run python main.py
```

Si quieres hacerlo en una sola linea:

```bash
uv sync && uv run python main.py
```

## Resultado esperado

Al iniciar, deberias ver la ventana `Sistema de Logistica` sin errores de dependencias. Si mas adelante agregas operaciones que consulten MySQL, la conexion usara los valores definidos en tu `.env`.
