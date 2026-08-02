

# codex-hotswap

[![CI](https://github.com/tanayyo1/codex-hotswap/actions/workflows/ci.yml/badge.svg)](https://github.com/tanayyo1/codex-hotswap/actions/workflows/ci.yml)
[![version](https://img.shields.io/badge/version-0.3.1-blue.svg)](https://github.com/tanayyo1/codex-hotswap)

`codex-hotswap` cambia automáticamente a otra cuenta conectada cuando la actual alcanza los límites de uso, manteniendo el historial normal del repositorio y `/resume`, incluso a través de múltiples sesiones de Codex envueltas.

## Qué hace esto

Si usas Codex intensamente en la terminal, eventualmente te encontrarás con esto:

- estás trabajando en un repositorio
- tu cuenta actual de Codex se queda sin uso
- tu trabajo se detiene
- cambias manualmente de cuenta e intentas recuperar la sesión

`codex-hotswap` elimina esa gestión manual de cuentas.

Inicias sesión en múltiples cuentas de Codex una vez, y luego sigues usando el `codex` normal.
Cuando una cuenta alcanza sus límites, `codex-hotswap` cambia a la siguiente y reanuda la sesión.

## Compatibilidad de plataformas

- Linux: soportado
- macOS: se espera que funcione, pero con menos pruebas en campo
- Windows nativo: aún no soportado
- Los usuarios de Windows deben usar WSL por ahora

## Comienza aquí

Si solo quieres la ruta de configuración más corta, haz esto.

### 1. Instala `pipx` si no lo tienes

En Ubuntu o Debian:

```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath
```

Reinicia tu shell después de `pipx ensurepath`.

### 2. Instala `codex-hotswap`

```bash
pipx install git+https://github.com/tanayyo1/codex-hotswap.git
```

### 3. Configura 4 cuentas

```bash
codex-hotswap setup --force --count 4 --prefix acc --login --install-shim
```

Qué hace esto:

- crea `acc1`, `acc2`, `acc3`, `acc4`
- te pide iniciar sesión en cada cuenta
- instala un pequeño shim para que el `codex` normal se ejecute a través de `codex-hotswap`

El inicio de sesión de cada cuenta sigue siendo interactivo. El comando te guía a través de ellas una por una.

### 4. Elige la cuenta de inicio

```bash
codex-hotswap use acc1
```

### 5. Usa Codex normalmente

```bash
cd ~/your-repo
codex
```

Ese es el flujo de trabajo diario normal después de la configuración.

Puedes abrir múltiples sesiones de `codex` envueltas en diferentes repositorios o pestañas. Cada lanzamiento envuelto ahora obtiene su propia capa de ejecución privada, mientras sigue compartiendo el almacén normal de sesiones de Codex.

### ¿Quieres volver a usar el Codex normal temporalmente?

Desactiva el hotswap:

```bash
codex-hotswap disable
hash -r
```

`disable` también prepara tu autenticación compartida `~/.codex` desde el objetivo actual para que el `codex` básico funcione de inmediato.

Vuelve a activar el hotswap:

```bash
codex-hotswap enable
hash -r
```

Usa esto si deseas trabajar en muchas pestañas de Codex básico por un tiempo y no necesitas la conmutación automática de cuentas en esas sesiones.

## Qué usas todos los días

La mayoría de los usuarios solo necesitan:

```bash
cd ~/your-repo
codex
```

Si la cuenta actual alcanza sus límites, `codex-hotswap` debería rotar automáticamente a la siguiente cuenta.

## Cómo funciona

`codex-hotswap` utiliza tres capas de almacenamiento:

- almacén compartido de Codex: `~/.codex`
- bóvedas de autenticación por cuenta: `~/.codex-acc1`, `~/.codex-acc2`, y así sucesivamente
- capas de ejecución por sesión: creadas automáticamente bajo `~/.local/state/codex-hotswap/runtime`

Qué permanece compartido:

- historial del repositorio
- `/resume` normal
- el almacén de sesiones de Codex

Qué permanece separado:

- el inicio de sesión de cada cuenta
- el `auth.json` privado de cada sesión activa envuelta

Cuando inicias `codex` envuelto:

1. `codex-hotswap` crea un `CODEX_HOME` de ejecución temporal
2. vincula ese directorio de ejecución con el almacén compartido de Codex
3. copia la autenticación de la cuenta seleccionada en ese directorio de ejecución

Cuando se alcanza un límite:

1. la cuenta actual se marca como agotada
2. la autenticación de la siguiente cuenta reemplaza solo el `auth.json` privado de la capa de ejecución
3. se intenta ejecutar `codex resume --last`

Qué debe permanecer igual:

- directorio del repositorio
- comportamiento normal de `/resume`
- flujo general de la sesión

Qué debe cambiar:

- la cuenta conectada

Por qué esto es importante:

- las sesiones envueltas ahora pueden ejecutarse en paralelo
- que una sesión envuelta cambie de cuenta ya no modifica la autenticación subyacente de otra sesión envuelta

## Ejemplo

Uso real de ejemplo:

1. estás en `~/tonr`
2. ejecutas `codex`
3. Codex está usando `acc1`
4. `acc1` alcanza un límite de uso
5. `codex-hotswap` cambia a `acc2`
6. Codex continúa en el mismo repositorio

La señal importante es:

- mismo repositorio
- mismo flujo general de sesión/hilo
- línea `Account:` diferente

## Comandos importantes

```bash
codex-hotswap doctor
codex-hotswap status
codex-hotswap current
codex-hotswap use <target>
codex-hotswap next
codex-hotswap login <target>
codex-hotswap enable
codex-hotswap disable
codex-hotswap reset
codex-hotswap reset <target>
codex-hotswap install-shim
codex-hotswap uninstall-shim
```

Qué significan:

- `codex-hotswap doctor` = verifica si la configuración es correcta
- `codex-hotswap status` = muestra los objetivos y el estado de agotamiento
- `codex-hotswap use acc1` = elige la cuenta de inicio
- `codex-hotswap login acc1` = inicia sesión en una cuenta
- `codex-hotswap enable` = activa el hotswap para el `codex` normal
- `codex-hotswap disable` = desactiva el hotswap, prepara la autenticación compartida y usa el `codex` normal
- `codex-hotswap reset` = borra los marcadores de agotamiento

## Si quieres usar cuentas con nombre

En lugar de `acc1`, `acc2`, `acc3`, `acc4`, puedes usar nombres:

```bash
codex-hotswap setup --force --accounts main,work,backup,extra --login --install-shim
```

## Si quieres autenticación por dispositivo

Para inicio de sesión headless o remoto:

```bash
codex-hotswap setup --force --count 4 --prefix acc --login --device-auth --install-shim
```

## Solución de problemas

### Verifica si todo está configurado correctamente

```bash
codex-hotswap doctor
```

Si ves:

```bash
doctor status: ok
```

tu configuración está sana.

### `pipx: command not found`

En Ubuntu o Debian:

```bash
sudo apt update
sudo apt install -y pipx
pipx ensurepath
```

Reinicia tu shell y luego vuelve a instalar.

### `codex-hotswap: Config file not found`

Crea la configuración primero:

```bash
codex-hotswap setup --force --count 4 --prefix acc
```

### No está cambiando automáticamente

Verifica:

- que estás usando `codex` a través del shim o `codex-hot`
- que cada cuenta inició sesión correctamente
- el orden de los objetivos en `codex-hotswap status`
- que no todas las cuentas estén ya agotadas

### `codex-hotswap: no non-exhausted targets remain`

Esto significa que todos los objetivos configurados están marcados como agotados actualmente.

Verifica:

```bash
codex-hotswap status
```

Borra todos los marcadores de agotamiento:

```bash
codex-hotswap reset
```

O comienza desde una cuenta específica:

```bash
codex-hotswap use acc3
codex
```

### Quiero usar el Codex básico sin envoltorio por un tiempo

Desactiva el hotswap:

```bash
codex-hotswap disable
hash -r
```

Vuelve a activarlo más tarde:

```bash
codex-hotswap enable
hash -r
```

Solo necesitas esto si deseas Codex puro sin conmutación automática. El uso de sesiones múltiples envueltas ya está soportado.

### `/resume` se ve incorrecto

Asegúrate de iniciar a través de `codex-hotswap`, no a través de una configuración de Codex no gestionada por separado con otro `CODEX_HOME`.

Usa:

```bash
cd ~/your-repo
codex
```

## Garantías y limitaciones

Lo que hace bien:

- mantiene el historial normal del repositorio/sesión en un almacén compartido de Codex
- preserva el comportamiento de `/resume` por repositorio
- aísla los inicios de sesión de múltiples cuentas
- intercambia la autenticación de la cuenta sin cambiar tu espacio de trabajo
- soporta múltiples sesiones envueltas al dar a cada una una capa de ejecución privada

Lo que no garantiza:

- detección perfecta de cada futuro banner de fallo de Codex
- un medidor de uso real upstream de Codex
- un comportamiento de reanudación perfecto si Codex cambia sus componentes internos
- compatibilidad perfecta si Codex cambia significativamente su estructura de almacenamiento

## Preguntas frecuentes (FAQ)

### ¿Necesito seguir usando `codex-hot`?

No. Si instalas el shim, puedes simplemente usar el `codex` normal.

### ¿Se mantendrán separadas las chats del repositorio?

Sí. El almacén compartido de Codex conserva el historial normal de Codex, por lo que `/resume` debería seguir organizado por repositorio.

### ¿Inicia sesión automáticamente en todas las cuentas?

No. Sigues iniciando sesión en cada cuenta una vez. Después de eso, el cambio es automático.

### ¿Soporta Windows nativo?

No. Usa WSL por ahora.

### ¿Cómo uso el Codex básico en múltiples pestañas?

Ahora puedes mantener el hotswap activado. Las sesiones de `codex` envueltas usan capas de ejecución privadas, por lo que se admiten múltiples pestañas envueltas.

Si deseas Codex puro sin envoltorio, desactiva el hotswap primero:

```bash
codex-hotswap disable
hash -r
```

Luego abre tantas sesiones de `codex` normales como quieras.

Vuelve a activar el hotswap más tarde:

```bash
codex-hotswap enable
hash -r
```

## Desarrollo

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest
python -m build
```
