import secrets
import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

# ==============================================================================
# VISTAS DE PÁGINAS Y NAVEGACIÓN
# ==============================================================================

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


def handler404_view(request, exception=None):
    return render(request, 'smartbids/404.html', status=404)


# ==============================================================================
# correo de Bienvenida
# ==============================================================================


@csrf_exempt
def enviar_correo_bienvenida(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        email_destinatario = data.get('email')

        if not email_destinatario:
            return JsonResponse({'status': 'error', 'mensaje': 'El correo electrónico es requerido.'}, status=400)

        asunto = '🚀 ¡Bienvenido a SmartBids! Comienza a ganar licitaciones'
        
        mensaje_plano = (
            f'¡Hola!\n\n'
            f'Te damos la bienvenida a SmartBids. Tu cuenta ({email_destinatario}) '
            f'ha sido registrada exitosamente. Por favor verifica tu correo para comenzar.'
        )

        html_mensaje = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f8f7; margin: 0; padding: 20px; color: #2d3748; }}
                .card {{ max-width: 560px; background: #ffffff; margin: 0 auto; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #e2ece9; }}
                .header {{ background: linear-gradient(135deg, #11634e 0%, #0b3831 100%); padding: 35px 30px; text-align: center; color: #ffffff; }}
                .header h1 {{ margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -0.5px; }}
                .header p {{ color: #b1d2ca; margin: 8px 0 0 0; font-size: 15px; }}
                .body {{ padding: 30px; }}
                .user-badge {{ background: #eef7f4; border-left: 4px solid #1ec498; padding: 12px 16px; border-radius: 4px; margin: 20px 0; font-size: 14px; color: #11634e; font-weight: 600; }}
                .features {{ background: #fdfefe; border: 1px dashed #b1d2ca; border-radius: 10px; padding: 18px 20px; margin: 25px 0; }}
                .features ul {{ margin: 0; padding-left: 18px; }}
                .features li {{ margin-bottom: 8px; font-size: 14px; color: #4a5568; }}
                .alert-box {{ background: #fffaf0; border: 1px solid #feebc8; border-radius: 8px; padding: 14px; margin: 20px 0; font-size: 13px; color: #c05621; }}
                .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #a0aec0; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="header">
                    <h1>¡Bienvenido a SmartBids! 🚀</h1>
                    <p>Inteligencia y datos para tus licitaciones</p>
                </div>
                <div class="body">
                    <p style="font-size: 16px; line-height: 1.6;">
                        ¡Hola! Estamos felices de darte la bienvenida a nuestra plataforma de analítica y monitoreo de compras públicas.
                    </p>
                    
                    <div class="user-badge">
                        👤 Cuenta registrada: <span>{email_destinatario}</span>
                    </div>

                    <div class="features">
                        <strong style="color: #11634e; display: block; margin-bottom: 8px;">¿Qué puedes hacer en SmartBids?</strong>
                        <ul>
                            <li>🎯 <strong>Monitorear</strong> oportunidades de negocio en Mercado Público en tiempo real.</li>
                            <li>🤖 <strong>Predecir</strong> probabilidades de adjudicación mediante Machine Learning.</li>
                            <li>⚡ <strong>Optimizar</strong> tus ofertas y tomar decisiones basadas en datos.</li>
                        </ul>
                    </div>

                    <div class="alert-box">
                        🔔 <strong>Paso indispensable:</strong> Recuerda hacer clic en el enlace de activación que enviamos a tu correo para habilitar tu acceso completo.
                    </div>

                    <p style="font-size: 14px; color: #718096; margin-top: 25px;">
                        Saludos cordiales,<br>
                        <strong style="color: #11634e;">El equipo de SmartBids</strong>
                    </p>
                </div>
                <div class="footer">
                    © SmartBids — Transformando el acceso al mercado público
                </div>
            </div>
        </body>
        </html>
        """

        # Enviar correo con soporte HTML y texto alternativo
        send_mail(
            subject=asunto,
            message=mensaje_plano,
            html_message=html_mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_destinatario],
            fail_silently=False,
        )

        return JsonResponse({
            'status': 'ok',
            'mensaje': 'Correo de bienvenida enviado exitosamente.'
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Cuerpo de la petición JSON inválido.'
        }, status=400)

    except Exception as e:
        logger.error(f"[SmartBids] Error al enviar correo de bienvenida: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error en el servidor de correo: {str(e)}'
        }, status=500)
    """
    API endpoint para despachar el correo de bienvenida vía SMTP de Gmail
    tras el registro de un nuevo usuario desde Firebase.
    """
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Método no permitido. Solo se acepta POST.'
        }, status=405)

    try:
        data = json.loads(request.body)
        email_destinatario = data.get('email')

        if not email_destinatario:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Correo no proporcionado.'
            }, status=400)

            asunto = '🚀 ¡Bienvenido a SmartBids! Tu puerta de entrada a las compras públicas'
            mensaje = (
                f'═══════════════════════════════════════════════════════════\n'
                f'        ¡BIENVENIDO/A A SMARTBIDS! 🚀\n'
                f'═══════════════════════════════════════════════════════════\n\n'
                f'¡Hola!\n\n'
                f'Estamos muy entusiasmados de darte la bienvenida a nuestra plataforma. '
                f'Tu cuenta ({email_destinatario}) ha sido creada con éxito.\n\n'
                f'✨ CON SMARTBIDS PODRÁS:\n'
                f'  • 🔍 Descubrir licitaciones públicas relevantes en Mercado Público.\n'
                f'  • 📊 Analizar probabilidades de adjudicación con Inteligencia Artificial.\n'
                f'  • 🔔 Recibir alertas y recomendaciones personalizadas para tu negocio.\n\n'
                f'───────────────────────────────────────────────────────────\n'
                f'⚠️ PASO IMPORTANTE PARA COMENZAR:\n'
                f'Para proteger tu cuenta y desbloquear todas las herramientas, por favor\n'
                f'revisa el correo de verificación que te enviamos y haz clic en el enlace.\n'
                f'───────────────────────────────────────────────────────────\n\n'
                f'Si tienes alguna duda o sugerencia, nuestro equipo está siempre atento\n'
                f'para ayudarte a potenciar tus postulaciones.\n\n'
                f'¡Mucho éxito en tus próximas licitaciones!\n\n'
                f'Atentamente,\n'
                f'El equipo de SmartBids\n'
                f'https://smartbids.cl'
            )   

        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_destinatario],
            fail_silently=False,
        )

        return JsonResponse({
            'status': 'ok',
            'mensaje': 'Correo de bienvenida enviado exitosamente.'
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Cuerpo de la petición JSON inválido.'
        }, status=400)

    except Exception as e:
        logger.error(f"[SmartBids] Error al enviar correo de bienvenida: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error en el servidor de correo: {str(e)}'
        }, status=500)





# ==============================================================================
# correo de envio de codigo
# ==============================================================================

@csrf_exempt
def enviar_codigo_login(request):
    """
    API endpoint para generar y enviar un código OTP de 6 dígitos
    al iniciar sesión.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        email_destinatario = data.get('email')

        if not email_destinatario:
            return JsonResponse({'status': 'error', 'mensaje': 'El correo electrónico es requerido.'}, status=400)

        # Genera un código criptográficamente seguro de 6 dígitos (100000 a 999999)
        codigo_seguridad = f"{secrets.randbelow(900000) + 100000}"

        asunto = f'🔐 Tu código de acceso SmartBids: {codigo_seguridad}'
        
        mensaje_plano = (
            f'¡Hola!\n\n'
            f'Tu código de verificación para iniciar sesión en SmartBids es: {codigo_seguridad}\n\n'
            f'Este código es personal e intransferible. Si no intentaste iniciar sesión, ignora este mensaje.'
        )

        html_mensaje = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f8f7; margin: 0; padding: 20px; color: #2d3748; }}
                .card {{ max-width: 560px; background: #ffffff; margin: 0 auto; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #e2ece9; }}
                .header {{ background: linear-gradient(135deg, #11634e 0%, #0b3831 100%); padding: 35px 30px; text-align: center; color: #ffffff; }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 800; }}
                .header p {{ color: #b1d2ca; margin: 8px 0 0 0; font-size: 14px; }}
                .body {{ padding: 30px; text-align: center; }}
                .code-box {{ background: #eef7f4; border: 2px dashed #1ec498; border-radius: 12px; padding: 18px 10px; margin: 25px auto; max-width: 280px; }}
                .code {{ font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #11634e; font-family: 'Consolas', monospace; }}
                .alert-box {{ background: #fffaf0; border: 1px solid #feebc8; border-radius: 8px; padding: 12px 14px; margin: 20px 0; font-size: 13px; color: #c05621; text-align: left; }}
                .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #a0aec0; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="header">
                    <h1>Código de Autenticación 🔐</h1>
                    <p>Verificación de seguridad en dos pasos</p>
                </div>
                <div class="body">
                    <p style="font-size: 15px; color: #4a5568; line-height: 1.5; margin: 0;">
                        Has solicitado ingresar a tu cuenta de <strong>SmartBids</strong> ({email_destinatario}). Utiliza el siguiente código para completar tu acceso:
                    </p>
                    
                    <div class="code-box">
                        <span class="code">{codigo_seguridad}</span>
                    </div>

                    <div class="alert-box">
                        ⚠️ <strong>Importante:</strong> Este código expira pronto y no debe compartirse con nadie. Si no intentaste iniciar sesión, te recomendamos cambiar tu contraseña inmediatamente.
                    </div>

                    <p style="font-size: 14px; color: #718096; margin-top: 25px; text-align: left;">
                        Saludos cordiales,<br>
                        <strong style="color: #11634e;">El equipo de Seguridad de SmartBids</strong>
                    </p>
                </div>
                <div class="footer">
                    © SmartBids — Transformando el acceso al mercado público
                </div>
            </div>
        </body>
        </html>
        """

        send_mail(
            subject=asunto,
            message=mensaje_plano,
            html_message=html_mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_destinatario],
            fail_silently=False,
        )

        return JsonResponse({
            'status': 'ok',
            'codigo': codigo_seguridad,  # Retornado para validación o hashing
            'mensaje': 'Código enviado exitosamente.'
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido.'}, status=400)
    except Exception as e:
        logger.error(f"[SmartBids] Error al enviar código de login: {str(e)}")
        return JsonResponse({'status': 'error', 'mensaje': f'Error en el servidor: {str(e)}'}, status=500)