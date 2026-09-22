# CreamLinux

**CreamLinux** es un gestor de escritorio nativo en Qt para Linux que detecta juegos instalados de Steam y Epic/Heroic/Legendary, obtiene los metadatos de sus DLC, agrupa instalaciones duplicadas y gestiona los backends de configuración de DLC compatibles desde una única interfaz.

Está diseñado en torno a un objetivo sencillo: **mostrar claramente la biblioteca real de juegos, detectar todas las rutas de instalación válidas y hacer que la configuración y la recuperación sean predecibles.**

## Características destacadas

- **Detección de múltiples bibliotecas de Steam** mediante `libraryfolders.vdf`, incluidas bibliotecas almacenadas en unidades adicionales.
- Compatible con instalaciones de **Steam nativo** y **Steam Flatpak**.
- Detecta juegos instalados mediante **Heroic** y **Legendary**.
- Las instalaciones duplicadas del mismo juego se muestran como **una única entrada**, conservando todas las rutas detectadas.
- Filtra entradas de Steam que no son juegos, como Proton, Steam Linux Runtime, redistribuibles de Steamworks y Lossless Scaling.
- Los juegos que usan **Easy Anti-Cheat** o **BattlEye** siguen siendo visibles y quedan claramente marcados en lugar de ser excluidos silenciosamente.
- Los juegos sin una DLL de destino compatible también permanecen visibles con un estado explícito.
- Compatible con flujos de trabajo de **CreamAPI**, **SmokeAPI** y **ScreamAPI**.
- Las DLL originales se respaldan antes de ser sustituidas y pueden restaurarse desde la aplicación.
- Los metadatos de DLC se almacenan en caché local y se recuerdan las selecciones de cada juego.
- Interfaz nativa **PyQt6 / PySide6** con imágenes, búsqueda, filtros y diseños compactos adaptables.

## Descargas

Utiliza la página de **GitHub Releases** para descargar las versiones empaquetadas.

| Paquete | Recomendado para |
| --- | --- |
| `CreamLinux-1.0.0-x86_64.AppImage` | La mayoría de distribuciones Linux x86_64 — portable, no requiere instalación |
| `CreamLinux-1.0.0.deb` | Ubuntu, Debian y distribuciones compatibles |
| `CreamLinux-1.0.0.zip` | Instalación universal/desde código fuente en Linux |
| `CreamLinux-1.0.0-SteamOS.zip` | SteamOS / Steam Deck — instalación en espacio de usuario sin modificar el sistema inmutable |

## Compatibilidad

CreamLinux está pensado para funcionar en distribuciones Linux modernas con Python 3 y Qt 6, entre ellas:

- Ubuntu / Debian
- Fedora / distribuciones basadas en RHEL
- Arch Linux
- SteamOS / Steam Deck
- openSUSE
- Alpine Linux
- Otras distribuciones capaces de proporcionar PyQt6 o PySide6

### SteamOS

Para SteamOS, utiliza la **AppImage** o el **ZIP específico para SteamOS**.

El paquete para SteamOS se instala en el directorio personal del usuario y **no** requiere desactivar el sistema de archivos raíz de solo lectura.

## Instalación universal

Extrae `CreamLinux-1.0.0.zip` y ejecuta:

```bash
chmod +x install.sh
./install.sh
```

Para una instalación en todo el sistema:

```bash
sudo ./install.sh --system
```

## Instalación en SteamOS

Extrae `CreamLinux-1.0.0-SteamOS.zip` y ejecuta:

```bash
chmod +x install.sh
./install.sh
```

La instalación permanece dentro del directorio personal del usuario actual, por lo que las actualizaciones del sistema de SteamOS no dependen de modificaciones en el sistema de archivos raíz inmutable.

## AppImage

```bash
chmod +x CreamLinux-1.0.0-x86_64.AppImage
./CreamLinux-1.0.0-x86_64.AppImage
```

## Ejecución portable desde el código fuente

```bash
python3 -m pip install -r requirements.txt
./run-portable.sh
```

## Compilar paquetes

Compilar el paquete Debian:

```bash
./packaging/build-deb.sh
```

Compilar la AppImage x86_64:

```bash
./packaging/build-appimage.sh
```

## Estructura del proyecto

```text
creamlinux.py             Aplicación principal
creamlinux.desktop        Integración con el escritorio
assets/                   Icono de la aplicación y recursos visuales
creamapi/                 Directorio de recursos de CreamAPI
smokeapi/                 Directorio de recursos de SmokeAPI
screamapi/                Directorio de recursos de ScreamAPI
packaging/                Scripts de compilación DEB y AppImage
install.sh                Instalador universal
uninstall.sh              Desinstalador
run-portable.sh           Lanzador portable desde código fuente
requirements.txt          Dependencias de Python
CHANGELOG.md              Historial de versiones
RELEASE_NOTES.md          Notas de la versión pública actual
```

## Desinstalación

Instalación de usuario:

```bash
./uninstall.sh
```

Instalación en todo el sistema:

```bash
sudo ./uninstall.sh --system
```

CreamLinux conserva intencionadamente sus datos de usuario y el directorio de caché en:

```text
~/.local/share/CreamLinux
```

## Notas importantes

CreamLinux modifica archivos DLL y de configuración dentro de las instalaciones de los juegos. Revisa siempre las rutas de juego detectadas antes de aplicar cambios, especialmente en títulos que utilicen software anti-cheat.

Utiliza CreamLinux únicamente con software y contenido que estés autorizado a modificar.

Los componentes de compatibilidad de terceros siguen sujetos a sus respectivos proyectos originales y licencias.
