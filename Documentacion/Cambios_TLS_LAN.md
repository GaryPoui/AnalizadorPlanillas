# Cambios de acceso HTTPS y certificados de PriceBot

Actualización del 13 de octubre de 2026 para la LAN `192.168.190.0/24`.
Servidor de referencia: `192.168.190.146`. El procedimiento completo está en
`Manual_de_Administracion_y_Operacion_PriceBot.docx` y `TLS_LAN/LEEME.md`.

## Archivos para distribuir

- [Archivo automático para usuarios](CONFIGURAR-PRICEBOT-LAN.bat): descargar el
  archivo original y ejecutar con doble clic normal, sin elevar permisos.
- [ZIP cliente completo](Clientes-PriceBot-SinAdmin.zip): extraer y ejecutar
  `CONFIGURAR-PRICEBOT-LAN.bat`. Incluye únicamente la CA pública y herramientas
  de cliente, no claves privadas. Corresponde a la CA e IP de referencia actuales.

## Cambios implementados

- El lanzador exige HTTPS para la LAN y cookies seguras. Sin certificado y clave,
  limita ambos servicios a localhost; `start.ps1` rechaza un enlace de red sin TLS.
- El certificado interno cubre la IP del servidor y los accesos locales
  `127.0.0.1`, `localhost` y `::1`. La CA privada se genera cifrada en el servidor
  y se protege con permisos NTFS; solo se distribuye su certificado público.
- El frontend usa el protocolo de su página para llamar a la API. Los orígenes
  y la CSP admiten los accesos HTTPS locales y de LAN previstos.
- El arranque comprueba que los servicios ya presentes respondan mediante TLS
  confiable, evitando reutilizar un proceso HTTP anterior como si fuera seguro.
- El cliente puede instalar confianza en `CurrentUser` sin elevar permisos.
  Para `LocalMachine` se conserva el requisito de administrador Windows.
- `CONFIGURAR-PRICEBOT-LAN.bat` incorpora la CA pública y su huella verificada.
  Hace la comprobación, instala en el usuario actual, prueba sitio y API con
  validación TLS normal y abre el navegador. No omite certificados ni autentica
  al usuario automáticamente dentro de PriceBot.
- `PREPARAR-CLIENTES.bat` genera el archivo y el ZIP para clientes leyendo la
  configuración pública existente. No renueva certificados, no lee claves
  privadas y no modifica procesos ni firewall del servidor.
- El generador del paquete usa una lista explícita de archivos. El ZIP cliente
  admite la CA pública y el script generado; excluye claves PEM, PFX y privadas.

## Responsabilidades

TI instala o renueva el servidor con permisos Windows de administrador, custodia
la frase de la CA y mantiene IP, firewall, respaldos y fechas de vencimiento.
Administración opera usuarios desde `https://127.0.0.1:3000` en el servidor;
ese rol local no equivale a la elevación de Windows. Los usuarios ejecutan el
archivo de acceso con su propia sesión Windows y luego ingresan por correo y
contraseña confirmados a `https://192.168.190.146:3000`.

Una CA o IP nueva requiere preparar y distribuir un script nuevo. Renovar solo
el certificado del servidor conservando la misma CA no requiere reinstalar la
raíz en los clientes. El kit usa renovación manual; no existe una tarea de
renovación automática ni revocación CRL/OCSP configurada.

## Verificaciones

Las pruebas cubren clave de CA cifrada, SAN y usos del certificado, renovación
con la misma CA, contraseña incorrecta sin reemplazo, rechazo de subred pública,
huella incorrecta y comprobación de ambos almacenes Windows sin importar raíces
de prueba. Se levantan frontend y API temporales por HTTPS y se comprueba el
rechazo de CA no confiable, nombre incorrecto y HTTP. El archivo independiente
se ejecuta en modo `--comprobar`, sin instalar confianza ni abrir el navegador,
y debe rechazar una huella incorporada alterada.

En esta edición pasaron 61 pruebas del proyecto y se repitieron las 7 del kit
después del ajuste del almacén Windows. El instalador independiente se ejecutó
sin elevación en una PC cliente con la CA de referencia y comprobó correctamente
el sitio y la API del servidor real por HTTPS. Se usa X509Store de Windows para
no depender de la carga automática del proveedor Cert de PowerShell.

La comprobación real de cada PC debe completarse con login y una extracción
no confidencial. HTTPS protege el tránsito; discos, descargas y respaldos
requieren cifrado y permisos propios.
