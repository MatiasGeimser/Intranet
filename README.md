# Intranet Corporativa Premium, Segura y Escalable (FastAPI + Jinja2 + SQLAlchemy + TailwindCSS)

Esta es una intranet corporativa completa y robusta construida con **Python 3.12+** y **FastAPI** como núcleo principal. Está diseñada bajo estrictos estándares de **ciberseguridad** e incorpora una interfaz de usuario premium inspirada en el minimalismo y funcionalidad de plataformas como **Stripe, Notion y Linear**.

---

## 🛠️ Stack Tecnológico Opcional & Producción

### Backend (Python)
- **FastAPI**: Endpoints REST API de altísimo desempeño y renderizado asíncrono rápido.
- **SQLAlchemy (V2.0)**: Mapeo de base de datos ORM híbrido con soporte nativo para **SQLite** (desarrollo rápido instantáneo) y **PostgreSQL** (producción).
- **Cryptography (AES-256-GCM)**: Cifrado simétrico de credenciales del Password Vault mediante una de las cunas de ciberseguridad más robustas del estándar AEAD.
- **PyJWT**: Firma digital HMAC-SHA256 para tokens de sesión y rotación segura de Refresh Tokens.
- **Passlib (Bcrypt)**: Hasheo seguro de contraseñas de usuarios.
- **Bleach**: Sanitización estricta de código HTML en hilos de comentarios y boletines de noticias para mitigar ataques XSS.

### Frontend
- **Jinja2 + HTML5 Semántico**: Servido y compilado directamente en servidor para máximo rendimiento.
- **TailwindCSS**: Diseño completamente adaptativo (responsive) e identidad visual con la paleta corporativa:
  - Gris principal: `#8C8C8C`
  - Azul corporativo: `#049DD9`
  - Verde agua/acento: `#79F2E6`
  - Negro oscuro: `#262523`
  - Gris claro/fondo: `#F2F2F2`
- **Chart.js**: Paneles de gráficas e interactividad de tráfico en el Dashboard.
- **Vanilla JS**: Modales, drag & drop de documentos, copiado rápido y desencriptación interactiva auditada de contraseñas.

---

## 🔒 Mecanismos de Ciberseguridad Activa

1. **Protección contra XSS (Cross-Site Scripting)**: Sanitización activa en backend (`bleach`) y escape nativo de HTML en Jinja2.
2. **Protección contra CSRF (Cross-Site Request Forgery)**: Middleware que inyecta y valida tokens csrf mediante cookies de sesión cifradas y validaciones en cabeceras `x-csrf-token` para verbos mutables (`POST`/`PUT`/`DELETE`).
3. **Auditoría Forense Integral (Compliance)**: Cada acción delicada (desencriptación de claves, accesos fallidos, subidas) genera un registro inalterable en `audit_logs` con IP, hora y descripción del ejecutor.
4. **Protección contra Fuerza Bruta**: Middleware de **Rate Limiting** in-memory configurable en rutas de acceso.
5. **Autenticación Cookie HTTPOnly**: Los tokens JWT de sesión se transmiten de manera segura en cabeceras de cookies configuradas con `HttpOnly` y `SameSite=Lax` para prevenir el secuestro de sesiones por JS de terceros.

---

## 📁 Arquitectura del Proyecto

```text
/c:/Intranet
├── Dockerfile              # Empaquetado Docker optimizado multi-stage
├── docker-compose.yml      # Orquestador (FastAPI, PostgreSQL, Redis)
├── requirements.txt        # Librerías y dependencias
├── run.py                  # Script arrancador local
├── .env                    # Configuración activa
└── /app
    ├── main.py             # Inicializador FastAPI y registro de Middlewares
    ├── /api
    │   ├── deps.py         # Inyectores de dependencias y control de acceso RBAC
    │   └── /endpoints      # Controladores de la API REST y Vistas Jinja2
    ├── /core
    │   ├── config.py       # Pydantic Base Settings
    │   ├── database.py     # Conector SQLAlchemy
    │   ├── database_seed.py# Sembrador y configurador de datos iniciales en BD
    │   └── security.py     # Cifrados AES y Hashes bcrypt
    ├── /models             # Entidades SQLAlchemy (User, Role, Credential, etc.)
    ├── /schemas            # Esquemas de validación Pydantic
    ├── /services           # Lógica de negocio (Criptografía, Uploads, Sesiones)
    ├── /middlewares        # XSS Headers, CSRF y Rate Limit
    ├── /templates          # Vistas HTML5 con Tailwind y Javascript
    └── /static             # Archivos de soporte (Avatar predeterminado SVG, uploads)
```

---

## 🚀 Guía de Puesta en Marcha (Local Rápido)

Para facilitar la evaluación de la intranet sin necesidad de configurar bases de datos externas o contenedores, el sistema detecta y se auto-configura con **SQLite** en un archivo local llamado `intranet.db` al instante de encenderlo:

1. **Instalar Dependencias de Python**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Ejecutar el Servidor**:
   ```bash
   python run.py
   ```

3. **Abrir la Plataforma**:
   Abra en su navegador la URL: [http://localhost:8000](http://localhost:8000).

---

## 🐳 Guía de Despliegue con Docker Compose (PostgreSQL)

Para simular un entorno de producción contenerizado de alta fidelidad con persistencia de volumen y base de datos relacional PostgreSQL:

1. **Levantar los Contenedores**:
   ```bash
   docker-compose up --build
   ```

2. **Acceso**:
   El servidor FastAPI se expondrá automáticamente en [http://localhost:8000](http://localhost:8000).

---

## 🔑 Credenciales de Acceso Iniciales (Sembrado Automático)

Al arrancar el sistema por primera vez (sea en SQLite o PostgreSQL), el sembrador de base de datos (`app/core/database_seed.py`) inyecta automáticamente los roles de ciberseguridad corporativos y la siguiente cuenta de administrador de sistemas:

- **Usuario**: `admin@intranet.local`
- **Contraseña**: `Admin12345!`

### Roles Disponibles (RBAC)
1. **Administrador**: Acceso absoluto. Único capaz de ver auditorías completas, desactivar usuarios y reasignar roles.
2. **Supervisor**: Capaz de auditar y subir documentos, agendar eventos y redactar boletines de noticias corporativas.
3. **Usuario estándar**: Acceso básico a su propia bóveda de contraseñas AES, calendario operativo y descarga de documentos de su carpeta.
