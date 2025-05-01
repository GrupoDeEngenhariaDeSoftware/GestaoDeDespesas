from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

app_name = 'despesas'

urlpatterns = [
    
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    
    path('registrar/', views.register, name='register'),
    path('perfil/', views.profile, name='profile'),
    
    
    path('despesas/', views.despesa_list, name='despesa_list'),
    path('despesas/nova/', views.despesa_create, name='despesa_create'),
    path('despesas/<uuid:codigo>/', views.despesa_detail, name='despesa_detail'),
    path('despesas/<uuid:codigo>/editar/', views.despesa_update, name='despesa_update'),
    path('despesas/<uuid:codigo>/excluir/', views.despesa_delete, name='despesa_delete'),
    
    
    path('reembolsos/', views.reembolso_list, name='reembolso_list'),
    path('reembolsos/nova/', views.reembolso_create, name='reembolso_create'),
    path('reembolsos/<uuid:codigo>/', views.reembolso_detail, name='reembolso_detail'),
    
    
    path('aprovacoes/', views.aprovacao_list, name='aprovacao_list'),
    path('aprovacoes/<uuid:codigo>/', views.aprovacao_detail, name='aprovacao_detail'),
    path('aprovacoes/<uuid:codigo>/aprovar/', views.aprovacao_update, name='aprovacao_update'),
    
    
    path('pagamentos/', views.pagamento_list, name='pagamento_list'),
    path('pagamentos/novo/<uuid:codigo_solicitacao>/', views.pagamento_create, name='pagamento_create'),
    path('pagamentos/<int:pk>/', views.pagamento_detail, name='pagamento_detail'),
    
    
    path('relatorios/', views.relatorio_list, name='relatorio_list'),
    path('relatorios/novo/', views.relatorio_create, name='relatorio_create'),
    path('relatorios/<int:pk>/', views.relatorio_detail, name='relatorio_detail'),
    path('relatorios/gerar/', views.relatorio_gerar, name='relatorio_gerar'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('relatorio/', views.relatorio_gerar, name='relatorio_gerar'),
    
]