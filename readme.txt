====================================================================
GUÍA DE INSTALACIÓN Y EJECUCIÓN (UBUNTU / MAC / WINDOWS)
====================================================================

--------------------------------------------------------------------
1. UBUNTU / DEBIAN
--------------------------------------------------------------------
# 1. Actualizar repositorios e instalar Python 3, pip y venv
sudo apt update
sudo apt install python3 python3-pip python3-venv

# 2. Navegar a la carpeta del proyecto
cd ~/Escritorio/SmartBids

# 3. Crear el entorno virtual
python3 -m venv venv

# 4. Activar el entorno virtual
source venv/bin/activate

# 5. Actualizar pip a la última versión
python3 -m pip install --upgrade pip

# 6. Instalar dependencias del proyecto
pip install -r requirements.txt

# 7. Iniciar el servidor de desarrollo de Django
python manage.py runserver --insecure

# 8. Abrir el proyecto en el navegador web:
http://127.0.0.1:8000


--------------------------------------------------------------------
2. macOS (Intel & Apple Silicon M1/M2/M3)
--------------------------------------------------------------------
# 1. Instalar Python moderno (Python 3.10 o superior) con Homebrew
brew install python

# 2. Navegar a la carpeta del proyecto
cd ~/Desktop/SmartBids   # Si tu Mac está en español usa: cd ~/Escritorio/SmartBids

# 3. Eliminar entorno anterior si dio problemas de versión (Opcional)
rm -rf venv

# 4. Crear el entorno virtual usando el Python actualizado de Homebrew
# En Macs Apple Silicon (M1/M2/M3):
/opt/homebrew/bin/python3 -m venv venv
# En Macs con procesador Intel (o si el comando anterior falla):
python3 -m venv venv

# 5. Activar el entorno virtual
source venv/bin/activate

# 6. Actualizar pip dentro del entorno virtual
python3 -m pip install --upgrade pip

# 7. Instalar dependencias del proyecto
pip install -r requirements.txt

# 8. Iniciar el servidor de desarrollo de Django
python manage.py runserver --insecure

# 9. Abrir el proyecto en el navegador web:
http://127.0.0.1:8000


--------------------------------------------------------------------
3. WINDOWS (PowerShell / Command Prompt)
--------------------------------------------------------------------
# 1. Instalar Python
# Descargar el instalador desde https://www.python.org/downloads/
# ¡IMPORTANTE! Marcar la casilla "Add Python to PATH" antes de instalar.

# 2. Navegar a la carpeta del proyecto
cd %USERPROFILE%\Desktop\SmartBids

# 3. Crear el entorno virtual
python -m venv venv

# 4. Activar el entorno virtual
# Si usas PowerShell:
.\venv\Scripts\Activate.ps1
# Si usas Command Prompt (CMD):
.\venv\Scripts\activate.bat

# 5. Actualizar pip dentro del entorno virtual
python -m pip install --upgrade pip

# 6. Instalar dependencias del proyecto
pip install -r requirements.txt

# 7. Iniciar el servidor de desarrollo de Django
python manage.py runserver --insecure

# 8. Abrir el proyecto en el navegador web:
http://127.0.0.1:8000


====================================================================
ACTUALIZACIÓN Y SINCRONIZACIÓN DE RAMAS (GIT)
====================================================================
# 1. Configurar tu identidad en Git (ejecutar una sola vez por equipo):
git config --global user.name "Tu Nombre"
git config --global user.email "tu-correo@example.com"

# 2. Descargar las ramas nuevas y referencias del servidor remoto (GitHub):
git fetch origin

# 3. Ver todas las ramas disponibles (locales y remotas):
git branch -a

# 4. Cambiarte a la rama que necesitas actualizar o revisar:
git switch nombre-de-la-rama
# (O alternativamente: git checkout nombre-de-la-rama)

# 5. Descargar los últimos cambios a tu rama local:
git pull origin nombre-de-la-rama

# NOTA SI TIENES CAMBIOS LOCALES SIN GUARDAR:
# Si Git no te permite cambiar de rama por modificaciones pendientes,
# guárdalas temporalmente en el baúl:
git stash
# Luego cámbiate de rama o haz pull, y recupera tus cambios con:
git stash pop


====================================================================
NOTAS GENERALES Y SOLUCIÓN DE PROBLEMAS
====================================================================
- ERROR "No matching distribution found for cffi/asgiref":
  Este error ocurre si intentas instalar el proyecto usando Python 3.9 o inferior.
  Asegúrate de haber creado el entorno virtual con Python 3.10 o superior.

- ERROR DE EJECUCIÓN EN WINDOWS (PowerShell):
  Si al ejecutar '.\venv\Scripts\Activate.ps1' sale un error de seguridad, 
  ejecuta primero este comando en PowerShell:
  Set-ExecutionPolicy Unrestricted -Scope Process

- NUNCA USAR 'sudo pip install':
  No uses 'sudo' para instalar librerías de Python. Siempre activa el entorno 
  virtual primero y luego usa 'pip install'.

- GUARDAR NUEVAS LIBRERÍAS:
  Si instalas o actualizas librerías en el proyecto, guarda los cambios ejecutando:
  pip freeze > requirements.txt