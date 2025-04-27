from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponse, FileResponse
from django.db.models import Sum, Count
from django.utils import timezone
from django.core.paginator import Paginator
import os
import zipfile
from io import BytesIO
import tempfile
import shutil
from .models import (
    Departamento, Funcionario, CategoriasDespesa, 
    Despesa, SolicitacaoReembolso, Pagamento, RelatorioFinanceiro
)
from .forms import (
    UserRegistrationForm, FuncionarioForm, DespesaForm, 
    SolicitacaoReembolsoForm, AprovarSolicitacaoForm, PagamentoForm,
    RelatorioFinanceiroForm, DespesaPeriodoForm
)
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

# Páginas Gerais
def home(request):
    return render(request, 'despesas/home.html')

@login_required
def dashboard(request):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    # Resumo das despesas do usuário
    despesas = Despesa.objects.filter(funcionario=funcionario)
    total_despesas = despesas.count()
    valor_total = despesas.aggregate(total=Sum('valor'))['total'] or 0
    
    # Despesas por status
    despesas_por_status = {
        'rascunho': despesas.filter(status='RASCUNHO').count(),
        'enviadas': despesas.filter(status='ENVIADA').count(),
        'aprovadas': despesas.filter(status='APROVADA').count(),
        'negadas': despesas.filter(status='NEGADA').count(),
        'pagas': despesas.filter(status='PAGA').count(),
    }
    
    # Despesas por categoria
    despesas_por_categoria = list(despesas.values('categoria__nome').annotate(
        total=Count('id')).order_by('-total')[:5])
    
    # Despesas recentes
    despesas_recentes = despesas.order_by('-data_criacao')[:5]
    
    # Solicitações de reembolso
    solicitacoes = SolicitacaoReembolso.objects.filter(funcionario=funcionario)
    total_solicitacoes = solicitacoes.count()
    solicitacoes_recentes = solicitacoes.order_by('-data_solicitacao')[:5]
    
    # Para gerentes: solicitações pendentes para aprovação
    aprovacoes_pendentes = None
    if funcionario.is_gerente():
        aprovacoes_pendentes = SolicitacaoReembolso.objects.filter(
            status='PENDENTE', 
            funcionario__departamento=funcionario.departamento
        ).exclude(funcionario=funcionario).count()
    
    # Para financeiro: solicitações aprovadas pendentes de pagamento
    pagamentos_pendentes = None
    if funcionario.is_financeiro():
        pagamentos_pendentes = SolicitacaoReembolso.objects.filter(
            status='APROVADA'
        ).count()
    
    context = {
        'total_despesas': total_despesas,
        'valor_total': valor_total,
        'despesas_por_status': despesas_por_status,
        'despesas_por_categoria': despesas_por_categoria,
        'despesas_recentes': despesas_recentes,
        'total_solicitacoes': total_solicitacoes,
        'solicitacoes_recentes': solicitacoes_recentes,
        'aprovacoes_pendentes': aprovacoes_pendentes,
        'pagamentos_pendentes': pagamentos_pendentes,
    }
    
    return render(request, 'despesas/dashboard.html', context)

# Autenticação e Perfil
def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        funcionario_form = FuncionarioForm(request.POST)
        
        if user_form.is_valid() and funcionario_form.is_valid():
            user = user_form.save()
            funcionario = funcionario_form.save(commit=False)
            funcionario.usuario = user
            funcionario.save()
            
            login(request, user)
            messages.success(request, "Cadastro realizado com sucesso! Bem-vindo ao sistema.")
            return redirect('despesas:dashboard')
    else:
        user_form = UserRegistrationForm()
        funcionario_form = FuncionarioForm()
    
    return render(request, 'despesas/register.html', {
        'user_form': user_form,
        'funcionario_form': funcionario_form
    })

@login_required
def profile(request):
    try:
        funcionario = request.user.funcionario
    except:
        funcionario = None
    
    if request.method == 'POST':
        if funcionario:
            funcionario_form = FuncionarioForm(request.POST, instance=funcionario)
        else:
            funcionario_form = FuncionarioForm(request.POST)
        
        if funcionario_form.is_valid():
            if not funcionario:
                funcionario = funcionario_form.save(commit=False)
                funcionario.usuario = request.user
                funcionario.save()
            else:
                funcionario_form.save()
            
            messages.success(request, "Perfil atualizado com sucesso!")
            return redirect('despesas:dashboard')
    else:
        funcionario_form = FuncionarioForm(instance=funcionario) if funcionario else FuncionarioForm()
    
    return render(request, 'despesas/profile.html', {
        'funcionario_form': funcionario_form,
        'funcionario': funcionario
    })

# Despesas
@login_required
def despesa_list(request):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    despesas = Despesa.objects.filter(funcionario=funcionario).order_by('-data_criacao')
    
    # Filtros
    status = request.GET.get('status')
    categoria = request.GET.get('categoria')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if status:
        despesas = despesas.filter(status=status)
    if categoria:
        despesas = despesas.filter(categoria_id=categoria)
    if data_inicio:
        despesas = despesas.filter(data_despesa__gte=data_inicio)
    if data_fim:
        despesas = despesas.filter(data_despesa__lte=data_fim)
    
    # Paginação
    paginator = Paginator(despesas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categorias = CategoriasDespesa.objects.all()
    
    context = {
        'page_obj': page_obj,
        'categorias': categorias,
        'status_choices': Despesa.STATUS_CHOICES,
    }
    
    return render(request, 'despesas/despesa_list.html', context)

@login_required
def despesa_create(request):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    if request.method == 'POST':
        form = DespesaForm(request.POST, request.FILES, funcionario=funcionario)
        if form.is_valid():
            despesa = form.save()
            messages.success(request, "Despesa registrada com sucesso!")
            return redirect('despesas:despesa_detail', codigo=despesa.codigo)
    else:
        form = DespesaForm(funcionario=funcionario)
    
    return render(request, 'despesas/despesa_form.html', {
        'form': form,
        'titulo': 'Nova Despesa'
    })

@login_required
def despesa_detail(request, codigo):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    despesa = get_object_or_404(Despesa, codigo=codigo)
    
    # Verifica permissão
    if despesa.funcionario != funcionario and not (funcionario.is_gerente() or funcionario.is_financeiro()):
        return HttpResponseForbidden("Você não tem permissão para acessar esta despesa.")
    
    return render(request, 'despesas/despesa_detail.html', {'despesa': despesa})

@login_required
def despesa_update(request, codigo):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    despesa = get_object_or_404(Despesa, codigo=codigo)
    
    # Verifica permissão
    if despesa.funcionario != funcionario:
        return HttpResponseForbidden("Você não tem permissão para editar esta despesa.")
    
    # Verifica se a despesa pode ser editada
    if despesa.status != 'RASCUNHO':
        messages.error(request, "Esta despesa não pode ser editada pois já foi enviada para aprovação.")
        return redirect('despesas:despesa_detail', codigo=despesa.codigo)
    
    if request.method == 'POST':
        form = DespesaForm(request.POST, request.FILES, instance=despesa, funcionario=funcionario)
        if form.is_valid():
            despesa = form.save()
            messages.success(request, "Despesa atualizada com sucesso!")
            return redirect('despesas:despesa_detail', codigo=despesa.codigo)
    else:
        form = DespesaForm(instance=despesa, funcionario=funcionario)
    
    return render(request, 'despesas/despesa_form.html', {
        'form': form,
        'titulo': 'Editar Despesa',
        'despesa': despesa
    })

@login_required
def despesa_delete(request, codigo):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    despesa = get_object_or_404(Despesa, codigo=codigo)
    
    # Verifica permissão
    if despesa.funcionario != funcionario:
        return HttpResponseForbidden("Você não tem permissão para excluir esta despesa.")
    
    # Verifica se a despesa pode ser excluída
    if despesa.status != 'RASCUNHO':
        messages.error(request, "Esta despesa não pode ser excluída pois já foi enviada para aprovação.")
        return redirect('despesas:despesa_detail', codigo=despesa.codigo)
    
    if request.method == 'POST':
        despesa.delete()
        messages.success(request, "Despesa excluída com sucesso!")
        return redirect('despesas:despesa_list')
    
    return render(request, 'despesas/despesa_confirm_delete.html', {'despesa': despesa})

# Solicitações de Reembolso
@login_required
def reembolso_list(request):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    solicitacoes = SolicitacaoReembolso.objects.filter(funcionario=funcionario).order_by('-data_solicitacao')
    
    # Filtros
    status = request.GET.get('status')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if status:
        solicitacoes = solicitacoes.filter(status=status)
    if data_inicio:
        solicitacoes = solicitacoes.filter(data_solicitacao__date__gte=data_inicio)
    if data_fim:
        solicitacoes = solicitacoes.filter(data_solicitacao__date__lte=data_fim)
    
    # Paginação
    paginator = Paginator(solicitacoes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_choices': SolicitacaoReembolso.STATUS_CHOICES,
    }
    
    return render(request, 'despesas/reembolso_list.html', context)

@login_required
def reembolso_create(request):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    # Verifica se há despesas em rascunho disponíveis
    despesas_disponiveis = Despesa.objects.filter(
        funcionario=funcionario,
        status='RASCUNHO'
    )
    
    if not despesas_disponiveis.exists():
        messages.warning(request, "Você não possui despesas em rascunho disponíveis para solicitar reembolso.")
        return redirect('despesas:despesa_create')
    
    if request.method == 'POST':
        form = SolicitacaoReembolsoForm(request.POST)
        despesas_ids = request.POST.getlist('despesas')
        
        if form.is_valid() and despesas_ids:
            # Cria a solicitação
            solicitacao = form.save(commit=False)
            solicitacao.funcionario = funcionario
            solicitacao.save()
            
            # Adiciona as despesas selecionadas
            despesas_selecionadas = Despesa.objects.filter(
                id__in=despesas_ids,
                funcionario=funcionario,
                status='RASCUNHO'
            )
            
            solicitacao.despesas.add(*despesas_selecionadas)
            
            # Atualiza o status das despesas
            for despesa in despesas_selecionadas:
                despesa.status = 'ENVIADA'
                despesa.save()
            
            messages.success(request, "Solicitação de reembolso criada com sucesso!")
            return redirect('despesas:reembolso_detail', codigo=solicitacao.codigo)
        else:
            if not despesas_ids:
                messages.error(request, "Selecione pelo menos uma despesa para solicitar reembolso.")
    else:
        form = SolicitacaoReembolsoForm()
    
    return render(request, 'despesas/reembolso_form.html', {
        'form': form,
        'despesas_disponiveis': despesas_disponiveis,
        'titulo': 'Nova Solicitação de Reembolso'
    })

@login_required
def reembolso_detail(request, codigo):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    solicitacao = get_object_or_404(SolicitacaoReembolso, codigo=codigo)
    
    # Verifica permissão
    if solicitacao.funcionario != funcionario and not (
        funcionario.is_gerente() and solicitacao.funcionario.departamento == funcionario.departamento or 
        funcionario.is_financeiro()
    ):
        return HttpResponseForbidden("Você não tem permissão para acessar esta solicitação.")
    
    # Verifica se há pagamento associado
    pagamento = None
    try:
        pagamento = solicitacao.pagamento
    except:
        pass
    
    return render(request, 'despesas/reembolso_detail.html', {
        'solicitacao': solicitacao,
        'pagamento': pagamento
    })

# Gerente - Aprovação de Reembolsos
@login_required
def aprovacao_list(request):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    # Verifica se é gerente
    if not funcionario.is_gerente():
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect('despesas:dashboard')
    
    # Busca solicitações pendentes do departamento
    solicitacoes = SolicitacaoReembolso.objects.filter(
        funcionario__departamento=funcionario.departamento,
        status='PENDENTE'
       ).order_by('-data_solicitacao')
    
    # Filtros
    funcionario_id = request.GET.get('funcionario')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if funcionario_id:
        solicitacoes = solicitacoes.filter(funcionario_id=funcionario_id)
    if data_inicio:
        solicitacoes = solicitacoes.filter(data_solicitacao__date__gte=data_inicio)
    if data_fim:
        solicitacoes = solicitacoes.filter(data_solicitacao__date__lte=data_fim)
    
    # Paginação
    paginator = Paginator(solicitacoes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    funcionarios = Funcionario.objects.filter(departamento=funcionario.departamento).exclude(id=funcionario.id)
    
    context = {
        'page_obj': page_obj,
        'funcionarios': funcionarios,
    }
    
    return render(request, 'despesas/aprovacao_list.html', context)

@login_required
def aprovacao_detail(request, codigo):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    # Verifica se é gerente
    if not funcionario.is_gerente():
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect('despesas:dashboard')
    
    solicitacao = get_object_or_404(SolicitacaoReembolso, codigo=codigo)
    
    # Verifica permissão
    if solicitacao.funcionario.departamento != funcionario.departamento:
        return HttpResponseForbidden("Você não tem permissão para acessar esta solicitação.")
    
    # Verifica se já foi aprovada/negada
    if solicitacao.status != 'PENDENTE':
        messages.warning(request, f"Esta solicitação já foi {solicitacao.get_status_display().lower()}.")
    
    return render(request, 'despesas/aprovacao_detail.html', {'solicitacao': solicitacao})

@login_required
def aprovacao_update(request, codigo):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    # Verifica se é gerente
    if not funcionario.is_gerente():
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect('despesas:dashboard')
    
    solicitacao = get_object_or_404(SolicitacaoReembolso, codigo=codigo)
    
    # Verifica permissão
    if solicitacao.funcionario.departamento != funcionario.departamento:
        return HttpResponseForbidden("Você não tem permissão para acessar esta solicitação.")
    
    # Verifica se já foi aprovada/negada
    if solicitacao.status != 'PENDENTE':
        messages.warning(request, f"Esta solicitação já foi {solicitacao.get_status_display().lower()}.")
        return redirect('despesas:aprovacao_detail', codigo=solicitacao.codigo)
    
    if request.method == 'POST':
        form = AprovarSolicitacaoForm(request.POST)
        if form.is_valid():
            decisao = form.cleaned_data['decisao']
            observacao = form.cleaned_data['observacao']
            
            solicitacao.status = decisao
            solicitacao.aprovador = funcionario
            solicitacao.data_aprovacao = timezone.now()
            solicitacao.save()
            
            # Atualiza o status das despesas
            for despesa in solicitacao.despesas.all():
                despesa.status = decisao
                despesa.save()
            
            messages.success(
                request, 
                f"Solicitação {solicitacao.get_status_display().lower()} com sucesso!"
            )
            return redirect('despesas:aprovacao_list')
    else:
        form = AprovarSolicitacaoForm()
    
    return render(request, 'despesas/aprovacao_form.html', {
        'form': form,
        'solicitacao': solicitacao
    })

# Financeiro - Pagamentos
@login_required
def pagamento_list(request):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    # Verifica se é financeiro
    if not funcionario.is_financeiro():
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect('despesas:dashboard')
    
    # Busca solicitações aprovadas pendentes de pagamento
    solicitacoes_pendentes = SolicitacaoReembolso.objects.filter(
        status='APROVADA'
    ).order_by('-data_aprovacao')
    
    # Busca pagamentos realizados
    pagamentos_realizados = Pagamento.objects.all().order_by('-data_pagamento')
    
    # Filtros para solicitações pendentes
    departamento = request.GET.get('departamento')
    funcionario_id = request.GET.get('funcionario')
    
    if departamento:
        solicitacoes_pendentes = solicitacoes_pendentes.filter(funcionario__departamento_id=departamento)
    if funcionario_id:
        solicitacoes_pendentes = solicitacoes_pendentes.filter(funcionario_id=funcionario_id)
    
    # Filtros para pagamentos realizados
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if data_inicio:
        pagamentos_realizados = pagamentos_realizados.filter(data_pagamento__date__gte=data_inicio)
    if data_fim:
        pagamentos_realizados = pagamentos_realizados.filter(data_pagamento__date__lte=data_fim)
    
    # Paginação
    paginator_pendentes = Paginator(solicitacoes_pendentes, 10)
    paginator_realizados = Paginator(pagamentos_realizados, 10)
    
    page_pendentes = request.GET.get('page_pendentes')
    page_realizados = request.GET.get('page_realizados')
    
    pendentes_page_obj = paginator_pendentes.get_page(page_pendentes)
    realizados_page_obj = paginator_realizados.get_page(page_realizados)
    
    departamentos = Departamento.objects.all()
    funcionarios = Funcionario.objects.all()
    
    context = {
        'pendentes_page_obj': pendentes_page_obj,
        'realizados_page_obj': realizados_page_obj,
        'departamentos': departamentos,
        'funcionarios': funcionarios,
    }
    
    return render(request, 'despesas/pagamento_list.html', context)

@login_required
def pagamento_create(request, codigo_solicitacao):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    # Verifica se é financeiro
    if not funcionario.is_financeiro():
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect('despesas:dashboard')
    
    solicitacao = get_object_or_404(SolicitacaoReembolso, codigo=codigo_solicitacao)
    
    # Verifica se já foi paga
    if solicitacao.status != 'APROVADA':
        messages.warning(request, "Esta solicitação não está disponível para pagamento.")
        return redirect('despesas:pagamento_list')
    
    # Verifica se já existe um pagamento
    try:
        pagamento = solicitacao.pagamento
        messages.warning(request, "Já existe um pagamento para esta solicitação.")
        return redirect('despesas:pagamento_detail', pk=pagamento.id)
    except:
        pass
    
    if request.method == 'POST':
        form = PagamentoForm(request.POST, request.FILES, solicitacao=solicitacao, responsavel=funcionario)
        if form.is_valid():
            pagamento = form.save()
            messages.success(request, "Pagamento registrado com sucesso!")
            return redirect('despesas:pagamento_detail', pk=pagamento.id)
    else:
        form = PagamentoForm(solicitacao=solicitacao, responsavel=funcionario)
    
    return render(request, 'despesas/pagamento_form.html', {
        'form': form,
        'solicitacao': solicitacao
    })

@login_required
def pagamento_detail(request, pk):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    pagamento = get_object_or_404(Pagamento, pk=pk)
    
    # Verifica permissão
    if not funcionario.is_financeiro() and pagamento.solicitacao.funcionario != funcionario:
        return HttpResponseForbidden("Você não tem permissão para acessar este pagamento.")
    
    return render(request, 'despesas/pagamento_detail.html', {'pagamento': pagamento})

# Relatórios
@login_required
def relatorio_list(request):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    # Verifica se é financeiro
    if not funcionario.is_financeiro():
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect('despesas:dashboard')
    
    relatorios = RelatorioFinanceiro.objects.all().order_by('-data_criacao')
    
    # Filtros
    tipo = request.GET.get('tipo')
    departamento = request.GET.get('departamento')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if tipo:
        relatorios = relatorios.filter(tipo=tipo)
    if departamento:
        relatorios = relatorios.filter(departamento_id=departamento)
    if data_inicio:
        relatorios = relatorios.filter(data_criacao__date__gte=data_inicio)
    if data_fim:
        relatorios = relatorios.filter(data_criacao__date__lte=data_fim)
    
    # Paginação
    paginator = Paginator(relatorios, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    departamentos = Departamento.objects.all()
    
    context = {
        'page_obj': page_obj,
        'departamentos': departamentos,
        'tipo_choices': RelatorioFinanceiro.TIPO_CHOICES,
    }
    
    return render(request, 'despesas/relatorio_list.html', context)

@login_required
def relatorio_create(request):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    # Verifica se é financeiro
    if not funcionario.is_financeiro():
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect('despesas:dashboard')
    
    if request.method == 'POST':
        form = RelatorioFinanceiroForm(request.POST, criado_por=funcionario)
        if form.is_valid():
            relatorio = form.save()
            messages.success(request, "Relatório criado com sucesso!")
            return redirect('despesas:relatorio_detail', pk=relatorio.id)
    else:
        form = RelatorioFinanceiroForm(criado_por=funcionario)
    
    return render(request, 'despesas/relatorio_form.html', {
        'form': form,
        'titulo': 'Novo Relatório Financeiro'
    })

@login_required
def relatorio_detail(request, pk):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    # Verifica se é financeiro
    if not funcionario.is_financeiro():
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect('despesas:dashboard')
    
    relatorio = get_object_or_404(RelatorioFinanceiro, pk=pk)
    
    return render(request, 'despesas/relatorio_detail.html', {'relatorio': relatorio})

@login_required
def relatorio_gerar(request):
    try:
        funcionario = request.user.funcionario
    except:
        messages.error(request, "Perfil de funcionário não encontrado. Por favor, complete seu cadastro.")
        return redirect('despesas:profile')
    
    # Verifica se é financeiro
    if not funcionario.is_financeiro():
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect('despesas:dashboard')
    
    if request.method == 'POST':
        form = DespesaPeriodoForm(request.POST)
        if form.is_valid():
            data_inicio = form.cleaned_data['data_inicio']
            data_fim = form.cleaned_data['data_fim']
            departamento = form.cleaned_data['departamento']
            
            # Filtra despesas pelo período e departamento (se especificado)
            despesas = Despesa.objects.filter(
                data_despesa__gte=data_inicio,
                data_despesa__lte=data_fim
            )
            
            if departamento:
                despesas = despesas.filter(funcionario__departamento=departamento)
            
            # Agrega dados para análise
            total_despesas = despesas.count()
            valor_total = despesas.aggregate(total=Sum('valor'))['total'] or 0
            
            # Despesas por status
            despesas_status = list(despesas.values('status').annotate(
                total=Count('id'), valor=Sum('valor')).order_by('status'))
            
            # Despesas por categoria
            despesas_categoria = list(despesas.values('categoria__nome').annotate(
                total=Count('id'), valor=Sum('valor')).order_by('-valor'))
            
            # Despesas por departamento
            despesas_departamento = list(despesas.values('funcionario__departamento__nome').annotate(
                total=Count('id'), valor=Sum('valor')).order_by('-valor'))
            
            # Gerar gráficos se houver dados
            grafico_categorias = None
            grafico_departamentos = None
            grafico_status = None
            
            if total_despesas > 0:
                # Gráfico de categorias
                df_cat = pd.DataFrame(despesas_categoria)
                if not df_cat.empty and 'categoria__nome' in df_cat and 'valor' in df_cat:
                    plt.figure(figsize=(10, 6))
                    plt.pie(df_cat['valor'], labels=df_cat['categoria__nome'], autopct='%1.1f%%')
                    plt.title('Despesas por Categoria')
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png')
                    buf.seek(0)
                    grafico_categorias = base64.b64encode(buf.read()).decode('utf-8')
                    plt.close()
                
                # Gráfico de departamentos
                df_dep = pd.DataFrame(despesas_departamento)
                if not df_dep.empty and 'funcionario__departamento__nome' in df_dep and 'valor' in df_dep:
                    plt.figure(figsize=(10, 6))
                    plt.bar(df_dep['funcionario__departamento__nome'], df_dep['valor'])
                    plt.title('Despesas por Departamento')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png')
                    buf.seek(0)
                    grafico_departamentos = base64.b64encode(buf.read()).decode('utf-8')
                    plt.close()
                
                # Gráfico de status
                df_status = pd.DataFrame(despesas_status)
                if not df_status.empty and 'status' in df_status and 'valor' in df_status:
                    # Mapear códigos de status para descrições
                    status_dict = dict(Despesa.STATUS_CHOICES)
                    df_status['status_desc'] = df_status['status'].map(status_dict)
                    
                    plt.figure(figsize=(10, 6))
                    plt.bar(df_status['status_desc'], df_status['valor'])
                    plt.title('Despesas por Status')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png')
                    buf.seek(0)
                    grafico_status = base64.b64encode(buf.read()).decode('utf-8')
                    plt.close()
            
            context = {
                'form': form,
                'data_inicio': data_inicio,
                'data_fim': data_fim,
                'departamento': departamento,
                'total_despesas': total_despesas,
                'valor_total': valor_total,
                'despesas_status': despesas_status,
                'despesas_categoria': despesas_categoria,
                'despesas_departamento': despesas_departamento,
                'grafico_categorias': grafico_categorias,
                'grafico_departamentos': grafico_departamentos,
                'grafico_status': grafico_status,
                'has_result': True
            }
            
            return render(request, 'despesas/relatorio_gerar.html', context)
    else:
        form = DespesaPeriodoForm()
    
    return render(request, 'despesas/relatorio_gerar.html', {
        'form': form,
        'has_result': False
    })

