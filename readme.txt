Pasos para correr el programa:

1. Instala Python 3, pip y venv si no están instalados:
    sudo apt update
    sudo apt install python3 python3-pip python3-venv

2. Crea el entorno virtual dentro de la carpeta del proyecto:
    cd ~/Escritorio/SmartBids
    python3 -m venv venv

3. Activa el entorno virtual:
    source venv/bin/activate

4. Instala todas las dependencias del proyecto (incluyendo Django):
    pip install -r requirements.txt

5. Inicia el servidor de Django desde la carpeta del proyecto:
    python manage.py runserver

6. Abre el navegador en:
    http://127.0.0.1:8000

Notas:
- No uses "sudo pip install" para este proyecto.
- Si el comando `python` no funciona o te indica módulos no encontrados, asegúrate de haber activado el entorno virtual en el paso 3 (`source venv/bin/activate`).
- Si instalas o actualizas nuevas librerías en tu proyecto, guarda los cambios en el archivo ejecutando:
    pip freeze > requirements.txt