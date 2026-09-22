from django.shortcuts import render
from django.core.paginator import Paginator
from .models.procurement import Licitacion


def mis_licitaciones_view(request):
    licitaciones_list = Licitacion.objects.select_related('lic_codigo_ucom').all().order_by('-lic_fecha_public')
    
    # 2. Total general para las métricas
    total_licitaciones = Licitacion.objects.count()
    
    paginator = Paginator(licitaciones_list, 20)
    page_number = request.GET.get('page')
    licitaciones = paginator.get_page(page_number)

    context = {
        'licitaciones': licitaciones,
        'total_licitaciones': total_licitaciones,
    }
    
    return render(request, 'smartbids/Mis_licitaciones.html', context)
