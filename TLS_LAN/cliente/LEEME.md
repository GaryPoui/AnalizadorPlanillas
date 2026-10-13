# Acceso HTTPS a PriceBot

Este paquete debe provenir del servidor PriceBot o de TI. Contiene la raíz
pública de la CA interna; no contiene claves privadas. Instalarla permite a
Windows confiar en los certificados emitidos por esa CA, por lo que hay que
verificar su procedencia y su huella antes de instalar.

1. Extraer todo el ZIP.
2. Obtener del responsable del servidor la huella SHA-256 por un canal confiable.
3. Para tu usuario de Windows, hacer doble clic en `INSTALAR-SOLO-USUARIO.bat`.
   No pide administrador y solo instala confianza en `Cert:\CurrentUser\Root`.
   Si TI quiere instalar para toda la PC, ejecutar `INSTALAR-CLIENTE.bat` como
   administrador; esa opcion usa `Cert:\LocalMachine\Root`.
4. Pegar esa huella cuando se solicite. Si difiere, la instalación se detiene.
5. Cerrar y abrir el navegador y entrar a `https://192.168.190.146:3000`.
6. Iniciar sesión con tu correo y contraseña confirmados por Administración.

Para comprobar sitio y API sin ignorar certificados, abrir PowerShell en esta
carpeta y ejecutar:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\verificar-conexion.ps1
```

Si cambia la IP del servidor, usar el dato de TI:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\verificar-conexion.ps1 -ServerIP "192.168.190.146"
```

Una alerta de certificado debe resolverse con TI antes de ingresar credenciales.
Si una politica corporativa bloquea instalar raices para el usuario, el script
mostrara el error; TI debe habilitar o distribuir la confianza. No se intenta
eludir esa politica ni se cambia automaticamente al almacen de toda la PC.
Para otros usuarios de la misma PC se debe instalar por separado o usar la
opcion de toda la PC con permisos de TI.
Firefox puede requerir ajustar la confianza según su política. Chrome y Edge
usan la confianza de Windows. Los documentos descargados requieren la protección
habitual de cada computadora.
