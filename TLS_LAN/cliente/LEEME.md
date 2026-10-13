# Acceso HTTPS a PriceBot

Este paquete debe provenir del servidor PriceBot o de TI. Contiene la raíz
pública de la CA interna; no contiene claves privadas. Instalarla permite a
Windows confiar en los certificados emitidos por esa CA, por lo que hay que
verificar su procedencia y su huella antes de instalar.

## Opción recomendada para cada usuario

Cuando TI entregue `CONFIGURAR-PRICEBOT-LAN.bat`, basta hacer doble clic con el
usuario de Windows que utilizará PriceBot. Ese archivo funciona por sí solo:
lleva la CA pública y la huella verificada por TI. Comprueba ambas, instala
confianza solo para el usuario actual, prueba el sitio y la API mediante HTTPS
válido y abre el navegador. No pide pegar huellas ni contraseña de administrador.
Windows puede mostrar un aviso de ejecución o de confianza según su política.
Recibirlo únicamente del responsable o del repositorio corporativo verificado.

Si aparece un error de red después de instalar confianza, comprobar que la PC
esté en la LAN y que el servidor siga funcionando. Cerrar y abrir el navegador;
si se usa el navegador integrado de Codex y conserva una advertencia anterior,
reiniciar Codex. Después ingresar con el correo y contraseña confirmados.

## Instalación manual o para toda la PC

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
