import io
import json
import re
import csv
import hashlib
import unicodedata
from datetime import date, datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.template.exceptions import TemplateDoesNotExist
from django.core.mail import send_mail, EmailMessage
from django.conf import settings

# Módulos para generación de PDF con ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from .models import Cliente, Campana, Proyecto, Creativo, Entregable, Revision
from .forms import (
    ClienteForm, 
    CampanaForm, 
    ProyectoForm, 
    CreativoForm,
    EntregableForm, 
    UsuarioEquipoForm,
    RevisionForm
)


def limpiar_texto_ascii(texto):
    if not texto:
        return ""
    texto_norm = unicodedata.normalize('NFD', str(texto))
    texto_ascii = "".join(c for c in texto_norm if unicodedata.category(c) != 'Mn')
    return texto_ascii


# ==========================================
# DECORADORES Y AUXILIARES DE ACCESO
# ==========================================
def solo_administrador(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_superuser or request.user.groups.filter(name='Administrador').exists() or request.user.groups.filter(name='Director de Arte').exists():
                return view_func(request, *args, **kwargs)
            else:
                messages.warning(request, "No tienes permisos de Director de Arte / PM para acceder a esta sección.")
                return redirect('kanban')
        return redirect('login')
    return wrapper_func


def verificar_alertas_retraso():
    """Envía un correo automático de alerta al Director de Arte cuando un entregable 
    ha superado su Fecha Límite y no ha sido aprobado/subido."""
    try:
        hoy = date.today()
        entregables_retrasados = Entregable.objects.filter(
            fecha_limite__lt=hoy
        ).exclude(
            estado__in=['APROBADO']
        )

        if entregables_retrasados.exists():
            directores = User.objects.filter(
                Q(is_superuser=True) | Q(groups__name='Administrador') | Q(groups__name='Director de Arte')
            ).distinct()
            
            emails_directores = [d.email for d in directores if d.email]
            if emails_directores:
                lista_titulos = "\n".join([f"- {e.titulo} (Proyecto: {e.proyecto.titulo if e.proyecto else 'N/A'}, Límite: {e.fecha_limite})" for e in entregables_retrasados[:10]])
                asunto = "ALERTA: Entregables con Infraccion de Tiempo / Retraso"
                mensaje = (
                    f"Estimado Director de Arte / PM,\n\n"
                    f"Se han detectado los siguientes entregables retrasados que superaron su fecha limite:\n\n"
                    f"{lista_titulos}\n\n"
                    f"Por favor, revisa la asignacion y carga de trabajo en la plataforma AgencyOS.\n\n"
                    f"Atentamente,\nSistema de Notificaciones AgencyOS"
                )
                try:
                    send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, emails_directores, fail_silently=True)
                except Exception:
                    pass
    except Exception:
        pass


# ==========================================
# 0. VISTA DE BIENVENIDA / LANDING PAGE
# ==========================================
def inicio(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    try:
        return render(request, 'core/inicio.html')
    except TemplateDoesNotExist:
        return render(request, 'inicio.html')


# ==========================================
# AUTENTICACIÓN: LOGIN Y LOGOUT
# ==========================================
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        
        if user is not None:
            auth_login(request, user)
            messages.success(request, f"¡Bienvenido de nuevo, {user.first_name or user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
            
    try:
        return render(request, 'core/login.html')
    except TemplateDoesNotExist:
        return render(request, 'login.html')


@csrf_exempt
@require_http_methods(["GET", "POST"])
def logout_view(request):
    auth_logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('inicio')


# ==========================================
# 1. DASHBOARD COMPLETO
# ==========================================
@login_required
def dashboard(request):
    user = request.user
    es_cliente = user.groups.filter(name='Cliente').exists() and not user.is_superuser
    es_creativo = False
    try:
        es_creativo = hasattr(user, 'perfil_creativo') and user.perfil_creativo is not None and not user.is_superuser
    except Exception:
        es_creativo = False

    try:
        verificar_alertas_retraso()
    except Exception:
        pass

    if es_cliente:
        cliente = Cliente.objects.filter(usuario=user).first()
        if not cliente and hasattr(user, 'perfil_cliente'):
            cliente = user.perfil_cliente

        if cliente:
            campanas = Campana.objects.filter(cliente=cliente)
            
            proyectos = Proyecto.objects.filter(
                Q(campana__cliente=cliente) | (Q(cliente=cliente) if hasattr(Proyecto, 'cliente') else Q())
            ).distinct()
            
            entregables = Entregable.objects.filter(
                Q(proyecto__campana__cliente=cliente) | (Q(proyecto__cliente=cliente) if hasattr(Proyecto, 'cliente') else Q())
            ).distinct()

            presupuesto_total = getattr(cliente, 'presupuesto_total', None) or Decimal('0.00')
            presupuesto_usado = campanas.aggregate(total=Sum('presupuesto'))['total'] or Decimal('0.00')

            context = {
                'es_cliente': True,
                'cliente': cliente,
                'campanas': campanas,
                'proyectos': proyectos.order_by('-id')[:5],
                'total_campanas': campanas.count(),
                'total_proyectos': proyectos.count(),
                'entregables_aprobados': entregables.filter(estado='APROBADO').count(),
                'entregables_pendientes': entregables.exclude(estado='APROBADO').count(),
                'presupuesto_total': presupuesto_total,
                'presupuesto_usado': presupuesto_usado,
            }
        else:
            context = {
                'es_cliente': True,
                'cliente': None,
                'campanas': [],
                'proyectos': [],
                'total_campanas': 0,
                'total_proyectos': 0,
                'entregables_aprobados': 0,
                'entregables_pendientes': 0,
                'presupuesto_total': Decimal('0.00'),
                'presupuesto_usado': Decimal('0.00'),
            }
    else:
        proyectos_activos = Proyecto.objects.filter(estado__in=['NUEVO', 'EN_PROCESO', 'REVISION']).count() if hasattr(Proyecto, 'estado') else Proyecto.objects.count()
        total_clientes = Cliente.objects.count()
        tareas_pendientes = Entregable.objects.exclude(estado='APROBADO').count()
        
        creativos = Creativo.objects.select_related('usuario').all()
        carga_creativos = []
        for cr in creativos:
            horas_asig = Entregable.objects.filter(
                creativo=cr
            ).exclude(
                estado='APROBADO'
            ).aggregate(total=Sum('horas_estimadas'))['total'] or Decimal('0.0')
            
            porcentaje = min(round((float(horas_asig) / 40.0) * 100, 1), 100.0)
            carga_creativos.append({
                'id': cr.id,
                'nombre': cr.usuario.get_full_name() or cr.usuario.username,
                'rol': cr.get_rol_display() if hasattr(cr, 'get_rol_display') else 'Creativo',
                'tarifa': getattr(cr, 'tarifa_hora', Decimal('0.00')),
                'horas_asignadas': float(horas_asig),
                'horas_disponibles': max(40.0 - float(horas_asig), 0.0),
                'porcentaje': porcentaje,
                'sobrecargado': float(horas_asig) > 40.0,
            })

        reporte_rentabilidad = []
        for cli in Cliente.objects.all():
            entregables_cliente = Entregable.objects.filter(
                Q(proyecto__campana__cliente=cli) | (Q(proyecto__cliente=cli) if hasattr(Proyecto, 'cliente') else Q())
            ).distinct()
            
            total_horas_reales = entregables_cliente.aggregate(total=Sum('horas_reales'))['total'] or Decimal('0.0')
            
            total_horas_rebasadas = Decimal('0.0')
            for ent in entregables_cliente:
                total_horas_rebasadas += Decimal(str(getattr(ent, 'horas_rebasadas', 0)))

            presupuesto_total = getattr(cli, 'presupuesto_total', None) or Decimal('0.0')
            COSTO_HORA_PROMEDIO = Decimal('25.0')
            costo_horas_extra = total_horas_rebasadas * COSTO_HORA_PROMEDIO
            costo_total_operativo = (total_horas_reales + total_horas_rebasadas) * COSTO_HORA_PROMEDIO
            rentabilidad = presupuesto_total - costo_total_operativo

            reporte_rentabilidad.append({
                'cliente_id': cli.id,
                'cliente': cli.nombre_empresa,
                'ruc': getattr(cli, 'ruc', 'N/A') or 'N/A',
                'presupuesto': presupuesto_total,
                'horas_reales': total_horas_reales,
                'horas_rebasadas': total_horas_rebasadas,
                'costo_horas_extra': costo_horas_extra,
                'costo_total_operativo': costo_total_operativo,
                'rentabilidad': rentabilidad,
                'es_rentable': rentabilidad >= Decimal('0.0')
            })

        context = {
            'es_cliente': False,
            'es_creativo': es_creativo,
            'proyectos_activos': proyectos_activos,
            'total_clientes': total_clientes,
            'tareas_pendientes': tareas_pendientes,
            'carga_creativos': carga_creativos,
            'reporte_rentabilidad': reporte_rentabilidad,
        }
    
    try:
        return render(request, 'core/dashboard.html', context)
    except TemplateDoesNotExist:
        return render(request, 'dashboard.html', context)


# ==========================================
# 2. VISTAS CRUD CLIENTES
# ==========================================
@login_required
@solo_administrador
def crear_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente registrado con éxito.')
            return redirect('crear_cliente')
    else:
        form = ClienteForm()
    
    clientes = Cliente.objects.all().order_by('-id')
    try:
        return render(request, 'core/clientes.html', {'form': form, 'clientes': clientes})
    except TemplateDoesNotExist:
        return render(request, 'clientes.html', {'form': form, 'clientes': clientes})


@login_required
@solo_administrador
def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == 'POST':
        form = ClienteForm(request.POST, request.FILES, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cliente "{cliente.nombre_empresa}" actualizado correctamente.')
            return redirect('crear_cliente')
    else:
        form = ClienteForm(instance=cliente)

    context = {'form': form, 'cliente': cliente}
    try:
        return render(request, 'core/editar_cliente.html', context)
    except TemplateDoesNotExist:
        return render(request, 'editar_cliente.html', context)


@login_required
@solo_administrador
def eliminar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    nombre = cliente.nombre_empresa
    if cliente.usuario:
        cliente.usuario.delete()
    cliente.delete()
    messages.success(request, f'Cliente "{nombre}" eliminado.')
    return redirect('crear_cliente')


@login_required
@solo_administrador
def enviar_reporte_pdf_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    email_destino = cliente.email or (cliente.usuario.email if cliente.usuario else None)

    if not email_destino:
        messages.error(request, f'El cliente "{cliente.nombre_empresa}" no tiene un correo electrónico registrado.')
        return redirect('crear_cliente')

    try:
        # Generar el reporte PDF en memoria
        pdf_response = generar_reporte_pdf_cliente(request, cliente_id)
        pdf_bytes = pdf_response.content

        asunto = f"Reporte de Proyectos y Estado - {cliente.nombre_empresa}"
        mensaje = (
            f"Estimado/a {cliente.contacto_nombre or cliente.nombre_empresa},\n\n"
            f"Adjunto encontrará el informe detallado del estado de sus campañas y proyectos en la plataforma AgencyOS.\n\n"
            f"Por favor, ingrese a su portal para revisar el detalle de sus entregables y revisiones.\n\n"
            f"Atentamente,\nEl Equipo de AgencyOS"
        )
        
        email = EmailMessage(
            subject=asunto,
            body=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email_destino]
        )
        email.attach(f"Reporte_{cliente.id}_AgencyOS.pdf", pdf_bytes, 'application/pdf')
        
        email.send(fail_silently=True)
        messages.success(request, f'Reporte PDF enviado exitosamente a {email_destino}.')
    except Exception as e:
        messages.warning(request, f'El proceso finalizó con aviso: {e}')

    return redirect('crear_cliente')


# ==========================================
# 3. VISTAS CRUD CAMPAÑAS Y PROYECTOS
# ==========================================
@login_required
@solo_administrador
def crear_campana(request):
    if request.method == 'POST':
        form = CampanaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Campaña creada con éxito.')
            return redirect('crear_campana')
    else:
        form = CampanaForm()

    campanas = Campana.objects.select_related('cliente').all().order_by('-id')
    try:
        return render(request, 'core/campanas.html', {'form': form, 'campanas': campanas})
    except TemplateDoesNotExist:
        return render(request, 'campanas.html', {'form': form, 'campanas': campanas})


@login_required
@solo_administrador
def crear_proyecto(request):
    if request.method == 'POST':
        form = ProyectoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Proyecto creado con éxito.')
            return redirect('crear_proyecto')
    else:
        form = ProyectoForm()

    proyectos = Proyecto.objects.select_related('campana__cliente').all().order_by('-id')
    try:
        return render(request, 'core/proyectos.html', {'form': form, 'proyectos': proyectos})
    except TemplateDoesNotExist:
        return render(request, 'proyectos.html', {'form': form, 'proyectos': proyectos})


# ==========================================
# 4. VISTAS CRUD CREATIVOS Y USUARIOS
# ==========================================
@login_required
@solo_administrador
def gestionar_creativos(request):
    if request.method == 'POST':
        form = CreativoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Creativo registrado correctamente.')
            return redirect('gestionar_creativos')
    else:
        form = CreativoForm()

    creativos = Creativo.objects.select_related('usuario').all()
    context = {'form': form, 'creativos': creativos}
    try:
        return render(request, 'core/creativos.html', context)
    except TemplateDoesNotExist:
        return render(request, 'creativos.html', context)


@login_required
@solo_administrador
def crear_usuario(request):
    group_admin, _ = Group.objects.get_or_create(name='Administrador')
    group_cliente, _ = Group.objects.get_or_create(name='Cliente')
    group_creativo, _ = Group.objects.get_or_create(name='Creativo')

    if request.method == 'POST':
        form = UsuarioEquipoForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                usuario.set_password(password)
            usuario.save()

            rol = request.POST.get('rol', 'CLIENTE')
            if rol == 'ADMINISTRADOR':
                usuario.groups.add(group_admin)
                usuario.is_staff = True
                usuario.save()
            elif rol == 'CREATIVO':
                usuario.groups.add(group_creativo)
                rol_creativo = request.POST.get('rol_creativo', 'DISEÑADOR_GRAFICO')
                Creativo.objects.get_or_create(
                    usuario=usuario,
                    defaults={'rol': rol_creativo, 'tarifa_hora': Decimal('25.00')}
                )
                messages.success(request, f'Creativo {usuario.username} registrado con perfil de {rol_creativo}.')
            else:
                usuario.groups.add(group_cliente)
                Cliente.objects.get_or_create(
                    usuario=usuario,
                    defaults={
                        'nombre_empresa': f"Empresa de {usuario.username}",
                        'contacto_nombre': f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username,
                        'email': usuario.email,
                        'presupuesto_total': Decimal('1000.00')
                    }
                )

            return redirect('crear_usuario')
    else:
        form = UsuarioEquipoForm()

    usuarios = User.objects.all().order_by('-date_joined')
    try:
        return render(request, 'core/usuarios.html', {'form': form, 'usuarios': usuarios})
    except TemplateDoesNotExist:
        return render(request, 'usuarios.html', {'form': form, 'usuarios': usuarios})


# ==========================================
# 5. TABLERO KANBAN
# ==========================================
@login_required
def kanban_view(request):
    user = request.user
    es_cliente = user.groups.filter(name='Cliente').exists() and not user.is_superuser
    es_creativo = hasattr(user, 'perfil_creativo') and user.perfil_creativo is not None and not user.is_superuser

    if request.method == 'POST':
        form = EntregableForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Entregable/Pieza guardado exitosamente.')
            return redirect('kanban')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")
    else:
        form = EntregableForm()

    if es_cliente:
        cliente = Cliente.objects.filter(usuario=user).first()
        if not cliente and hasattr(user, 'perfil_cliente'):
            cliente = user.perfil_cliente

        if cliente:
            base_qs = Entregable.objects.filter(
                Q(proyecto__campana__cliente=cliente) | (Q(proyecto__cliente=cliente) if hasattr(Proyecto, 'cliente') else Q())
            ).select_related('proyecto', 'creativo__usuario', 'creativo').distinct()
        else:
            base_qs = Entregable.objects.none()
    elif es_creativo:
        base_qs = Entregable.objects.filter(
            Q(creativo=user.perfil_creativo) | Q(asignado_a=user)
        ).select_related('proyecto', 'creativo__usuario', 'creativo').distinct()
    else:
        base_qs = Entregable.objects.all().select_related('proyecto', 'creativo__usuario', 'creativo')

    context = {
        'form': form,
        'por_iniciar': base_qs.filter(estado__in=['POR_INICIAR', 'PENDIENTE']),
        'en_proceso': base_qs.filter(estado='EN_PROCESO'),
        'en_revision': base_qs.filter(estado__in=['EN_REVISION', 'REVISION', 'CORRECCION']),
        'aprobados': base_qs.filter(estado='APROBADO'),
        'rechazados': base_qs.filter(estado='RECHAZADO'),
        'es_cliente': es_cliente,
        'es_creativo': es_creativo,
    }
    
    try:
        return render(request, 'core/kanban.html', context)
    except TemplateDoesNotExist:
        return render(request, 'kanban.html', context)


# ==========================================
# 6. REVISIONES Y REGISTRO DE OBSERVACIONES
# ==========================================
@login_required
def agregar_revision(request, entregable_id):
    entregable = get_object_or_404(Entregable, id=entregable_id)

    if request.method == 'POST':
        form = RevisionForm(request.POST, request.FILES)
        if form.is_valid():
            revision = form.save(commit=False)
            revision.entregable = entregable
            revision.revisor = request.user
            revision.realizado_por = request.user
            revision.save()

            horas_adicionales = getattr(revision, 'horas_adicionales', Decimal('0.0')) or Decimal('0.0')
            entregable.horas_revision = (getattr(entregable, 'horas_revision', Decimal('0.0')) or Decimal('0.0')) + horas_adicionales
            
            if revision.aprobado:
                entregable.estado = 'APROBADO'
                messages.success(request, f'¡La pieza "{entregable.titulo}" ha sido APROBADA con éxito!')
            else:
                entregable.estado = 'EN_REVISION'
                messages.info(request, 'Se ha registrado la solicitud de ajuste/corrección.')
            
            entregable.save()
            return redirect('kanban')
    else:
        form = RevisionForm()

    try:
        return render(request, 'core/agregar_revision.html', {'form': form, 'entregable': entregable})
    except TemplateDoesNotExist:
        return render(request, 'agregar_revision.html', {'form': form, 'entregable': entregable})


# ==========================================
# 7. CRONOGRAMA INTERACTIVO
# ==========================================
@login_required
def cronograma_view(request):
    es_cliente = request.user.groups.filter(name='Cliente').exists() and not request.user.is_superuser
    clientes = Cliente.objects.all()
    campanas = Campana.objects.all()

    if es_cliente:
        cliente_obj = Cliente.objects.filter(usuario=request.user).first()
        if cliente_obj:
            campanas = campanas.filter(cliente=cliente_obj)
            clientes = clientes.filter(id=cliente_obj.id)

    context = {
        'clientes': clientes,
        'campanas': campanas,
    }
    try:
        return render(request, 'core/cronograma.html', context)
    except TemplateDoesNotExist:
        return render(request, 'cronograma.html', context)


# ==========================================
# 8. APIS Y AJAX
# ==========================================
@login_required
def api_eventos_entregables(request):
    es_cliente = request.user.groups.filter(name='Cliente').exists() and not request.user.is_superuser
    cliente_id = request.GET.get('cliente_id')
    campana_id = request.GET.get('campana_id')

    if es_cliente:
        cliente_obj = Cliente.objects.filter(usuario=request.user).first()
        entregables = Entregable.objects.filter(
            Q(proyecto__campana__cliente=cliente_obj) | (Q(proyecto__cliente=cliente_obj) if hasattr(Proyecto, 'cliente') else Q())
        ).distinct() if cliente_obj else Entregable.objects.none()
    else:
        entregables = Entregable.objects.all()

    if cliente_id:
        entregables = entregables.filter(
            Q(proyecto__campana__cliente_id=cliente_id) | (Q(proyecto__cliente_id=cliente_id) if hasattr(Proyecto, 'cliente') else Q())
        )
    if campana_id:
        entregables = entregables.filter(proyecto__campana_id=campana_id)

    entregables = entregables.select_related('proyecto__campana__cliente', 'creativo__usuario')

    eventos = []
    color_map = {
        'POR_INICIAR': '#6c757d',
        'PENDIENTE': '#ffc107',
        'EN_PROCESO': '#17a2b8',
        'EN_REVISION': '#fd7e14',
        'CORRECCION': '#dc3545',
        'APROBADO': '#28a745',
        'RECHAZADO': '#6f42c1',
    }

    for e in entregables:
        fecha_target = getattr(e, 'fecha_limite', None) or getattr(e, 'fecha_entrega', None)
        if fecha_target:
            nombre_proyecto = e.proyecto.titulo if e.proyecto else 'Sin proyecto'
            titulo_entregable = e.titulo
            cliente_nombre = 'N/A'
            campana_nombre = 'N/A'
            if e.proyecto and e.proyecto.campana and e.proyecto.campana.cliente:
                cliente_nombre = e.proyecto.campana.cliente.nombre_empresa
                campana_nombre = e.proyecto.campana.nombre

            eventos.append({
                'id': e.id,
                'title': f"{titulo_entregable} ({nombre_proyecto})",
                'start': fecha_target.isoformat(),
                'color': color_map.get(e.estado, '#6c757d'),
                'extendedProps': {
                    'estado': e.get_estado_display(),
                    'cliente': cliente_nombre,
                    'campana': campana_nombre,
                    'creativo': e.creativo.usuario.get_full_name() if e.creativo else 'Sin asignar',
                    'horas_estimadas': float(e.horas_estimadas),
                }
            })

    return JsonResponse(eventos, safe=False)


@csrf_exempt
@login_required
def cambiar_estado_entregable(request, entregable_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nuevo_estado = data.get('estado')
            
            entregable = get_object_or_404(Entregable, id=entregable_id)
            
            if nuevo_estado == 'APROBADO':
                tiene_aprobacion = entregable.revisiones.filter(aprobado=True).exists()
                if not tiene_aprobacion:
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'No se puede aprobar la pieza sin antes contar con al menos una Revisión aprobada registrada por el cliente o revisor.'
                    }, status=400)

            entregable.estado = nuevo_estado
            entregable.save()

            if nuevo_estado in ['EN_REVISION', 'REVISION']:
                cliente_user = None
                if entregable.proyecto and entregable.proyecto.campana and entregable.proyecto.campana.cliente:
                    cliente_user = entregable.proyecto.campana.cliente.usuario

                if cliente_user and cliente_user.email:
                    titulo_limpio = limpiar_texto_ascii(entregable.titulo)
                    nombre_user_limpio = limpiar_texto_ascii(cliente_user.first_name or cliente_user.username)
                    asunto = f"Notificación de Entrega para Revisión: {titulo_limpio}"
                    mensaje = (
                        f"Hola {nombre_user_limpio},\n\n"
                        f"La pieza publicitaria '{titulo_limpio}' ha sido subida y cambiada al estado EN REVISION.\n"
                        f"Por favor ingresa a tu portal para revisar las observaciones, adjuntos y aprobar el arte.\n\n"
                        f"Atentamente,\nEl Equipo de AgencyOS"
                    )
                    try:
                        send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [cliente_user.email], fail_silently=True)
                    except Exception:
                        pass

            return JsonResponse({'status': 'success', 'nuevo_estado': entregable.estado})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'invalid method'}, status=405)


# ==========================================
# 9. EXPORTACIÓN Y GENERACIÓN DE PDF
# ==========================================
@login_required
@solo_administrador
def exportar_rentabilidad_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="Reporte_Rentabilidad_{date.today().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID Cliente', 
        'Empresa', 
        'RUC / Tax ID', 
        'Presupuesto Contratado ($)', 
        'Horas Reales Consumidas', 
        'Horas Rebasadas (>3 Revisiones)', 
        'Costo Horas Extras ($)', 
        'Costo Operativo Total ($)', 
        'Rentabilidad Neta ($)', 
        'Estado Rentable'
    ])

    COSTO_HORA = Decimal('25.0')
    for cli in Cliente.objects.all():
        entregables = Entregable.objects.filter(
            Q(proyecto__campana__cliente=cli) | (Q(proyecto__cliente=cli) if hasattr(Proyecto, 'cliente') else Q())
        ).distinct()
        
        total_horas_reales = entregables.aggregate(total=Sum('horas_reales'))['total'] or Decimal('0.0')
        
        total_horas_rebasadas = Decimal('0.0')
        for ent in entregables:
            total_horas_rebasadas += Decimal(str(getattr(ent, 'horas_rebasadas', 0)))

        presupuesto = getattr(cli, 'presupuesto_total', None) or Decimal('0.0')
        costo_extra = total_horas_rebasadas * COSTO_HORA
        costo_total = (total_horas_reales + total_horas_rebasadas) * COSTO_HORA
        rentabilidad = presupuesto - costo_total

        writer.writerow([
            cli.id,
            cli.nombre_empresa,
            getattr(cli, 'ruc', 'N/A') or 'N/A',
            f"{presupuesto:.2f}",
            f"{total_horas_reales:.2f}",
            f"{total_horas_rebasadas:.2f}",
            f"{costo_extra:.2f}",
            f"{costo_total:.2f}",
            f"{rentabilidad:.2f}",
            'RENTABLE' if rentabilidad >= Decimal('0.0') else 'DÉFICIT'
        ])

    return response


@login_required
def generar_reporte_pdf_cliente(request, cliente_id):
    """Genera y devuelve un reporte institucional en PDF para un cliente específico."""
    cliente = get_object_or_404(Cliente, id=cliente_id)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        rightMargin=36, 
        leftMargin=36, 
        topMargin=36, 
        bottomMargin=36
    )
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#0f172a'), spaceAfter=4)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#475569'), spaceAfter=12)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor('#1e293b'), spaceBefore=10, spaceAfter=8)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#334155'))
    cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#0f172a'), fontName='Helvetica-Bold')

    story.append(Paragraph("<b>REPORTE INSTITUCIONAL DE CLIENTE</b>", title_style))
    story.append(Paragraph(f"<b>AgencyOS Platform</b> | Generado el: {date.today().strftime('%d/%m/%Y')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=12))

    # Información general del cliente
    datos_cliente = [
        [Paragraph("<b>Empresa:</b>", cell_bold), Paragraph(cliente.nombre_empresa, cell_style), Paragraph("<b>Contacto:</b>", cell_bold), Paragraph(cliente.contacto_nombre or "N/A", cell_style)],
        [Paragraph("<b>RUC / Tax ID:</b>", cell_bold), Paragraph(getattr(cliente, 'ruc', 'N/A') or 'N/A', cell_style), Paragraph("<b>Email:</b>", cell_bold), Paragraph(cliente.email or "N/A", cell_style)],
        [Paragraph("<b>Presupuesto Total:</b>", cell_bold), Paragraph(f"${getattr(cliente, 'presupuesto_total', Decimal('0.00')):.2f}", cell_style), Paragraph("<b>Teléfono:</b>", cell_bold), Paragraph(cliente.telefono or "N/A", cell_style)],
    ]
    t_cliente = Table(datos_cliente, colWidths=[100, 170, 80, 190])
    t_cliente.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
    ]))
    story.append(t_cliente)
    story.append(Spacer(1, 14))

    # Proyectos y Entregables del Cliente
    story.append(Paragraph("<b>Resumen de Proyectos y Piezas Registradas</b>", section_style))
    
    proyectos = Proyecto.objects.filter(
        Q(campana__cliente=cliente) | (Q(cliente=cliente) if hasattr(Proyecto, 'cliente') else Q())
    ).distinct()

    tabla_datos = [[
        Paragraph("<b>Proyecto / Pieza</b>", cell_bold),
        Paragraph("<b>Estado</b>", cell_bold),
        Paragraph("<b>Hrs. Est.</b>", cell_bold),
        Paragraph("<b>Hrs. Reales</b>", cell_bold),
        Paragraph("<b>Fecha Límite</b>", cell_bold)
    ]]

    entregables_total = Entregable.objects.filter(
        Q(proyecto__campana__cliente=cliente) | (Q(proyecto__cliente=cliente) if hasattr(Proyecto, 'cliente') else Q())
    ).distinct()

    if entregables_total.exists():
        for ent in entregables_total:
            fecha_str = ent.fecha_limite.strftime('%d/%m/%Y') if getattr(ent, 'fecha_limite', None) else 'N/A'
            tabla_datos.append([
                Paragraph(ent.titulo, cell_style),
                Paragraph(ent.get_estado_display(), cell_style),
                Paragraph(f"{ent.horas_estimadas:.1f}", cell_style),
                Paragraph(f"{ent.horas_reales:.1f}", cell_style),
                Paragraph(fecha_str, cell_style)
            ])
    else:
        tabla_datos.append([Paragraph("No hay entregables o piezas registradas.", cell_style), "", "", "", ""])

    t_proyectos = Table(tabla_datos, colWidths=[180, 110, 70, 70, 110])
    t_proyectos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(t_proyectos)

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Reporte_{cliente.nombre_empresa}_{date.today().strftime("%Y%m%d")}.pdf"'
    return response