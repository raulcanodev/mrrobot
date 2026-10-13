# mrrobot

Orquestador modular de **OSINT y pentesting autorizado** para terminal.

`mrrobot` no reimplementa herramientas de seguridad: las **orquesta**. Ejecuta
herramientas open source reputadas (Sherlock, subfinder, Nmap…) a través de
adaptadores, normaliza sus resultados, guarda un historial y te avisa cuando
hay actualizaciones disponibles. Pensado para crecer: hoy es una CLI limpia;
mañana, sin tocar el núcleo, puede tener una interfaz (TUI/web).

> ⚖️ **Uso responsable.** Está diseñado para reconocimiento pasivo sobre
> fuentes públicas y para pruebas activas **solo** contra objetivos propios o
> con autorización explícita (laboratorios, bug bounty en alcance, clientes con
> permiso por escrito). Las acciones activas están bloqueadas salvo que el
> objetivo esté en tu alcance declarado. Tú eres responsable del uso que hagas.

## Arquitectura

```
src/mrrobot/
├── cli/            # Capa fina de terminal (Typer + Rich)
│   ├── app.py      #   comandos: run, tools, scope, history, doctor
│   └── banner.py
├── core/           # Núcleo reutilizable (independiente de la UI)
│   ├── models.py   #   ToolMeta, RunResult, Scope, Mode…
│   ├── config.py   #   scope / autorización
│   ├── registry.py #   registro central de herramientas
│   ├── runner.py   #   ejecución de procesos externos
│   ├── updates.py  #   versión instalada vs. última release
│   └── storage.py  #   historial en SQLite
├── tools/          # Un adaptador por herramienta
│   ├── osint/sherlock.py
│   ├── web/subfinder.py
│   └── network/nmap.py
└── reports/
```

**Modos de ejecución**

| Modo | Qué hace | Autorización |
|------|----------|--------------|
| `passive` | Consulta fuentes públicas, no toca el objetivo | Permitido por defecto |
| `active`  | Envía tráfico al objetivo | Requiere scope autorizado |

## Instalación

Copia y pega esto en tu terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/raulcanodev/mrrobot/main/install.sh | bash
```

Instala `mrrobot` en su propio entorno virtual bajo `~/.local/share/mrrobot`
y enlaza el comando en `~/.local/bin/mrrobot`, sin tocar tu Python de sistema.
Requiere Python 3.11+ (p. ej. `brew install python`).

Luego ejecuta:

```bash
mrrobot doctor
```

Para actualizar, vuelve a ejecutar el mismo comando de instalación. Para
desinstalar:

```bash
rm ~/.local/bin/mrrobot
rm -rf ~/.local/share/mrrobot
```

### Instalación para desarrollo

```bash
git clone https://github.com/raulcanodev/mrrobot.git
cd mrrobot
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Las herramientas externas que orquesta se instalan aparte (mrrobot te dice cómo):

```bash
pipx install sherlock-project      # OSINT de usuarios
brew install subfinder nmap        # subdominios / red
```

## Uso

```bash
mrrobot doctor                     # chequeo + avisos de actualización
mrrobot tools --online             # herramientas integradas y versiones
mrrobot scope init                 # crea tu plantilla de alcance
mrrobot run sherlock raulcanodev   # OSINT pasivo
mrrobot run subfinder ejemplo.com  # subdominios (pasivo)
mrrobot run nmap 192.168.1.10      # red (activo → exige scope)
mrrobot history                    # ejecuciones anteriores
```

## Añadir una herramienta

1. Crea `tools/<categoria>/<nombre>.py` heredando de `ToolAdapter`.
2. Declara su `ToolMeta` (binario, repo, modo, versión, pista de instalación).
3. Regístralo en `core/registry.py`.

El resto (autorización, ejecución, historial, avisos de update) ya es común.

## Notas de licencias

Cada herramienta mantiene su propia licencia. `mrrobot` las ejecuta como
procesos externos (adaptadores); no copia ni redistribuye su código.
