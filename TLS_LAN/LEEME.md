# Instalación HTTPS de PriceBot en una red privada

Este kit crea una autoridad certificadora interna para PriceBot y un certificado
para `192.168.190.146`, `127.0.0.1`, `::1` y `localhost`. No necesita dominio,
cPanel ni puertos abiertos en Internet. El ZIP inicial contiene scripts, no
certificados ni claves privadas. La generación se hace en la PC servidor.

## Antes de instalar

1. En el servidor, actualizar el repositorio con `git pull`. Deben estar presentes
   las correcciones de HTTPS local incluidas junto a este kit.
2. Si faltan dependencias del proyecto, ejecutar `instalar.bat` en el repositorio.
   Se necesita conexión a Internet inicial para descargar `cryptography` desde
   PyPI en la `.venv`. El funcionamiento HTTPS posterior es local.
3. Cerrar las ventanas del backend y frontend de PriceBot. El instalador rechaza
   puertos 3000/8000 ocupados y no termina procesos automáticamente.
4. Verificar que esta PC tenga la IP `192.168.190.146` y que su interfaz tenga
   perfil de red **Privado**. Reservar la IP en DHCP o configurarla con TI para
   que no cambie. La subred prevista es `192.168.190.0/24`.
5. Tener configurado `PRICEBOT_SESSION_SECRET` en la configuración habitual del
   servidor. No se reemplazan las credenciales, usuarios ni SMTP existentes.
6. Identificar la cuenta Windows que inicia PriceBot, por ejemplo
   `NOMBRE-SERVIDOR\Soporte`. Si se eleva con otra cuenta administradora, indicar
   expresamente la cuenta de operación cuando el instalador la pregunte.

## En la PC servidor

1. Extraer **todo** el ZIP en una carpeta local.
2. Clic derecho en `INSTALAR-SERVIDOR.bat` → **Ejecutar como administrador**.
3. Introducir la ruta del repositorio, por ejemplo
   `C:\Users\Soporte\Documents\AnalizadorPlanillas`, sin comillas.
4. Indicar la cuenta Windows que inicia PriceBot. Se concede a esa cuenta lectura
   de la clave del servidor; la clave de la CA queda restringida a Administradores
   y SYSTEM y además cifrada.
5. Elegir y repetir una **frase secreta de al menos 16 caracteres** para la CA.
   No se verá al escribirla. Guardarla en el gestor corporativo: se necesita para
   renovar. No es la contraseña de los usuarios de PriceBot ni la de Gmail.
6. Esperar el mensaje `INSTALACION TERMINADA`. Copiar la huella SHA-256 que se
   muestra y comunicarla a quienes instalarán las PCs por un canal confiable.
7. Iniciar mediante:

   ```text
   C:\ProgramData\PriceBotTLS\INICIAR-PRICEBOT-SEGURO.bat
   ```

   Este lanzador carga la configuración guardada aunque la consola o el
   Explorador no hayan recibido todavía las nuevas variables de Windows.
8. Abrir `https://127.0.0.1:3000` en el servidor para administrar usuarios.
   No debe mostrar una alerta de certificado. Para usuarios de otras PCs:
   `https://192.168.190.146:3000`.

El instalador conserva la CA si ya existe y se vuelve a ejecutar: pide la frase
original y renueva únicamente el certificado/clave del servidor. Una frase
incorrecta detiene el proceso sin reemplazar la CA. Un fallo durante la
instalación debe corregirse antes de iniciar; no asumir que terminó por el solo
hecho de que aparezcan archivos en la carpeta de salida.

Para cambiar IP, subred o cuenta se puede ejecutar, desde PowerShell elevado:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\instalar-servidor.ps1 -ProjectPath "C:\Users\Soporte\Documents\AnalizadorPlanillas" -ServerIP "192.168.190.146" -AllowedSubnet "192.168.190.0/24" -ServiceAccount "NOMBRE-SERVIDOR\Soporte"
```

## En cada PC autorizada

1. Copiar desde el servidor **solo**:

   ```text
   C:\ProgramData\PriceBotTLS\Clientes-PriceBot.zip
   ```

2. Extraerlo completo. Incluye `PriceBot-CA.cer` público y los instaladores de
   confianza. No incluye la clave de la CA ni la del servidor.
3. Sin permisos de administrador, hacer doble clic en
   `INSTALAR-SOLO-USUARIO.bat`: instala confianza solo para el usuario Windows
   actual. Para toda la PC, TI puede ejecutar `INSTALAR-CLIENTE.bat` como
   administrador. El servidor sigue instalando confianza para toda su PC.
4. Pegar la huella SHA-256 comunicada desde el servidor/TI. Compararla con la
   recibida por un canal confiable, no confiar solo en un texto dentro del ZIP.
   Si no coincide, el script no instala el certificado.
5. Cerrar y abrir Chrome o Edge y entrar a
   `https://192.168.190.146:3000`. Debe abrir sin alertas. Firefox puede requerir
   una configuración adicional de confianza según la política de la empresa.
6. Iniciar sesión con el correo y contraseña individuales y confirmados.
   Instalar la CA no crea usuarios ni concede permisos en PriceBot.

## Verificación sin ignorar certificados

Desde la carpeta del paquete cliente:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\verificar-conexion.ps1
```

En el servidor, la variante local comprueba los accesos del administrador:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\verificar-conexion.ps1 -LocalAdmin
```

La prueba exige HTTPS confiable en el frontend y la API (`/health`). No acepta
certificados inválidos ni omite verificación. Después probar login, confirmación
por correo y una extracción con un archivo no confidencial. Este kit puede
probarse técnicamente antes de entregarse, pero la conectividad real de la LAN
se confirma después de instalar en el servidor y clientes.

## Archivos y custodia

- `C:\ProgramData\PriceBotTLS\ca\ca-key-encrypted.pem`: clave privada de la CA,
  cifrada con la frase. Nunca enviarla a clientes, subirla a Git ni distribuirla
  en un ZIP. Mantener una copia de recuperación cifrada bajo custodia de TI.
- `server-key.pem`: clave privada del servidor. No lleva contraseña porque los
  servicios deben arrancar sin interacción; está protegida con permisos NTFS.
- `server-cert.pem`: certificado del servidor, válido un año.
- `PriceBot-CA.cer`: certificado público de la CA, válido cinco años.
- `certificates.json`: huellas y vencimientos, sin claves privadas.
- `environment-before-install.json`: valores anteriores de las variables de
  entorno modificadas, para que TI pueda revertir la configuración si hace falta.
- `Clientes-PriceBot.zip`: único ZIP generado que debe distribuirse a las PCs.

Renovar 30 días antes del vencimiento: cerrar PriceBot y volver a ejecutar el
instalador del servidor usando la misma frase de la CA. No hace falta instalar
de nuevo la raíz en las PCs mientras se conserve la misma CA. La renovación no
está automatizada en este kit. Antes de vencer la CA, TI debe planificar su
sustitución y distribuir la raíz nueva.

## Límites de la protección

HTTPS protege contraseñas, cookies, documentos y respuestas durante el tránsito.
Los discos, los archivos descargados y los respaldos necesitan sus propios
controles, por ejemplo cifrado de disco y permisos por usuario. El administrador
local depende también de la protección de su sesión de Windows.

Las reglas creadas/restringidas por el instalador permiten TCP 3000/8000 solo
para la IP del servidor y la subred indicada, con perfil Privado. Otras reglas
de firewall más amplias existentes no se eliminan: TI debe revisarlas si las hay.
No se cambia el router ni se habilita acceso por Internet.

Si se compromete la CA, TI debe eliminar **esa raíz específica** de las PCs
(identificarla por la huella en `certificates.json`), sustituir la CA y volver a
instalar la raíz nueva. No borrar todas las autoridades de Windows. Este kit no
configura un servicio de revocación CRL/OCSP. Las claves privadas deben seguir
bajo custodia de TI y no se deben aceptar excepciones de certificado.
