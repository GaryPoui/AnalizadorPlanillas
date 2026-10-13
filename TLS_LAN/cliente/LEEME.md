# Acceso HTTPS a PriceBot

Este paquete debe provenir del servidor PriceBot o de TI. Contiene la raíz
pública de la CA interna; no contiene claves privadas. Instalarla permite a
Windows confiar en los certificados emitidos por esa CA, por lo que hay que
verificar su procedencia y su huella antes de instalar.

1. Extraer todo el ZIP.
2. Obtener del responsable del servidor la huella SHA-256 por un canal confiable.
3. Clic derecho en `INSTALAR-CLIENTE.bat` → Ejecutar como administrador.
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
Firefox puede requerir ajustar la confianza según su política. Chrome y Edge
usan la confianza de Windows. Los documentos descargados requieren la protección
habitual de cada computadora.
