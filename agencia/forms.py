# forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Cliente, Campana, Proyecto, Creativo, Entregable, Revision


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'nombre_empresa',
            'ruc',
            'contacto_nombre',
            'email',
            'telefono',
            'presupuesto_total',
            'estado',
            'logotipo',
        ]
        widgets = {
            'nombre_empresa': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Nombre de la Empresa',
                }
            ),
            'ruc': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'RUC / Tax ID'}
            ),
            'contacto_nombre': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Nombre de Contacto',
                }
            ),
            'email': forms.EmailInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'correo@empresa.com',
                }
            ),
            'telefono': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '+593 999 999 999',
                }
            ),
            'presupuesto_total': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01'}
            ),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'logotipo': forms.FileInput(attrs={'class': 'form-control'}),
        }


class CampanaForm(forms.ModelForm):
    class Meta:
        model = Campana
        fields = [
            'cliente',
            'nombre',
            'presupuesto',
            'fecha_inicio',
            'fecha_fin',
            'estado',
        ]
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'presupuesto': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01'}
            ),
            'fecha_inicio': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'fecha_fin': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }


class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = [
            'campana',
            'titulo',
            'descripcion',
            'tipo',
            'prioridad',
            'estado',
            'horas_estimadas',
            'fecha_limite',
        ]
        widgets = {
            'campana': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'prioridad': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'horas_estimadas': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.1'}
            ),
            'fecha_limite': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
        }


class CreativoForm(forms.ModelForm):
    class Meta:
        model = Creativo
        fields = ['usuario', 'rol', 'tarifa_hora', 'estado']
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-select'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
            'tarifa_hora': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01'}
            ),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }


class EntregableForm(forms.ModelForm):
    class Meta:
        model = Entregable
        # Se remueven 'descripcion' y 'archivo_adjunto' para alinearse al modelo
        fields = [
            'proyecto',
            'creativo',
            'titulo',
            'rol_responsable',
            'estado',
            'horas_estimadas',
            'horas_reales',
            'fecha_limite',
        ]
        widgets = {
            'proyecto': forms.Select(attrs={'class': 'form-select'}),
            'creativo': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'rol_responsable': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'horas_estimadas': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.1'}
            ),
            'horas_reales': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.1'}
            ),
            'fecha_limite': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
        }


class RevisionForm(forms.ModelForm):
    class Meta:
        model = Revision
        fields = [
            'aprobado',
            'comentarios',
            'horas_adicionales',
            'archivo_anotaciones',
        ]
        widgets = {
            'aprobado': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'comentarios': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Describe los cambios solicitados u observaciones',
                }
            ),
            'horas_adicionales': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.1'}
            ),
            'archivo_anotaciones': forms.FileInput(
                attrs={'class': 'form-control'}
            ),
        }


class UsuarioEquipoForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }