from django.db import models
from django.contrib.auth.models import User

class Cliente(models.Model):
    # Relación opcional con User para permitir inicio de sesión a clientes
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='perfil_cliente')
    nombre_empresa = models.CharField(max_length=150)
    contacto_nombre = models.CharField(max_length=100)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True, null=True)
    presupuesto_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def __str__(self):
        return self.nombre_empresa

class Campana(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='campanas')
    nombre = models.CharField(max_length=150)
    presupuesto = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} - {self.cliente.nombre_empresa}"

class Proyecto(models.Model):
    ESTADOS = [
        ('NUEVO', 'Nuevo'),
        ('EN_PROCESO', 'En Proceso'),
        ('REVISION', 'En Revisión'),
        ('FINALIZADO', 'Finalizado'),
    ]
    campana = models.ForeignKey(Campana, on_delete=models.CASCADE, related_name='proyectos')
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='NUEVO')
    fecha_limite = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.titulo

class Entregable(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En Proceso'),
        ('CORRECCION', 'Corrección'),
        ('APROBADO', 'Aprobado'),
    ]
    ROLES = [
        ('DISEÑADOR', 'Diseñador'),
        ('COPYWRITER', 'Copywriter'),
    ]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='entregables')
    titulo = models.CharField(max_length=150)
    asignado_a = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='entregables')
    rol_responsable = models.CharField(max_length=20, choices=ROLES, default='DISEÑADOR')
    fecha_entrega = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    
    # Control de Horas
    horas_estimadas = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    horas_reales = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    horas_revision = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.titulo} ({self.proyecto.titulo})"

# NUEVA ENTIDAD: Historial de Revisiones / Ajustes de Artes
class Revision(models.Model):
    entregable = models.ForeignKey(Entregable, on_delete=models.CASCADE, related_name='revisiones')
    realizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    comentario = models.TextField()
    horas_adicionales = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Revisión {self.id} - {self.entregable.titulo}"