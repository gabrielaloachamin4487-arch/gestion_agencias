from django.contrib import admin
from .models import Cliente, Campana, Proyecto, Creativo, Entregable, Revision


class RevisionInline(admin.TabularInline):
    """Permite ver y agregar revisiones directamente dentro del Entregable."""
    model = Revision
    extra = 1
    fields = ('revisor', 'realizado_por', 'comentarios', 'horas_adicionales', 'aprobado', 'archivo_anotaciones')
    readonly_fields = ('fecha_revision',)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre_empresa', 'ruc', 'contacto_nombre', 'email', 'telefono', 'presupuesto_total', 'estado')
    search_fields = ('nombre_empresa', 'contacto_nombre', 'ruc', 'email')
    list_filter = ('estado',)
    list_editable = ('estado',)


@admin.register(Campana)
class CampanaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cliente', 'presupuesto', 'fecha_inicio', 'fecha_fin', 'estado')
    list_filter = ('estado', 'cliente')
    search_fields = ('nombre', 'cliente__nombre_empresa')
    raw_id_fields = ('cliente',)


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'campana', 'tipo', 'prioridad', 'estado', 'horas_estimadas', 'horas_reales', 'fecha_limite')
    list_filter = ('estado', 'tipo', 'prioridad', 'campana__cliente')
    search_fields = ('titulo', 'descripcion', 'campana__nombre')
    raw_id_fields = ('campana',)


@admin.register(Creativo)
class CreativoAdmin(admin.ModelAdmin):
    list_display = ('obtener_nombre_completo', 'usuario', 'rol', 'tarifa_hora', 'estado')
    list_filter = ('rol', 'estado')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'usuario__email')
    raw_id_fields = ('usuario',)

    @admin.display(description='Nombre Completo')
    def obtener_nombre_completo(self, obj):
        return obj.usuario.get_full_name() or obj.usuario.username


@admin.register(Entregable)
class EntregableAdmin(admin.ModelAdmin):
    list_display = (
        'titulo', 
        'proyecto', 
        'creativo', 
        'rol_responsable', 
        'estado', 
        'horas_estimadas', 
        'horas_reales', 
        'obtener_num_revisiones', 
        'obtener_horas_rebasadas', 
        'fecha_limite'
    )
    list_filter = ('estado', 'rol_responsable', 'proyecto__campana')
    search_fields = ('titulo', 'proyecto__titulo', 'creativo__usuario__username')
    raw_id_fields = ('proyecto', 'creativo', 'asignado_a')
    inlines = [RevisionInline]

    @admin.display(description='Nº Revisiones')
    def obtener_num_revisiones(self, obj):
        return obj.num_revisiones

    @admin.display(description='Horas Rebasadas')
    def obtener_horas_rebasadas(self, obj):
        return f"{obj.horas_rebasadas:.2f} hrs"


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'entregable', 'revisor', 'realizado_por', 'aprobado', 'horas_adicionales', 'fecha_revision')
    list_filter = ('aprobado', 'fecha_revision')
    search_fields = ('entregable__titulo', 'comentarios', 'revisor__username', 'realizado_por__username')
    raw_id_fields = ('entregable', 'revisor', 'realizado_por')
    readonly_fields = ('fecha_revision',)