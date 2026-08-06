from django.shortcuts import render


def home(request):
    return render(request, 'smartbids/home.html')


def login_view(request):
    return render(request, 'registro/ingreso.html')


def register_view(request):
    return render(request, 'registro/registro.html')

def perfil_view(request):
    return render(request, 'smartbids/perfil.html')