# Iniciar PriceBot en la computadora servidor

Después de actualizar el proyecto con `git pull`, hacer doble clic normal en
`INICIAR-PRICEBOT-SEGURO.bat`, en la carpeta principal del repositorio.
No se necesita ejecutar como administrador para el inicio habitual.

El archivo carga la configuración existente de
`C:\ProgramData\PriceBotTLS\launch-config.json` y usa los certificados instalados
en esa computadora. Mantener abiertas las ventanas del frontend y backend.
No iniciar también `start.bat`: este es el acceso recomendado para el servidor HTTPS.

- Administración desde el servidor: `https://127.0.0.1:3000/`.
- Usuarios en la red de la empresa: `https://192.168.190.146:3000/`.

El lanzador instalado en `C:\ProgramData\PriceBotTLS` sigue funcionando.
El del repositorio usa la versión actualizada de `TLS_LAN/iniciar-seguro.ps1`.

## Si no inicia

La ventana conserva el mensaje del error. Enviarlo a Soporte sin contraseñas ni
documentos confidenciales. El lanzador no abre puertos, no instala dependencias,
no cambia permisos y no crea ni renueva certificados durante el inicio.

- Si nunca se preparó esta PC como servidor: instalar dependencias con
  `instalar.bat` y realizar la instalación HTTPS con
  `TLS_LAN\INSTALAR-SERVIDOR.bat` como administrador, siguiendo `TLS_LAN/LEEME.md`.
- Si ya estaba funcionando: no reinstalar ni generar otra CA ante un error.
  Soporte debe revisar la configuración guardada, la ruta del proyecto y el acceso
  a los certificados. La ruta guardada debe corresponder al repo de esa PC.
- Los certificados privados y las contraseñas no se descargan del repositorio.
  Se conservan únicamente en el servidor con sus permisos existentes.

## Comprobación sin iniciar servicios

Desde PowerShell en la carpeta del repo:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\TLS_LAN\iniciar-seguro.ps1 -ValidateOnly
```

Esta comprobación valida rutas y opciones básicas. El inicio habitual realiza
las comprobaciones de TLS y de los servicios mediante `start.ps1`.
