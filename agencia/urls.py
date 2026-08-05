# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard y Kanban
    path('dashboard/', views.dashboard, name='dashboard'),
    path('kanban/', views.kanban_view, name='kanban'),
    
    # CRUD Clientes
    path('clientes/', views.crear_cliente, name='crear_cliente'),
    path('clientes/<int:cliente_id>/editar/', views.editar_cliente, name='editar_cliente'),
    path('clientes/<int:cliente_id>/eliminar/', views.eliminar_cliente, name='eliminar_cliente'),
    path('clientes/<int:cliente_id>/reporte-pdf/', views.enviar_reporte_pdf_cliente, name='enviar_reporte_pdf_cliente'),
    
    # Campañas y Proyectos
    path('campanas/', views.crear_campana, name='crear_campana'),
    path('proyectos/', views.crear_proyecto, name='crear_proyecto'),
    
    # Usuarios y Creativos
    path('creativos/', views.gestionar_creativos, name='gestionar_creativos'),
    path('usuarios/', views.crear_usuario, name='crear_usuario'),
    
    # Revisiones
    path('entregable/<int:entregable_id>/revision/', views.agregar_revision, name='agregar_revision'),
    path('entregable/<int:entregable_id>/comprobante-pdf/', views.generar_comprobante_pdf_entregable, name='generar_comprobante_pdf_entregable'),
    
    # Cronograma y APIs
    path('cronograma/', views.cronograma_view, name='cronograma'),
    path('api/eventos/', views.api_eventos_entregables, name='api_eventos_entregables'),
    path('api/entregable/<int:entregable_id>/cambiar-estado/', views.cambiar_estado_entregable, name='cambiar_estado_entregable'),
    path('exportar-rentabilidad-csv/', views.exportar_rentabilidad_csv, name='exportar_rentabilidad_csv'),
]