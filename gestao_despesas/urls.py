from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('despesas.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='despesas/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('senha/alterar/', auth_views.PasswordChangeView.as_view(template_name='despesas/password_change.html'), name='password_change'),
    path('senha/alterar/done/', auth_views.PasswordChangeDoneView.as_view(template_name='despesas/password_change_done.html'), name='password_change_done'),   
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)