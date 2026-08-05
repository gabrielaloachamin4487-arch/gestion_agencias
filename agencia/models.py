from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


def validar_peso_archivo(value):
    limit = 25 * 1024 * 1024  # 25 MB
    if value and hasattr(value, 'size') and value.size > limit:
        raise ValidationError("El peso máximo permitido para la subida de archivos es de 25 MB.")


class Cliente(models.Model):
    ESTADOS = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
    ]

    usuario = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='perfil_cliente'
    )
    nombre_empresa = models.CharField(max_length=150)
    ruc = models.CharField(max_length=13, blank=True, null=True, unique=True, verbose_name="RUC / Tax ID")
    contacto_nombre = models.CharField(max_length=100, verbose_name="Contacto Principal")
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True, null=True)
    logotipo = models.ImageField(upload_to='logos/', blank=True, null=True)
    presupuesto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='ACTIVO')

    @property
    def contacto_principal(self):
        return self.contacto_nombre

    def __str__(self):
        return self.nombre_empresa


class Campana(models.Model):
    ESTADOS = [
        ('PLANIFICACION', 'Planificación'),
        ('EN_PROGRESO', 'En Progreso'),
        ('FINALIZADA', 'Finalizada'),
        ('CANCELADA', 'Cancelada'),
    ]

    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE, 
        related_name='campanas'
    )
    nombre = models.CharField(max_length=150)
    presupuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PLANIFICACION')

    def __str__(self):
        return f"{self.nombre} - {self.cliente.nombre_empresa}"


class Proyecto(models.Model):
    TIPOS = [
        ('DISEÑO', 'Diseño'),
        ('VIDEO', 'Video'),
        ('BRANDING', 'Branding'),
        ('WEB', 'Web'),
    ]
    PRIORIDADES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]
    ESTADOS = [
        ('NUEVO', 'Nuevo'),
        ('EN_PROCESO', 'En Proceso'),
        ('REVISION', 'En Revisión'),
        ('FINALIZADO', 'Finalizado'),
    ]

    campana = models.ForeignKey(
        Campana, 
        on_delete=models.CASCADE, 
        related_name='proyectos'
    )
    titulo = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='DISEÑO')
    prioridad = models.CharField(max_length=20, choices=PRIORIDADES, default='MEDIA')
    horas_estimadas = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    horas_reales = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='NUEVO')
    fecha_limite = models.DateField(null=True, blank=True)

    @property
    def nombre(self):
        return self.titulo

    def __str__(self):
        return self.titulo


class Creativo(models.Model):
    ROLES = [
        ('DISEÑADOR_GRAFICO', 'Diseñador Gráfico'),
        ('COPYWRITER', 'Copywriter'),
        ('EDITOR_VIDEO', 'Editor Video'),
        ('DIRECTOR_ARTE', 'Director de Arte'),
    ]
    ESTADOS = [
        ('DISPONIBLE', 'Disponible'),
        ('OCUPADO', 'Ocupado'),
    ]

    usuario = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='perfil_creativo'
    )
    rol = models.CharField(max_length=30, choices=ROLES, default='DISEÑADOR_GRAFICO')
    tarifa_hora = models.DecimalField(max_digits=8, decimal_places=2, default=25.00)
    foto_perfil = models.ImageField(upload_to='perfiles/', null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='DISPONIBLE')

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} ({self.get_rol_display()})"


class Entregable(models.Model):
    ESTADOS = [
        ('POR_INICIAR', 'Por Iniciar'),
        ('EN_PROCESO', 'En Proceso'),
        ('EN_REVISION', 'En Revisión'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
    ]
    ROLES = [
        ('DISEÑADOR_GRAFICO', 'Diseñador Gráfico'),
        ('COPYWRITER', 'Copywriter'),
        ('EDITOR_VIDEO', 'Editor Video'),
        ('DIRECTOR_ARTE', 'Director de Arte'),
    ]

    proyecto = models.ForeignKey(
        Proyecto, 
        on_delete=models.CASCADE, 
        related_name='entregables'
    )
    titulo = models.CharField(max_length=150)
    creativo = models.ForeignKey(
        Creativo, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='entregables'
    )
    asignado_a = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='entregables_legacy'
    )
    rol_responsable = models.CharField(max_length=30, choices=ROLES, default='DISEÑADOR_GRAFICO')
    archivo = models.FileField(
        upload_to='entregables/', 
        null=True, 
        blank=True, 
        validators=[validar_peso_archivo]
    )
    version = models.IntegerField(default=1)
    fecha_limite = models.DateField(null=True, blank=True)
    fecha_entrega = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='POR_INICIAR')
    
    # Control de Horas
    horas_estimadas = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    horas_reales = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    horas_revision = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.titulo} ({self.proyecto.titulo})"

    @property
    def num_revisiones(self):
        return self.revisiones.count()

    @property
    def horas_rebasadas(self):
        """Si un cliente genera más de 3 revisiones sobre el entregable, 
        las horas adicionales de la 4ta revisión en adelante se registran como horas rebasadas."""
        revs = list(self.revisiones.order_by('fecha'))
        if len(revs) > 3:
            exceso = sum(float(r.horas_adicionales or 0) for r in revs[3:])
            return exceso
        return 0.0


class Revision(models.Model):
    entregable = models.ForeignKey(
        Entregable, 
        on_delete=models.CASCADE, 
        related_name='revisiones'
    )
    revisor = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='revisiones'
    )
    realizado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='revisiones_realizadas'
    )
    comentarios = models.TextField()
    archivo_anotaciones = models.FileField(
        upload_to='revisiones/', 
        null=True, 
        blank=True, 
        validators=[validar_peso_archivo]
    )
    horas_adicionales = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    aprobado = models.BooleanField(default=False)
    fecha_revision = models.DateTimeField(auto_now_add=True)

    @property
    def comentario(self):
        return self.comentarios

    def __str__(self):
        return f"Revisión {self.id} - {self.entregable.titulo} ({'Aprobado' if self.aprobado else 'Ajuste'})"