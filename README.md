<div align="center">

# 🚀 SmartBids — Inteligencia para Ofertar

**Plataforma SaaS para el mercado de compras públicas (Mercado Público / ChileCompra)**  
*Analítica de datos masivos y Machine Learning predictivo para MiPyMEs.*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.x-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Firebase](https://img.shields.io/badge/Firebase-Auth%20%26%20Firestore-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)](https://firebase.google.com/)

[📖 Ver Guía Completa de Instalación y Comandos Git (readme.txt)](./readme.txt)

</div>

---

## 📌 Vista General de la Plataforma

SmartBids automatiza el monitoreo de licitaciones públicas en Chile, aplicando modelos de Machine Learning (XGBoost / Scikit-Learn) para predecir probabilidades de éxito según bases técnicas y datos históricos.

![Hero Section](docs/img/01-hero-landing.png)
*Vista principal con scoring predictivo de adjudicación y métricas de mercado.*

---

## 📸 Recorrido Visual de Módulos

### 1. Inteligencia de Mercado y Licitaciones
| Dashboard Analítico | Mis Licitaciones Sincronizadas |
| :---: | :---: |
| ![Dashboard Analítico](docs/img/18-dashboard-analitico.png) | ![Mis Licitaciones](docs/img/19-mis-licitaciones-oportunidades.png) |
| *Métricas trimestrales, competencia y productos top* | *Oportunidades de compra filtradas según perfil* |

---

### 2. Autenticación y Verificación en Dos Pasos (2FA)
| Acceso / Inicio de Sesión | Validación de Seguridad OTP (6 dígitos) |
| :---: | :---: |
| ![Iniciar Sesión](docs/img/09-iniciar-sesion.png) | ![Modal OTP](docs/img/14-modal-verificacion-otp.png) |
| *Formulario de ingreso al panel* | *Modal interactivo para verificación en 2 pasos* |

| Código Transaccional por Correo | Registro de Nuevas MiPyMEs |
| :---: | :---: |
| ![Correo OTP](docs/img/15-email-codigo-autenticacion.png) | ![Registro](docs/img/10-crear-cuenta.png) |
| *Notificación transaccional con vigencia de 10 min* | *Alta de cuenta y credenciales corporativas* |

---

### 3. Perfilamiento Empresarial y Filtros de Búsqueda
| Información del Suscriptor | Datos de la Empresa (Tributaria) |
| :---: | :---: |
| ![Datos Personales](docs/img/11-perfil-datos-personales.png) | ![Datos Empresa](docs/img/12-perfil-datos-empresa.png) |
| *Gestión de usuario y estado de calibración* | *RUT de empresa, razón social y contacto comercial* |

| Calibración de Mercado (Catálogo ONU) | Seguridad y Cambio de Clave |
| :---: | :---: |
| ![Filtros Mercado](docs/img/13-filtros-mercado-licitaciones.png) | ![Seguridad](docs/img/17-seguridad-cambiar-clave.png) |
| *Segmentación por territorio, códigos ONU y entidades* | *Actualización de credenciales y auditoría de sesión* |

---

### 4. Sistema Dinámico de Alertas y Notificaciones Globales
| Panel de Administración de Alertas | Demostración en Vivo |
| :---: | :---: |
| ![Administración de Mensajería](docs/img/Captura%20de%20pantalla%202026-10-03%20a%20la(s)%201.25.59%20p.m..jpg) | ![Demo Alertas](docs/img/demo-mensajeria-alertas.gif) |
| *Consola administrativa para avisos en tiempo real* | *Notificaciones flotantes con temporizador regresivo* |

---

<details>
<summary><strong>🔍 Ver más vistas: Propuesta de Valor, Modelos de IA y Marco Normativo (Clic para desplegar)</strong></summary>

<br>

#### Propuesta de Valor y Módulos
| Pilares de la Solución | Búsqueda Avanzada y Perfilamiento |
| :---: | :---: |
| ![Propuesta de Valor](docs/img/02-propuesta-valor.png) | ![Búsqueda](docs/img/03-busqueda-perfilamiento.png) |

#### Modelos Predictivos y Beneficios Comerciales
| Motor Predictivo (XGBoost) | Beneficios Cuantificables |
| :---: | :---: |
| ![Modelos Predictivos](docs/img/04-modelos-predictivos.png) | ![Beneficios](docs/img/05-beneficios-tangibles.png) |

#### Marco Legal, Privacidad y Ciberseguridad
| Términos del Servicio | Política de Privacidad (Ley N° 19.628) | Seguridad Empresarial |
| :---: | :---: | :---: |
| ![Términos](docs/img/06-terminos-del-servicio.png) | ![Privacidad](docs/img/07-politica-de-privacidad.png) | ![Seguridad 2FA](docs/img/08-seguridad-2fa.png) |

</details>

---

## 🛠️ Stack Tecnológico

* **Backend:** Python 3.10+, Django, WhiteNoise, Gunicorn[cite: 7, 43].
* **Machine Learning & Datos:** Scikit-Learn, XGBoost, Pandas[cite: 10].
* **Frontend:** HTML5, CSS3 modular, JavaScript ES6+, FontAwesome[cite: 7, 31].
* **Autenticación & Real-time:** Firebase Authentication (2FA/OTP), Cloud Firestore[cite: 13, 23, 38].
* **Base de Datos Relacional:** PostgreSQL.

---

## ⚙️ Instalación y Despliegue Local

Toda la guía paso a paso para ejecutar el entorno en **Ubuntu / Debian**, **macOS** o **Windows**, junto a la sincronización de ramas con Git, se encuentra disponible en:

👉 **[Consultar la Guía de Instalación Detallada (readme.txt)](./readme.txt)**