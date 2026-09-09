import base64
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class GmailApiBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.service = None

    def _obtener_servicio(self):
        # Lee la variable que contiene todo el JSON
        token_env = os.getenv('GMAIL_TOKEN_JSON')

        if not token_env:
            raise ImproperlyConfigured(
                "La variable de entorno 'GMAIL_TOKEN_JSON' no está configurada en el .env."
            )

        try:
            token_data = json.loads(token_env)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception as e:
            raise ImproperlyConfigured(f"Error al procesar GMAIL_TOKEN_JSON desde el .env: {e}")

        # Renueva el token de acceso usando el refresh_token si ya expiró
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        return build('gmail', 'v1', credentials=creds)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        try:
            if not self.service:
                self.service = self._obtener_servicio()
        except Exception as e:
            if not self.fail_silently:
                raise e
            return 0

        num_sent = 0
        for message in email_messages:
            try:
                mime_msg = MIMEMultipart('alternative')
                mime_msg['To'] = ', '.join(message.to)
                mime_msg['From'] = message.from_email or settings.DEFAULT_FROM_EMAIL
                mime_msg['Subject'] = message.subject

                if message.body:
                    mime_msg.attach(MIMEText(message.body, 'plain', 'utf-8'))

                for content, mimetype in getattr(message, 'alternatives', []):
                    if mimetype == 'text/html':
                        mime_msg.attach(MIMEText(content, 'html', 'utf-8'))

                raw_message = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode('utf-8')

                self.service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute()

                num_sent += 1
            except Exception as e:
                if not self.fail_silently:
                    raise e

        return num_sent