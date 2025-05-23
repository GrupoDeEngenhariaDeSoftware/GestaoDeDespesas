# Generated by Django 5.2 on 2025-04-26 17:18

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoriasDespesa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('descricao', models.TextField(blank=True, null=True)),
                ('limite_valor', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('requer_aprovacao', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Categoria de Despesa',
                'verbose_name_plural': 'Categorias de Despesas',
            },
        ),
        migrations.CreateModel(
            name='Departamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('descricao', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Departamento',
                'verbose_name_plural': 'Departamentos',
            },
        ),
        migrations.CreateModel(
            name='Funcionario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cargo', models.CharField(choices=[('FUNCIONARIO', 'Funcionário'), ('GERENTE', 'Gerente'), ('FINANCEIRO', 'Financeiro')], default='FUNCIONARIO', max_length=15)),
                ('matricula', models.CharField(max_length=20, unique=True)),
                ('telefone', models.CharField(blank=True, max_length=20, null=True)),
                ('data_admissao', models.DateField()),
                ('departamento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='funcionarios', to='despesas.departamento')),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='funcionario', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Funcionário',
                'verbose_name_plural': 'Funcionários',
            },
        ),
        migrations.CreateModel(
            name='Despesa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.TextField()),
                ('valor', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)])),
                ('data_despesa', models.DateField()),
                ('comprovante', models.FileField(blank=True, null=True, upload_to='comprovantes/')),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('data_atualizacao', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('RASCUNHO', 'Rascunho'), ('ENVIADA', 'Enviada para aprovação'), ('APROVADA', 'Aprovada'), ('NEGADA', 'Negada'), ('PAGA', 'Reembolso realizado')], default='RASCUNHO', max_length=20)),
                ('codigo', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('categoria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='despesas', to='despesas.categoriasdespesa')),
                ('funcionario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='despesas', to='despesas.funcionario')),
            ],
            options={
                'verbose_name': 'Despesa',
                'verbose_name_plural': 'Despesas',
                'ordering': ['-data_criacao'],
            },
        ),
        migrations.CreateModel(
            name='RelatorioFinanceiro',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=200)),
                ('tipo', models.CharField(choices=[('MENSAL', 'Relatório Mensal'), ('TRIMESTRAL', 'Relatório Trimestral'), ('ANUAL', 'Relatório Anual'), ('PERSONALIZADO', 'Relatório Personalizado')], default='MENSAL', max_length=20)),
                ('data_inicio', models.DateField()),
                ('data_fim', models.DateField()),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('observacoes', models.TextField(blank=True, null=True)),
                ('arquivo', models.FileField(blank=True, null=True, upload_to='relatorios/')),
                ('criado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='relatorios', to='despesas.funcionario')),
                ('departamento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='relatorios', to='despesas.departamento')),
            ],
            options={
                'verbose_name': 'Relatório Financeiro',
                'verbose_name_plural': 'Relatórios Financeiros',
                'ordering': ['-data_criacao'],
            },
        ),
        migrations.CreateModel(
            name='SolicitacaoReembolso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_solicitacao', models.DateTimeField(auto_now_add=True)),
                ('data_aprovacao', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('PENDENTE', 'Pendente de Aprovação'), ('APROVADA', 'Aprovada'), ('NEGADA', 'Negada'), ('PAGA', 'Reembolso Realizado')], default='PENDENTE', max_length=20)),
                ('justificativa', models.TextField(blank=True, null=True)),
                ('codigo', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('aprovador', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='aprovacoes', to='despesas.funcionario')),
                ('despesas', models.ManyToManyField(related_name='solicitacoes', to='despesas.despesa')),
                ('funcionario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='solicitacoes', to='despesas.funcionario')),
            ],
            options={
                'verbose_name': 'Solicitação de Reembolso',
                'verbose_name_plural': 'Solicitações de Reembolso',
                'ordering': ['-data_solicitacao'],
            },
        ),
        migrations.CreateModel(
            name='Pagamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor', models.DecimalField(decimal_places=2, max_digits=10)),
                ('data_pagamento', models.DateTimeField(default=django.utils.timezone.now)),
                ('metodo', models.CharField(choices=[('PIX', 'PIX'), ('TED', 'Transferência'), ('DEPOSITO', 'Depósito'), ('OUTRO', 'Outro')], default='PIX', max_length=10)),
                ('comprovante', models.FileField(blank=True, null=True, upload_to='pagamentos/')),
                ('observacoes', models.TextField(blank=True, null=True)),
                ('responsavel', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pagamentos', to='despesas.funcionario')),
                ('solicitacao', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='pagamento', to='despesas.solicitacaoreembolso')),
            ],
            options={
                'verbose_name': 'Pagamento',
                'verbose_name_plural': 'Pagamentos',
                'ordering': ['-data_pagamento'],
            },
        ),
    ]
