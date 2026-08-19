from django.shortcuts import render


def home(request):
    return render(request, 'smartbids/home.html')


def login_view(request):
    return render(request, 'registro/ingreso.html')


def register_view(request):
    return render(request, 'registro/registro.html')

def perfil_view(request):
    return render(request, 'smartbids/perfil.html')

def mensajeria_view(request):
    return render(request, 'smartbids/mensajeria.html')

def handler404_view(request):
    return render(request, 'smartbids/404.html', status=404)