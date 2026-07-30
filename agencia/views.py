import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Cliente, Campana, Proyecto, Entregable, Revision
from .forms import (
    ClienteForm, 
    CampanaForm, 
    ProyectoForm, 
    EntregableForm, 
    UsuarioEquipoForm,
    RevisionForm
)


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
# 1. DASHBOARD COMPLETO CON ANALYTICS
# ==========================================
@login_required
@solo_administrador
def dashboard(request):
    # Métricas generales
    proyectos_activos = Proyecto.objects.filter(estado__in=['NUEVO', 'EN_PROCESO', 'REVISION']).count()
    total_clientes = Cliente.objects.count()
    tareas_pendientes = Entregable.objects.filter(estado__in=['PENDIENTE', 'EN_PROCESO', 'CORRECCION']).count()
    
    # 1.1 Carga de trabajo agrupada por Diseñador y Copywriter
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

    # 1.2 Reporte de Rentabilidad por Cliente
    # Fórmula: Rentabilidad = Presupuesto - (Horas Totales Invertidas * Costo Operativo $25/h)
    COSTO_POR_HORA = Decimal('25.0')
    reporte_rentabilidad = []
    
    for cli in Cliente.objects.all():
        entregables_cliente = Entregable.objects.filter(proyecto__campana__cliente=cli)
        
        total_horas_invertidas = entregables_cliente.aggregate(Sum('horas_reales'))['horas_reales__sum'] or Decimal('0.0')
        total_horas_revision = entregables_cliente.aggregate(Sum('horas_revision'))['horas_revision__sum'] or Decimal('0.0')
        
        presupuesto = Decimal(str(cli.presupuesto_total)) if cli.presupuesto_total else Decimal('0.0')
        costo_total = (total_horas_invertidas + total_horas_revision) * COSTO_POR_HORA
        rentabilidad = presupuesto - costo_total

        reporte_rentabilidad.append({
            'cliente': cli.nombre_empresa,
            'presupuesto': presupuesto,
            'horas_invertidas': total_horas_invertidas,
            'horas_revision': total_horas_revision,
            'costo_total': costo_total,
            'rentabilidad': rentabilidad,
            'es_rentable': rentabilidad >= Decimal('0.0')
        })

    # 1.3 Horas Rebasadas en Revisiones o Estimación
    entregables_con_exceso_revision = Entregable.objects.filter(
        Q(horas_revision__gt=0) | Q(horas_reales__gt=Decimal('0.0'))
    ).select_related('proyecto', 'asignado_a')

    context = {
        'proyectos_activos': proyectos_activos,
        'total_clientes': total_clientes,
        'tareas_pendientes': tareas_pendientes,
        'carga_disenadores': carga_disenadores,
        'carga_copywriters': carga_copywriters,
        'reporte_rentabilidad': reporte_rentabilidad,
        'entregables_revision': entregables_con_exceso_revision,
    }
    return render(request, 'core/dashboard.html', context)


# ==========================================
# 2. VISTAS DE CREACIÓN Y GESTIÓN (ADMIN)
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
    return render(request, 'core/clientes.html', {'form': form, 'clientes': clientes})


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
    return render(request, 'core/campanas.html', {'form': form, 'campanas': campanas})


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
    return render(request, 'core/proyectos.html', {'form': form, 'proyectos': proyectos})


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

            messages.success(request, f'Usuario {usuario.username} creado correctamente.')
            return redirect('crear_usuario')
    else:
        form = UsuarioEquipoForm()

    usuarios = User.objects.all().order_by('-date_joined')
    return render(request, 'core/usuarios.html', {'form': form, 'usuarios': usuarios})


# ==========================================
# 3. TABLERO KANBAN
# ==========================================
@login_required
def kanban_view(request):
    es_cliente = request.user.groups.filter(name='Cliente').exists()

    if request.method == 'POST':
        form = EntregableForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Entregable guardado exitosamente.')
            return redirect('kanban')
    else:
        form = EntregableForm()

    # Si el usuario logueado es un Cliente, filtrar únicamente sus entregables
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
    return render(request, 'core/kanban.html', context)


# ==========================================
# 4. ENTIDAD REVISIONES (REGISTRO DE AJUSTES)
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

            # Sumar las horas de la revisión al acumulado del entregable y pasar a estado de Corrección
            entregable.horas_revision = Decimal(str(entregable.horas_revision)) + Decimal(str(revision.horas_adicionales))
            entregable.estado = 'CORRECCION'
            entregable.save()

            messages.success(request, 'Solicitud de revisión registrada correctamente.')
            return redirect('kanban')
    else:
        form = RevisionForm()

    return render(request, 'core/agregar_revision.html', {'form': form, 'entregable': entregable})


# ==========================================
# 5. VISTA DE CRONOGRAMA
# ==========================================
@login_required
def cronograma_view(request):
    es_cliente = request.user.groups.filter(name='Cliente').exists()

    if es_cliente:
        entregables = Entregable.objects.filter(
            proyecto__campana__cliente__usuario=request.user
        ).select_related('proyecto', 'asignado_a').order_by('fecha_entrega')
        proyectos = Proyecto.objects.filter(
            campana__cliente__usuario=request.user
        ).order_by('fecha_limite')
    else:
        entregables = Entregable.objects.select_related('proyecto', 'asignado_a').order_by('fecha_entrega')
        proyectos = Proyecto.objects.all().order_by('fecha_limite')
    
    context = {
        'entregables': entregables,
        'proyectos': proyectos,
    }
    return render(request, 'core/cronograma.html', context)


# ==========================================
# 6. APIS (JSON)
# ==========================================
@login_required
def api_eventos_entregables(request):
    es_cliente = request.user.groups.filter(name='Cliente').exists()

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
        if e.fecha_entrega:
            nombre_proyecto = getattr(e.proyecto, 'titulo', getattr(e.proyecto, 'nombre_proyecto', 'Proyecto'))
            eventos.append({
                'id': e.id,
                'title': f"{e.titulo} ({nombre_proyecto})",
                'start': e.fecha_entrega.isoformat(),
                'color': color_map.get(e.estado, '#6c757d'),
                'extendedProps': {
                    'estado': e.get_estado_display(),
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

            return JsonResponse({'status': 'success', 'nuevo_estado': entregable.estado})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'invalid method'}, status=405)


# Alias de compatibilidad
actualizar_estado_entregable = cambiar_estado_entregable