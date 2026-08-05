from django.contrib import admin
from .models import Cliente, Campana, Proyecto, Creativo, Entregable, Revision

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre_empresa', 'ruc', 'contacto_nombre', 'email', 'telefono', 'presupuesto_total', 'estado')
    search_fields = ('nombre_empresa', 'contacto_nombre', 'ruc')
    list_filter = ('estado',)

@admin.register(Campana)
class CampanaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cliente', 'presupuesto', 'fecha_inicio', 'fecha_fin', 'estado')
    list_filter = ('estado', 'cliente')
    search_fields = ('nombre',)

@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'campana', 'tipo', 'prioridad', 'estado', 'horas_estimadas', 'horas_reales', 'fecha_limite')
    list_filter = ('estado', 'tipo', 'prioridad', 'campana')
    search_fields = ('titulo',)

@admin.register(Creativo)
class CreativoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'tarifa_hora', 'estado')
    list_filter = ('rol', 'estado')

@admin.register(Entregable)
class EntregableAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'proyecto', 'creativo', 'rol_responsable', 'estado', 'horas_estimadas', 'horas_reales', 'fecha_limite')
    list_filter = ('estado', 'rol_responsable')
    search_fields = ('titulo',)

@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ('entregable', 'revisor', 'aprobado', 'horas_adicionales', 'fecha_revision')
    list_filter = ('aprobado', 'fecha_revision')