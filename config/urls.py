from django.contrib import admin
from django.urls import path
from agencia import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),
    path('kanban/', views.kanban_view, name='kanban'),
    path('cronograma/', views.cronograma_view, name='cronograma'),
    
    # Nombre 'proyectos' habilitado para evitar NoReverseMatch
    path('proyectos/', views.crear_proyecto, name='proyectos'),
    path('proyectos/crear/', views.crear_proyecto, name='crear_proyecto'),
    
    path('clientes/', views.crear_cliente, name='clientes'),
    path('clientes/crear/', views.crear_cliente, name='crear_cliente'),
    
    path('campanas/', views.crear_campana, name='campanas'),
    path('campanas/crear/', views.crear_campana, name='crear_campana'),
    
    path('api/eventos/', views.api_eventos_entregables, name='api_eventos_entregables'),
    path('api/entregable/<int:entregable_id>/estado/', views.cambiar_estado_entregable, name='cambiar_estado_entregable'),
]