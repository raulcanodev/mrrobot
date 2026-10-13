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
├── cli/                 # Capa fina de terminal (Typer + Rich + questionary)
│   ├── app.py           #   comandos: run, report, tools, scope, history, doctor
│   ├── menu.py          #   menú interactivo (selector con flechas)
│   ├── actions.py       #   lógica compartida entre comandos y menú
│   ├── report_wizard.py #   asistente interactivo de informes
│   ├── style.py         #   estilo visual compartido del selector
│   └── banner.py
├── core/                # Núcleo reutilizable (independiente de la UI)
│   ├── models.py        #   ToolMeta, RunResult, Scope, Mode, TargetKind…
│   ├── config.py        #   scope / autorización
│   ├── registry.py      #   registro central de herramientas
│   ├── runner.py        #   ejecución de procesos externos
│   ├── installer.py     #   instalación automática (brew/pipx)
│   ├── updates.py       #   versión instalada vs. última release
│   ├── report.py        #   agregación de resultados en un informe
│   └── storage.py       #   historial en SQLite
└── tools/               # Un adaptador por herramienta
    ├── osint/            # sherlock, theharvester, whois
    ├── web/               # subfinder, amass, crtsh, wayback
    └── network/           # nmap, internetdb, certinfo
```

**Modos de ejecución**

| Modo | Qué hace | Autorización |
|------|----------|--------------|
| `passive` | Consulta fuentes públicas, no toca el objetivo | Permitido por defecto |
| `active`  | Envía tráfico al objetivo | Requiere scope autorizado |

**Herramientas integradas** (10 ahora mismo, sin contar lo que tú añadas):

| Herramienta | Categoría | Modo | Instalación |
|---|---|---|---|
| `sherlock` | osint | passive | externa (brew/pipx) — usuario en redes sociales |
| `theharvester` | osint | passive | externa (brew) — emails/hosts vía fuentes OSINT |
| `whois` | osint | passive | **integrada** — registrante, fechas, DNS autoritativo |
| `subfinder` | web | passive | externa (brew) — subdominios |
| `amass` | web | passive | externa (brew), siempre en `-passive` |
| `crtsh` | web | passive | **integrada** — subdominios vía Certificate Transparency |
| `wayback` | web | passive | **integrada** — URLs históricas (Internet Archive) |
| `nmap` | network | active | externa (brew) — puertos y servicios |
| `internetdb` | network | passive | **integrada** — snapshot de Shodan (sin API key) |
| `certinfo` | network | active | **integrada** — certificado TLS, SANs, cifrado |

Las "integradas" no requieren instalar nada: están escritas en Python dentro
de mrrobot y funcionan desde el primer `mrrobot doctor`.

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

Las herramientas externas se instalan aparte, con un solo comando cada una:

```bash
mrrobot tools install sherlock     # te muestra el comando (brew/pipx) y pide confirmación
```

## Uso

### Menú interactivo

```bash
mrrobot
```

Ejecutado sin nada más, abre un **menú con selector de flechas** (↑/↓ + Enter,
sin escribir comandos): ejecutar una herramienta, generar un informe, ver el
estado de las herramientas, instalar las que falten, gestionar el scope o ver
el historial. `mrrobot menu` hace lo mismo de forma explícita.

Esto **no sustituye** la vía por comando: todo lo del menú tiene su comando
directo, para scripts, automatización o si ya sabes lo que quieres ejecutar.

### Comandos directos

```bash
mrrobot doctor                     # chequeo + avisos de actualización
mrrobot tools --online             # herramientas integradas y versiones
mrrobot tools install <nombre>     # instala una herramienta externa
mrrobot tools install --all        # instala de una vez todas las que falten
mrrobot scope init                 # crea tu plantilla de alcance
mrrobot run sherlock raulcanodev   # OSINT pasivo, una sola herramienta
mrrobot run subfinder ejemplo.com  # subdominios (pasivo)
mrrobot run nmap 192.168.1.10      # red (activo → exige scope)
mrrobot report                     # asistente interactivo: informe completo
mrrobot history                    # ejecuciones anteriores
```

### Informes completos (`mrrobot report`)

```
mrrobot report ejemplo.com
```

Te pregunta si quieres generar el informe, confirma el tipo de objetivo
(dominio/usuario/IP), y te deja elegir con casillas (espacio para marcar,
Enter para continuar) qué herramientas aplicables ejecutar. Al terminar:

- imprime un resumen en consola (cada herramienta en su panel, con las
  primeras líneas de salida);
- te pregunta si quieres guardar el **informe completo** en un `.txt` bajo
  `~/.local/share/mrrobot/reports/`;
- registra cada ejecución en el historial (`mrrobot history`).

Las herramientas ACTIVAS fuera de tu scope autorizado no se bloquean con un
error: simplemente quedan marcadas como "bloqueada" dentro del informe.

## Añadir una herramienta

**Externa** (lanza un binario):
1. Crea `tools/<categoria>/<nombre>.py` heredando de `ToolAdapter`.
2. Declara su `ToolMeta` (binario, repo, modo, `target_kind`, `install_cmds`).
3. Sobrescribe `build_args()`.

**Integrada** (sin binario, p. ej. una API pública):
1. Mismo `ToolMeta`, con `builtin=True` y sin `binary`.
2. Sobrescribe `execute()` directamente y construye el resultado con
   `make_result()` (ver `tools/web/crtsh.py` como ejemplo corto).

En ambos casos, regístrala en `core/registry.py`. El resto (autorización,
historial, informes, avisos de update) ya es común.

## Notas de licencias

Cada herramienta mantiene su propia licencia. `mrrobot` las ejecuta como
procesos externos (adaptadores); no copia ni redistribuye su código.
