from django.contrib import admin
from .models import Cliente, Campana, Proyecto, Entregable

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre_empresa', 'contacto_nombre', 'email', 'telefono', 'presupuesto_total')
    search_fields = ('nombre_empresa', 'contacto_nombre')

@admin.register(Campana)
class CampanaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cliente', 'presupuesto', 'fecha_inicio', 'fecha_fin')
    list_filter = ('cliente',)

@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'campana', 'estado', 'fecha_limite')
    list_filter = ('estado', 'campana')

@admin.register(Entregable)
class EntregableAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'proyecto', 'rol_responsable', 'asignado_a', 'estado', 'horas_estimadas', 'horas_reales', 'horas_revision')
    list_filter = ('estado', 'rol_responsable')
    search_fields = ('titulo',)