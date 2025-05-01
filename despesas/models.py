from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid

class Departamento(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'

class Funcionario(models.Model):
    CARGO_CHOICES = [
        ('FUNCIONARIO', 'Funcionário'),
        ('GERENTE', 'Gerente'),
        ('FINANCEIRO', 'Financeiro'),
    ]
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='funcionario')
    cargo = models.CharField(max_length=15, choices=CARGO_CHOICES, default='FUNCIONARIO')
    departamento = models.ForeignKey(Departamento, on_delete=models.PROTECT, related_name='funcionarios')
    matricula = models.CharField(max_length=20, unique=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    data_admissao = models.DateField()
    
    def __str__(self):
        return f"{self.usuario.get_full_name()} ({self.matricula})"
    
    def is_gerente(self):
        return self.cargo == 'GERENTE'
    
    def is_financeiro(self):
        return self.cargo == 'FINANCEIRO'
    
    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'

class CategoriasDespesa(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    limite_valor = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    requer_aprovacao = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = 'Categoria de Despesa'
        verbose_name_plural = 'Categorias de Despesas'

class Despesa(models.Model):
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('ENVIADA', 'Enviada para aprovação'),
        ('APROVADA', 'Aprovada'),
        ('NEGADA', 'Negada'),
        ('PAGA', 'Reembolso realizado'),
    ]
    
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='despesas')
    categoria = models.ForeignKey(CategoriasDespesa, on_delete=models.PROTECT, related_name='despesas')
    descricao = models.TextField()
    valor = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    data_despesa = models.DateField()
    comprovante = models.FileField(upload_to='comprovantes/', blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RASCUNHO')
    codigo = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    def __str__(self):
        return f"{self.descricao[:30]} - R$ {self.valor} ({self.get_status_display()})"
    
    class Meta:
        verbose_name = 'Despesa'
        verbose_name_plural = 'Despesas'
        ordering = ['-data_criacao']

class SolicitacaoReembolso(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente de Aprovação'),
        ('APROVADA', 'Aprovada'),
        ('NEGADA', 'Negada'),
        ('PAGA', 'Reembolso Realizado'),
    ]
    
    despesas = models.ManyToManyField(Despesa, related_name='solicitacoes')
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='solicitacoes')
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_aprovacao = models.DateTimeField(blank=True, null=True)
    aprovador = models.ForeignKey(Funcionario, on_delete=models.SET_NULL, related_name='aprovacoes', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    justificativa = models.TextField(blank=True, null=True)
    codigo = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    def valor_total(self):
        return self.despesas.aggregate(total=models.Sum('valor'))['total'] or 0
    
    def __str__(self):
        return f"Solicitação #{self.id} - {self.funcionario.usuario.get_full_name()}"
    
    class Meta:
        verbose_name = 'Solicitação de Reembolso'
        verbose_name_plural = 'Solicitações de Reembolso'
        ordering = ['-data_solicitacao']

class Pagamento(models.Model):
    METODO_CHOICES = [
        ('PIX', 'PIX'),
        ('TED', 'Transferência'),
        ('DEPOSITO', 'Depósito'),
        ('OUTRO', 'Outro'),
    ]
    
    solicitacao = models.OneToOneField(SolicitacaoReembolso, on_delete=models.CASCADE, related_name='pagamento')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_pagamento = models.DateTimeField(default=timezone.now)
    responsavel = models.ForeignKey(Funcionario, on_delete=models.PROTECT, related_name='pagamentos')
    metodo = models.CharField(max_length=10, choices=METODO_CHOICES, default='PIX')
    comprovante = models.FileField(upload_to='pagamentos/', blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Pagamento #{self.id} - R$ {self.valor} ({self.metodo})"
    
    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        ordering = ['-data_pagamento']

class RelatorioFinanceiro(models.Model):
    TIPO_CHOICES = [
        ('MENSAL', 'Relatório Mensal'),
        ('TRIMESTRAL', 'Relatório Trimestral'),
        ('ANUAL', 'Relatório Anual'),
        ('PERSONALIZADO', 'Relatório Personalizado'),
    ]
    
    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='MENSAL')
    data_inicio = models.DateField()
    data_fim = models.DateField()
    departamento = models.ForeignKey(Departamento, on_delete=models.SET_NULL, null=True, blank=True, related_name='relatorios')
    criado_por = models.ForeignKey(Funcionario, on_delete=models.PROTECT, related_name='relatorios')
    data_criacao = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True, null=True)
    arquivo = models.FileField(upload_to='relatorios/', blank=True, null=True)
    
    def __str__(self):
        return self.titulo
    
    class Meta:
        verbose_name = 'Relatório Financeiro'
        verbose_name_plural = 'Relatórios Financeiros'
        ordering = ['-data_criacao']

class Reembolso(models.Model):
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.TextField()
    data_reembolso = models.DateField()
    criado_em = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True)


    def __str__(self):
        return f"Reembolso de {self.valor} em {self.data_reembolso}"