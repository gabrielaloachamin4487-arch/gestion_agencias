from django import forms
from django.contrib.auth.models import User
from .models import Cliente, Campana, Proyecto, Entregable, Revision


class ClienteForm(forms.ModelForm):
    # Campo opcional para vincular una cuenta de usuario al cliente
    usuario = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="-- Sin usuario vinculado (Opcional) --"
    )

    class Meta:
        model = Cliente
        # Se agrega 'usuario' a la lista para que se guarde el vínculo
        fields = ['nombre_empresa', 'contacto_nombre', 'email', 'telefono', 'presupuesto_total', 'usuario']
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la Empresa'}),
            'contacto_nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de Contacto'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}),
            'presupuesto_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class CampanaForm(forms.ModelForm):
    class Meta:
        model = Campana
        fields = ['cliente', 'nombre', 'presupuesto', 'fecha_inicio', 'fecha_fin']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la Campaña'}),
            'presupuesto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['campana', 'titulo', 'descripcion', 'estado', 'fecha_limite']
        widgets = {
            'campana': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título del Proyecto'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'fecha_limite': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class EntregableForm(forms.ModelForm):
    # Selector de usuario responsable del entregable
    asignado_a = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="-- Seleccionar Responsable --"
    )

    class Meta:
        model = Entregable
        fields = [
            'proyecto', 
            'titulo', 
            'asignado_a', 
            'rol_responsable', 
            'fecha_entrega', 
            'estado', 
            'horas_estimadas', 
            'horas_reales'
        ]
        widgets = {
            'proyecto': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título del Arte/Entregable'}),
            'rol_responsable': forms.Select(attrs={'class': 'form-select'}),
            'fecha_entrega': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'horas_estimadas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'horas_reales': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
        }


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
        fields = ['comentario', 'horas_adicionales']
        widgets = {
            'comentario': forms.Textarea(
                attrs={
                    'class': 'form-control', 
                    'rows': 3, 
                    'placeholder': 'Escribe las observaciones o solicitud de corrección del cliente...'
                }
            ),
            'horas_adicionales': forms.NumberInput(
                attrs={
                    'class': 'form-control', 
                    'step': '0.50'
                }
            ),
        }