"""Validated inputs and inference for the saved tender classifier."""
import logging
import math
from functools import lru_cache
from pathlib import Path

from django import forms
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)
FEATURES = {
    'Valor Total Ofertado': 'valor_total_ofertado',
    'MesPublicacion': 'mes_publicacion',
    'CodigoProductoONU': 'codigo_producto_onu',
    'CantidadReclamos': 'cantidad_reclamos',
    'DuracionProceso': 'duracion_proceso',
    'DiaSemanaPublicacion': 'dia_semana_publicacion',
    'Cantidad': 'cantidad',
    'GrupoOferentes': 'grupo_oferentes',
}


class SimuladorForm(forms.Form):
    codigo_producto_onu = forms.IntegerField(min_value=0)
    mes_publicacion = forms.TypedChoiceField(
        coerce=int, widget=forms.Select(attrs={'disabled': True}),
        choices=[('', 'Seleccionar mes')] + list(enumerate(
            ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'], 1)))
    dia_semana_publicacion = forms.TypedChoiceField(
        coerce=int, widget=forms.Select(attrs={'disabled': True}),
        choices=[('', 'Seleccionar día')] + list(enumerate(
            ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'], 1)))
    duracion_proceso = forms.FloatField(min_value=0)
    cantidad = forms.FloatField(min_value=0)
    cantidad_reclamos = forms.IntegerField(min_value=0)
    valor_total_ofertado = forms.FloatField(min_value=0)
    numero_oferentes = forms.IntegerField(min_value=1)


def simulador_context(request):
    return {'simulador_form': SimuladorForm()}


def formulario_para_licitacion(licitacion):
    """Prefill tender attributes and use its budget as the editable offer default."""
    initial = {}
    budget = getattr(licitacion, 'lic_presupuesto', None)
    if budget is not None and budget >= 0:
        initial['valor_total_ofertado'] = budget
    published = licitacion.lic_fecha_public
    if published:
        initial['mes_publicacion'] = published.month
        initial['dia_semana_publicacion'] = published.isoweekday()
        initial['duracion_proceso'] = max(0, (timezone.localdate() - published).days)
    codes = {str(code).strip() for code in (licitacion.lic_codigos_producto or [])
             if code is not None and str(code).strip()}
    # Multiple product lines require the user to choose the item to simulate.
    if len(codes) == 1:
        code = next(iter(codes))
        if code.isascii() and code.isdigit():
            initial['codigo_producto_onu'] = int(code)
    return SimuladorForm(initial=initial)


@lru_cache(maxsize=1)
def cargar_modelo():
    import joblib
    path = Path(getattr(settings, 'SIMULADOR_MODEL_PATH',
                        settings.BASE_DIR / 'smartbids' / 'ml_models' /
                        'arbol_decision_licitaciones_optimizado.joblib'))
    artifact = joblib.load(path)
    if set(artifact['columnas']) != set(FEATURES):
        raise ValueError('Unexpected model columns')
    if not math.isfinite(float(artifact['umbral'])) or not 0 <= artifact['umbral'] <= 1:
        raise ValueError('Invalid model threshold')
    return artifact


def preparar_datos_modelo(datos):
    datos = dict(datos)
    # Training used pandas dayofweek (Monday=0), while the form uses 1–7.
    datos['dia_semana_publicacion'] -= 1
    count = datos.pop('numero_oferentes')
    datos['grupo_oferentes'] = 1 if count <= 3 else 2 if count <= 6 else 3 if count == 7 else 4
    return datos


def predecir(datos):
    import pandas as pd
    datos = preparar_datos_modelo(datos)
    artifact = cargar_modelo()
    columns = artifact['columnas']
    frame = pd.DataFrame([[datos[FEATURES[c]] for c in columns]], columns=columns)
    model = artifact['modelo']
    positive_index = list(model.classes_).index(1)
    score = float(model.predict_proba(frame)[0][positive_index])
    threshold = float(artifact['umbral'])
    return {'puntuacion': round(score * 100, 2),
            'umbral': round(threshold * 100, 2),
            'etiqueta': 'Seleccionada' if score >= threshold else 'No seleccionada'}


@require_POST
def simulador_ofertas(request):
    form = SimuladorForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
    try:
        result = predecir(form.cleaned_data)
    except Exception:
        logger.exception('Simulator inference failed')
        return JsonResponse({'error': 'El modelo no está disponible. Intenta más tarde.'}, status=503)
    return JsonResponse({'resultado': result})
