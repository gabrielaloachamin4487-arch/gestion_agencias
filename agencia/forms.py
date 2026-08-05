from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Sum
from .models import Cliente, Campana, Proyecto, Creativo, Entregable, Revision, validar_peso_archivo


class ClienteForm(forms.ModelForm):
    usuario = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="-- Sin usuario vinculado (Opcional) --"
    )

    class Meta:
        model = Cliente
        fields = [
            'nombre_empresa', 
            'ruc', 
            'contacto_nombre', 
            'email', 
            'telefono', 
            'logotipo', 
            'presupuesto_total', 
            'estado', 
            'usuario'
        ]
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la Empresa'}),
            'ruc': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RUC / Tax ID'}),
            'contacto_nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de Contacto Principal'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}),
            'logotipo': forms.FileInput(attrs={'class': 'form-control'}),
            'presupuesto_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }


class CampanaForm(forms.ModelForm):
    class Meta:
        model = Campana
        fields = ['cliente', 'nombre', 'presupuesto', 'fecha_inicio', 'fecha_fin', 'estado']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la Campaña'}),
            'presupuesto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }


class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = [
            'campana', 
            'titulo', 
            'tipo', 
            'prioridad', 
            'horas_estimadas', 
            'horas_reales', 
            'descripcion', 
            'estado', 
            'fecha_limite'
        ]
        widgets = {
            'campana': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre / Título del Proyecto'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'prioridad': forms.Select(attrs={'class': 'form-select'}),
            'horas_estimadas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'horas_reales': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'fecha_limite': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class CreativoForm(forms.ModelForm):
    class Meta:
        model = Creativo
        fields = ['usuario', 'rol', 'tarifa_hora', 'foto_perfil', 'estado']
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-select'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
            'tarifa_hora': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'foto_perfil': forms.FileInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }


class EntregableForm(forms.ModelForm):
    class Meta:
        model = Entregable
        fields = [
            'proyecto', 
            'titulo', 
            'creativo', 
            'rol_responsable', 
            'archivo', 
            'version', 
            'fecha_limite', 
            'fecha_entrega', 
            'estado', 
            'horas_estimadas', 
            'horas_reales'
        ]
        widgets = {
            'proyecto': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título de la Pieza Publicitaria'}),
            'creativo': forms.Select(attrs={'class': 'form-select'}),
            'rol_responsable': forms.Select(attrs={'class': 'form-select'}),
            'archivo': forms.FileInput(attrs={'class': 'form-control'}),
            'version': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'fecha_limite': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_entrega': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'horas_estimadas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'horas_reales': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
        }

    def clean_archivo(self):
        archivo = self.cleaned_data.get('archivo')
        if archivo:
            validar_peso_archivo(archivo)
        return archivo

    def clean(self):
        cleaned_data = super().clean()
        creativo = cleaned_data.get('creativo')
        horas_estimadas = cleaned_data.get('horas_estimadas') or 0
        nuevo_estado = cleaned_data.get('estado')

        # Validación 1: Carga máxima permitida de 40 horas semanales para el creativo
        if creativo and horas_estimadas > 0:
            entregables_activos = Entregable.objects.filter(
                creativo=creativo
            ).exclude(
                estado='APROBADO'
            )
            
            if self.instance and self.instance.pk:
                entregables_activos = entregables_activos.exclude(pk=self.instance.pk)
            
            total_horas = entregables_activos.aggregate(total=Sum('horas_estimadas'))['total'] or 0
            if (float(total_horas) + float(horas_estimadas)) > 40.0:
                raise ValidationError(
                    f"No se puede asignar el entregable a {creativo.usuario.get_full_name() or creativo.usuario.username}: "
                    f"Superaría la carga máxima permitida de 40 horas semanales estimadas (Horas actuales activas: {total_horas}h)."
                )

        # Validación 2: Una pieza solo puede pasar a estado 'APROBADO' si cuenta con al menos una revisión registrada como aprobada.
        if nuevo_estado == 'APROBADO' and self.instance and self.instance.pk:
            tiene_aprobacion = self.instance.revisiones.filter(aprobado=True).exists()
            if not tiene_aprobacion:
                raise ValidationError(
                    "Una pieza publicitaria solo puede pasar al estado 'Aprobado' si cuenta con al menos una Revisión registrada con Aprobado = True."
                )

        return cleaned_data


class UsuarioEquipoForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}), 
        required=False
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de Usuario'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo Electrónico'}),
        }


class RevisionForm(forms.ModelForm):
    class Meta:
        model = Revision
        fields = ['comentarios', 'archivo_anotaciones', 'horas_adicionales', 'aprobado']
        widgets = {
            'comentarios': forms.Textarea(
                attrs={
                    'class': 'form-control', 
                    'rows': 3, 
                    'placeholder': 'Escribe las observaciones o comentarios de revisión...'
                }
            ),
            'archivo_anotaciones': forms.FileInput(attrs={'class': 'form-control'}),
            'horas_adicionales': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.50'}),
            'aprobado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_archivo_anotaciones(self):
        archivo = self.cleaned_data.get('archivo_anotaciones')
        if archivo:
            validar_peso_archivo(archivo)
        return archivo