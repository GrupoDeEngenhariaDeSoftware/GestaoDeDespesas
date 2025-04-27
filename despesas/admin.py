from django.contrib import admin
from .models import (
    Departamento,
    Funcionario,
    CategoriasDespesa,
    Despesa,
    SolicitacaoReembolso,
    Pagamento,
    RelatorioFinanceiro
)

@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao')
    search_fields = ('nome',)

@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('matricula', 'get_nome', 'cargo', 'departamento', 'data_admissao')
    list_filter = ('cargo', 'departamento')
    search_fields = ('matricula', 'usuario__first_name', 'usuario__last_name', 'usuario__username')
    
    def get_nome(self, obj):
        return obj.usuario.get_full_name()
    get_nome.short_description = 'Nome'

@admin.register(CategoriasDespesa)
class CategoriasDespesaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'limite_valor', 'requer_aprovacao')
    list_filter = ('requer_aprovacao',)
    search_fields = ('nome',)

class DespesaInline(admin.TabularInline):
    model = SolicitacaoReembolso.despesas.through
    extra = 0

@admin.register(Despesa)
class DespesaAdmin(admin.ModelAdmin):
    list_display = ('id', 'funcionario', 'categoria', 'valor', 'data_despesa', 'status')
    list_filter = ('status', 'categoria', 'data_despesa')
    search_fields = ('descricao', 'funcionario__usuario__first_name', 'funcionario__usuario__last_name')
    readonly_fields = ('codigo', 'data_criacao', 'data_atualizacao')
    date_hierarchy = 'data_despesa'

@admin.register(SolicitacaoReembolso)
class SolicitacaoReembolsoAdmin(admin.ModelAdmin):
    list_display = ('id', 'funcionario', 'get_valor_total', 'data_solicitacao', 'status')
    list_filter = ('status', 'data_solicitacao')
    search_fields = ('funcionario__usuario__first_name', 'funcionario__usuario__last_name')
    readonly_fields = ('codigo', 'data_solicitacao')
    inlines = [DespesaInline]
    exclude = ('despesas',)
    
    def get_valor_total(self, obj):
        return f'R$ {obj.valor_total()}'
    get_valor_total.short_description = 'Valor Total'

@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'solicitacao', 'valor', 'metodo', 'data_pagamento', 'responsavel')
    list_filter = ('metodo', 'data_pagamento')
    search_fields = ('solicitacao__codigo', 'solicitacao__funcionario__usuario__first_name')
    readonly_fields = ('data_pagamento',)

@admin.register(RelatorioFinanceiro)
class RelatorioFinanceiroAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'data_inicio', 'data_fim', 'criado_por', 'data_criacao')
    list_filter = ('tipo', 'data_inicio', 'data_fim')
    search_fields = ('titulo', 'observacoes')
    readonly_fields = ('data_criacao',)
    date_hierarchy = 'data_criacao'