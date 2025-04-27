from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Despesa, SolicitacaoReembolso, Funcionario, Pagamento, RelatorioFinanceiro

class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, label='Nome')
    last_name = forms.CharField(max_length=30, required=True, label='Sobrenome')
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class FuncionarioForm(forms.ModelForm):
    class Meta:
        model = Funcionario
        fields = ('departamento', 'cargo', 'matricula', 'telefone', 'data_admissao')
        widgets = {
            'data_admissao': forms.DateInput(attrs={'type': 'date'}),
        }

class DespesaForm(forms.ModelForm):
    class Meta:
        model = Despesa
        fields = ('categoria', 'descricao', 'valor', 'data_despesa', 'comprovante')
        widgets = {
            'data_despesa': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        self.funcionario = kwargs.pop('funcionario', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        despesa = super().save(commit=False)
        if self.funcionario:
            despesa.funcionario = self.funcionario
        if commit:
            despesa.save()
        return despesa

class SolicitacaoReembolsoForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoReembolso
        fields = ('justificativa',)
        widgets = {
            'justificativa': forms.Textarea(attrs={'rows': 4}),
        }

class AprovarSolicitacaoForm(forms.Form):
    CHOICES = [
        ('APROVADA', 'Aprovar'),
        ('NEGADA', 'Negar'),
    ]
    decisao = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect)
    observacao = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=False)

class PagamentoForm(forms.ModelForm):
    class Meta:
        model = Pagamento
        fields = ('valor', 'metodo', 'comprovante', 'observacoes')
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        self.solicitacao = kwargs.pop('solicitacao', None)
        self.responsavel = kwargs.pop('responsavel', None)
        super().__init__(*args, **kwargs)
        if self.solicitacao:
            self.fields['valor'].initial = self.solicitacao.valor_total()

    def save(self, commit=True):
        pagamento = super().save(commit=False)
        if self.solicitacao:
            pagamento.solicitacao = self.solicitacao
        if self.responsavel:
            pagamento.responsavel = self.responsavel
        if commit:
            pagamento.save()
            # Atualizar o status da solicitação
            self.solicitacao.status = 'PAGA'
            self.solicitacao.save()
            # Atualizar o status de todas as despesas relacionadas
            for despesa in self.solicitacao.despesas.all():
                despesa.status = 'PAGA'
                despesa.save()
        return pagamento

class RelatorioFinanceiroForm(forms.ModelForm):
    class Meta:
        model = RelatorioFinanceiro
        fields = ('titulo', 'tipo', 'data_inicio', 'data_fim', 'departamento', 'observacoes')
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        self.criado_por = kwargs.pop('criado_por', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        relatorio = super().save(commit=False)
        if self.criado_por:
            relatorio.criado_por = self.criado_por
        if commit:
            relatorio.save()
        return relatorio

class DespesaPeriodoForm(forms.Form):
    data_inicio = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    data_fim = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    departamento = forms.ModelChoiceField(queryset=None, required=False)
    
    def __init__(self, *args, **kwargs):
        from .models import Departamento
        super().__init__(*args, **kwargs)
        self.fields['departamento'].queryset = Departamento.objects.all()