import io
import json
import re
import unicodedata
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.template.exceptions import TemplateDoesNotExist
from django.core.mail import send_mail, EmailMessage
from django.conf import settings

# Módulos para generación de PDF con ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from .models import Cliente, Campana, Proyecto, Entregable, Revision
from .forms import (
    ClienteForm, 
    CampanaForm, 
    ProyectoForm, 
    EntregableForm, 
    UsuarioEquipoForm,
    RevisionForm
)


# Función auxiliar para eliminar caracteres especiales y acentos
def limpiar_texto_ascii(texto):
    if not texto:
        return ""
    texto_norm = unicodedata.normalize('NFD', str(texto))
    texto_ascii = "".join(c for c in texto_norm if unicodedata.category(c) != 'Mn')
    return texto_ascii


# ==========================================
# 0. VISTA DE BIENVENIDA / LANDING PAGE
# ==========================================
def inicio(request):
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Cliente').exists() and not request.user.is_superuser:
            return redirect('dashboard')
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
        if request.user.groups.filter(name='Cliente').exists() and not request.user.is_superuser:
            return redirect('dashboard')
        return redirect('dashboard')
        
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        
        if user is not None:
            auth_login(request, user)
            if user.groups.filter(name='Cliente').exists() and not user.is_superuser:
                messages.success(request, f"¡Bienvenido de nuevo, {user.first_name or user.username}!")
                return redirect('dashboard')
            else:
                messages.success(request, f"Panel de Control - Bienvenido Administrador {user.username}")
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
# DECORADOR PERSONALIZADO PARA ADMINISTRADOR
# ==========================================
def solo_administrador(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_superuser or request.user.groups.filter(name='Administrador').exists():
                return view_func(request, *args, **kwargs)
            else:
                messages.warning(request, "No tienes permisos de Administrador para acceder a esta sección.")
                return redirect('kanban')
        return redirect('login')
    return wrapper_func


# ==========================================
# 1. DASHBOARD COMPLETO CON ANALYTICS Y VISTA CLIENTE
# ==========================================
@login_required
def dashboard(request):
    user = request.user
    es_cliente = user.groups.filter(name='Cliente').exists() and not user.is_superuser

    if es_cliente:
        # Obtener el cliente vinculado al usuario actual
        cliente = Cliente.objects.filter(usuario=user).first()
        if not cliente and hasattr(user, 'perfil_cliente'):
            cliente = user.perfil_cliente

        if cliente:
            campanas = Campana.objects.filter(cliente=cliente)
            proyectos = Proyecto.objects.filter(campana__cliente=cliente)
            entregables = Entregable.objects.filter(proyecto__campana__cliente=cliente)

            presupuesto_total = getattr(cliente, 'presupuesto_total', Decimal('0.00')) or Decimal('0.00')
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
        # Vista Administrador / Staff
        proyectos_activos = Proyecto.objects.filter(estado__in=['NUEVO', 'EN_PROCESO', 'REVISION']).count() if hasattr(Proyecto, 'estado') else Proyecto.objects.count()
        total_clientes = Cliente.objects.count()
        tareas_pendientes = Entregable.objects.filter(estado__in=['PENDIENTE', 'EN_PROCESO', 'CORRECCION']).count()
        
        carga_disenadores = Entregable.objects.filter(
            rol_responsable='DISEÑADOR'
        ).exclude(
            estado='APROBADO'
        ).values(
            'asignado_a__username', 'asignado_a__first_name', 'asignado_a__last_name'
        ).annotate(
            total_tareas=Count('id'),
            horas_totales=Sum('horas_estimadas')
        )

        carga_copywriters = Entregable.objects.filter(
            rol_responsable='COPYWRITER'
        ).exclude(
            estado='APROBADO'
        ).values(
            'asignado_a__username', 'asignado_a__first_name', 'asignado_a__last_name'
        ).annotate(
            total_tareas=Count('id'),
            horas_totales=Sum('horas_estimadas')
        )

        COSTO_POR_HORA = Decimal('25.0')
        reporte_rentabilidad = []
        
        for cli in Cliente.objects.all():
            entregables_cliente = Entregable.objects.filter(
                proyecto__campana__cliente=cli
            )
            
            total_horas_invertidas = entregables_cliente.aggregate(Sum('horas_reales'))['horas_reales__sum'] or Decimal('0.0')
            total_horas_revision = entregables_cliente.aggregate(Sum('horas_revision'))['horas_revision__sum'] or Decimal('0.0')
            
            presupuesto = Decimal(str(cli.presupuesto_total)) if hasattr(cli, 'presupuesto_total') and cli.presupuesto_total else Decimal('0.0')
            costo_total = (total_horas_invertidas + total_horas_revision) * COSTO_POR_HORA
            rentabilidad = presupuesto - costo_total

            reporte_rentabilidad.append({
                'cliente': getattr(cli, 'nombre_empresa', str(cli)),
                'presupuesto': presupuesto,
                'horas_invertidas': total_horas_invertidas,
                'horas_revision': total_horas_revision,
                'costo_total': costo_total,
                'rentabilidad': rentabilidad,
                'es_rentable': rentabilidad >= Decimal('0.0')
            })

        entregables_con_exceso_revision = Entregable.objects.filter(
            Q(horas_revision__gt=0) | Q(horas_reales__gt=Decimal('0.0'))
        ).select_related('proyecto', 'asignado_a')

        context = {
            'es_cliente': False,
            'proyectos_activos': proyectos_activos,
            'total_clientes': total_clientes,
            'tareas_pendientes': tareas_pendientes,
            'carga_disenadores': carga_disenadores,
            'carga_copywriters': carga_copywriters,
            'reporte_rentabilidad': reporte_rentabilidad,
            'entregables_revision': entregables_con_exceso_revision,
        }
    
    try:
        return render(request, 'core/dashboard.html', context)
    except TemplateDoesNotExist:
        return render(request, 'dashboard.html', context)


# ==========================================
# 2. VISTAS DE CLIENTES (CREAR, EDITAR, ELIMINAR CON CASCADA)
# ==========================================
@login_required
@solo_administrador
def crear_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
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
    """Permite editar los datos de un cliente existente."""
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cliente "{cliente.nombre_empresa}" actualizado correctamente.')
            return redirect('crear_cliente')
    else:
        form = ClienteForm(instance=cliente)

    try:
        return render(request, 'core/editar_cliente.html', {'form': form, 'cliente': cliente})
    except TemplateDoesNotExist:
        return render(request, 'editar_cliente.html', {'form': form, 'cliente': cliente})


@login_required
@solo_administrador
def eliminar_cliente(request, cliente_id):
    """Elimina el cliente y en cascada borra sus campañas, proyectos y entregables vinculados."""
    cliente = get_object_or_404(Cliente, id=cliente_id)
    nombre = cliente.nombre_empresa
    
    Campana.objects.filter(cliente=cliente).delete()
    
    if cliente.usuario:
        cliente.usuario.delete()
        
    cliente.delete()
    messages.success(request, f'Cliente "{nombre}" y todo su historial de campañas, proyectos y tareas fueron eliminados.')
    return redirect('crear_cliente')


# ==========================================
# 3. OTRAS VISTAS DE CREACIÓN
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


@login_required
@solo_administrador
def crear_usuario(request):
    group_admin, _ = Group.objects.get_or_create(name='Administrador')
    group_cliente, _ = Group.objects.get_or_create(name='Cliente')

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

                if usuario.email:
                    nombre_limpio = limpiar_texto_ascii(usuario.first_name or usuario.username)
                    asunto = "Accesos a tu panel de cliente - AgencyOS"
                    mensaje = (
                        f"Hola {nombre_limpio},\n\n"
                        f"Tu cuenta de Cliente ha sido creada correctamente.\n\n"
                        f"Detalles de acceso:\n"
                        f"- Usuario: {usuario.username}\n"
                        f"- Panel de Control: https://gestion-agencias.onrender.com/login/\n\n"
                        f"Desde el panel podras ver tus tableros, cronogramas y aprobar avances.\n\n"
                        f"Atentamente,\nEl Equipo de la Agencia."
                    )
                    try:
                        send_mail(
                            asunto,
                            mensaje,
                            settings.DEFAULT_FROM_EMAIL,
                            [usuario.email],
                            fail_silently=False
                        )
                        messages.success(request, f'Usuario {usuario.username} registrado. ¡Correo enviado a {usuario.email}!')
                    except Exception as e:
                        messages.warning(request, f'Usuario creado, pero no se pudo enviar el correo: {e}')

            return redirect('crear_usuario')
    else:
        form = UsuarioEquipoForm()

    usuarios = User.objects.all().order_by('-date_joined')
    try:
        return render(request, 'core/usuarios.html', {'form': form, 'usuarios': usuarios})
    except TemplateDoesNotExist:
        return render(request, 'usuarios.html', {'form': form, 'usuarios': usuarios})


# ==========================================
# 4. ENVÍO DE REPORTES PDF POR CORREO
# ==========================================
@login_required
@solo_administrador
def enviar_reporte_pdf_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    destino_email = cliente.email or (cliente.usuario.email if cliente.usuario and cliente.usuario.email else None)

    if not destino_email:
        messages.error(request, f"El cliente '{cliente.nombre_empresa}' no tiene un correo asignado.")
        return redirect('crear_cliente')

    empresa_limpia = limpiar_texto_ascii(cliente.nombre_empresa)
    contacto_limpio = limpiar_texto_ascii(cliente.contacto_nombre or cliente.nombre_empresa)

    campanas_ids = Campana.objects.filter(cliente=cliente).values_list('id', flat=True)
    proyectos = Proyecto.objects.filter(campana__in=campanas_ids).distinct()

    entregables = Entregable.objects.filter(
        Q(proyecto__in=proyectos) | Q(proyecto__campana__cliente=cliente)
    ).select_related('proyecto').distinct()

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

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#0f172a'), spaceAfter=6)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#475569'), spaceAfter=12)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor('#1e293b'), spaceBefore=10, spaceAfter=8)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#334155'))
    cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#0f172a'), fontName='Helvetica-Bold')

    story.append(Paragraph("<b>REPORTE OFICIAL DE ESTADO DE PROYECTOS</b>", title_style))
    story.append(Paragraph(f"<b>Cliente:</b> {empresa_limpia} &nbsp;|&nbsp; <b>Contacto:</b> {contacto_limpio} &nbsp;|&nbsp; <b>Sistema:</b> AgencyOS", subtitle_style))
    story.append(Spacer(1, 5))

    story.append(Paragraph("<b>1. Resumen de Proyectos</b>", section_style))
    data_proyectos = [["Nombre del Proyecto", "Campaña", "Estado / Descripción"]]

    for proy in proyectos:
        nombre_p = Paragraph(limpiar_texto_ascii(getattr(proy, 'titulo', getattr(proy, 'nombre_proyecto', getattr(proy, 'nombre', str(proy))))), cell_bold)
        campana_p = Paragraph(limpiar_texto_ascii(str(proy.campana)) if hasattr(proy, 'campana') and proy.campana else "General", cell_style)
        estado_p = Paragraph(limpiar_texto_ascii(proy.get_estado_display() if hasattr(proy, 'get_estado_display') else getattr(proy, 'estado', 'Activo')), cell_style)
        data_proyectos.append([nombre_p, campana_p, estado_p])

    if len(data_proyectos) == 1:
        data_proyectos.append([Paragraph("Sin proyectos asignados", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style)])

    t_proyectos = Table(data_proyectos, colWidths=[200, 160, 170])
    t_proyectos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_proyectos)
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>2. Detalle de Entregables</b>", section_style))
    data_entregables = [["Proyecto", "Entregable / Tarea", "Estado", "Fecha Entrega"]]

    for item in entregables:
        nombre_proy = Paragraph(limpiar_texto_ascii(getattr(item.proyecto, 'titulo', getattr(item.proyecto, 'nombre_proyecto', getattr(item.proyecto, 'nombre', str(item.proyecto))))), cell_bold)
        titulo_ent = Paragraph(limpiar_texto_ascii(getattr(item, 'titulo', getattr(item, 'nombre', 'Entregable'))), cell_style)
        estado_ent = Paragraph(limpiar_texto_ascii(item.get_estado_display() if hasattr(item, 'get_estado_display') else item.estado), cell_style)
        fecha_ent = Paragraph(item.fecha_entrega.strftime('%d/%m/%Y') if hasattr(item, 'fecha_entrega') and item.fecha_entrega else 'Pendiente', cell_style)
        
        data_entregables.append([nombre_proy, titulo_ent, estado_ent, fecha_ent])

    if len(data_entregables) == 1:
        data_entregables.append([Paragraph("Sin entregables registrados", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style)])

    t_entregables = Table(data_entregables, colWidths=[150, 180, 100, 100])
    t_entregables.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_entregables)

    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()

    slug_empresa = re.sub(r'[^a-zA-Z0-9_]', '_', empresa_limpia)
    nombre_archivo_adjunto = f"Reporte_{slug_empresa}.pdf"

    asunto_texto = f"Reporte de Avances - {empresa_limpia}"
    cuerpo = (
        f"Hola {contacto_limpio},\n\n"
        f"Adjunto a este correo encontraras el reporte actualizado en PDF con el estado de tus proyectos y entregables.\n\n"
        f"Atentamente,\nEl Equipo de AgencyOS."
    )

    try:
        email = EmailMessage(
            subject=asunto_texto,
            body=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destino_email],
        )
        email.attach(nombre_archivo_adjunto, pdf_data, 'application/pdf')
        email.send(fail_silently=False)

        messages.success(request, f"¡Reporte PDF enviado con éxito a {destino_email}!")
    except Exception as e:
        messages.error(request, f"Ocurrió un error al enviar el correo: {e}")

    return redirect('crear_cliente')


# ==========================================
# 5. TABLERO KANBAN
# ==========================================
@login_required
def kanban_view(request):
    es_cliente = request.user.groups.filter(name='Cliente').exists() and not request.user.is_superuser

    if request.method == 'POST':
        form = EntregableForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Entregable guardado exitosamente.')
            return redirect('kanban')
    else:
        form = EntregableForm()

    if es_cliente:
        base_qs = Entregable.objects.filter(
            proyecto__campana__cliente__usuario=request.user
        ).select_related('proyecto', 'asignado_a')
    else:
        base_qs = Entregable.objects.all().select_related('proyecto', 'asignado_a')

    context = {
        'form': form,
        'pendientes': base_qs.filter(estado='PENDIENTE'),
        'en_proceso': base_qs.filter(estado='EN_PROCESO'),
        'correccion': base_qs.filter(estado='CORRECCION'),
        'aprobados': base_qs.filter(estado='APROBADO'),
        'es_cliente': es_cliente,
    }
    
    try:
        return render(request, 'core/kanban.html', context)
    except TemplateDoesNotExist:
        return render(request, 'kanban.html', context)


# ==========================================
# 6. ENTIDAD REVISIONES (REGISTRO DE AJUSTES)
# ==========================================
@login_required
def agregar_revision(request, entregable_id):
    entregable = get_object_or_404(Entregable, id=entregable_id)

    if request.method == 'POST':
        form = RevisionForm(request.POST)
        if form.is_valid():
            revision = form.save(commit=False)
            revision.entregable = entregable
            revision.realizado_por = request.user
            revision.save()

            horas_actuales = Decimal(str(entregable.horas_revision or 0))
            horas_adicionales = Decimal(str(getattr(revision, 'horas_adicionales', 0) or 0))
            
            entregable.horas_revision = horas_actuales + horas_adicionales
            entregable.estado = 'CORRECCION'
            entregable.save()

            messages.success(request, 'Solicitud de revisión registrada correctamente.')
            return redirect('kanban')
    else:
        form = RevisionForm()

    try:
        return render(request, 'core/agregar_revision.html', {'form': form, 'entregable': entregable})
    except TemplateDoesNotExist:
        return render(request, 'agregar_revision.html', {'form': form, 'entregable': entregable})


# ==========================================
# 7. VISTA DE CRONOGRAMA
# ==========================================
@login_required
def cronograma_view(request):
    es_cliente = request.user.groups.filter(name='Cliente').exists() and not request.user.is_superuser

    if es_cliente:
        entregables = Entregable.objects.filter(
            proyecto__campana__cliente__usuario=request.user
        ).select_related('proyecto', 'asignado_a').order_by('fecha_entrega')
        proyectos = Proyecto.objects.filter(
            campana__cliente__usuario=request.user
        ).order_by('fecha_limite') if hasattr(Proyecto, 'fecha_limite') else Proyecto.objects.none()
    else:
        entregables = Entregable.objects.select_related('proyecto', 'asignado_a').order_by('fecha_entrega')
        proyectos = Proyecto.objects.all().order_by('fecha_limite') if hasattr(Proyecto, 'fecha_limite') else Proyecto.objects.all()
    
    context = {
        'entregables': entregables,
        'proyectos': proyectos,
    }
    
    try:
        return render(request, 'core/cronograma.html', context)
    except TemplateDoesNotExist:
        return render(request, 'cronograma.html', context)


# ==========================================
# 8. APIS (JSON)
# ==========================================
@login_required
def api_eventos_entregables(request):
    es_cliente = request.user.groups.filter(name='Cliente').exists() and not request.user.is_superuser

    if es_cliente:
        entregables = Entregable.objects.filter(
            proyecto__campana__cliente__usuario=request.user
        ).select_related('proyecto', 'asignado_a')
    else:
        entregables = Entregable.objects.select_related('proyecto', 'asignado_a').all()

    eventos = []
    color_map = {
        'PENDIENTE': '#ffc107',
        'EN_PROCESO': '#17a2b8',
        'CORRECCION': '#dc3545',
        'APROBADO': '#28a745',
    }

    for e in entregables:
        if hasattr(e, 'fecha_entrega') and e.fecha_entrega:
            nombre_proyecto = getattr(e.proyecto, 'titulo', getattr(e.proyecto, 'nombre_proyecto', 'Proyecto'))
            titulo_entregable = getattr(e, 'titulo', getattr(e, 'nombre', 'Entregable'))
            eventos.append({
                'id': e.id,
                'title': f"{titulo_entregable} ({nombre_proyecto})",
                'start': e.fecha_entrega.isoformat(),
                'color': color_map.get(e.estado, '#6c757d'),
                'extendedProps': {
                    'estado': e.get_estado_display() if hasattr(e, 'get_estado_display') else e.estado,
                    'responsable': e.asignado_a.username if e.asignado_a else 'Sin asignar',
                    'rol': getattr(e, 'rol_responsable', 'Sin Rol'),
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
            entregable.estado = nuevo_estado
            entregable.save()

            if nuevo_estado == 'REVISION':
                cliente_user = getattr(getattr(getattr(entregable, 'proyecto', None), 'campana', None), 'cliente', None)
                if cliente_user:
                    cliente_user = getattr(cliente_user, 'usuario', None)
                if cliente_user and cliente_user.email:
                    titulo_limpio = limpiar_texto_ascii(getattr(entregable, 'titulo', 'Entregable'))
                    nombre_user_limpio = limpiar_texto_ascii(cliente_user.first_name or cliente_user.username)
                    try:
                        send_mail(
                            f"Avance listo para revision: {titulo_limpio}",
                            f"Hola {nombre_user_limpio},\n\nEl entregable esta listo para tu aprobacion.",
                            settings.DEFAULT_FROM_EMAIL,
                            [cliente_user.email],
                            fail_silently=True
                        )
                    except Exception:
                        pass

            return JsonResponse({'status': 'success', 'nuevo_estado': entregable.estado})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'invalid method'}, status=405)


# Alias de compatibilidad
actualizar_estado_entregable = cambiar_estado_entregable