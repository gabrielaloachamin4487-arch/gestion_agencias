from django.urls import path
from . import views

urlpatterns = [
    # ==========================================
    # 1. RUTAS PRINCIPALES Y AUTENTICACIÓN
    # ==========================================
    path('', views.inicio, name='inicio'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ==========================================
    # 2. TABLERO KANBAN Y CRONOGRAMA
    # ==========================================
    path('kanban/', views.kanban_view, name='kanban'),
    path('cronograma/', views.cronograma_view, name='cronograma'),
    
    # ==========================================
    # 3. GESTIÓN DE ENTIDADES (SOLO ADMIN)
    # ==========================================
    path('clientes/', views.crear_cliente, name='crear_cliente'),
    path('clientes/editar/<int:cliente_id>/', views.editar_cliente, name='editar_cliente'),
    path('clientes/eliminar/<int:cliente_id>/', views.eliminar_cliente, name='eliminar_cliente'),
    path('campanas/', views.crear_campana, name='crear_campana'),
    path('proyectos/', views.crear_proyecto, name='crear_proyecto'),
    path('usuarios/', views.crear_usuario, name='crear_usuario'),
    
    # ==========================================
    # 4. ENVÍO DE REPORTES PDF POR CORREO
    # ==========================================
    path('clientes/enviar-pdf/<int:cliente_id>/', views.enviar_reporte_pdf_cliente, name='enviar_reporte_pdf_cliente'),
    
    # ==========================================
    # 5. REGISTRO DE REVISIONES Y AJUSTES
    # ==========================================
    path('revision/<int:entregable_id>/', views.agregar_revision, name='agregar_revision'),
    
    # ==========================================
    # 6. ENDPOINTS API (JSON)
    # ==========================================
    path('api/eventos/', views.api_eventos_entregables, name='api_eventos_entregables'),
    path('api/cambiar-estado/<int:entregable_id>/', views.cambiar_estado_entregable, name='cambiar_estado_entregable'),
]