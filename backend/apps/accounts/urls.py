from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.MeView.as_view(), name="me"),
    path("legal-acceptance/", views.LegalAcceptanceView.as_view(), name="legal-acceptance"),
    path("verify-email/", views.VerifyEmailView.as_view(), name="verify-email"),
    path("verify-email/resend/", views.ResendVerificationView.as_view(), name="verify-email-resend"),
    path("password-reset/", views.PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset/confirm/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("password/change/", views.ChangePasswordView.as_view(), name="password-change"),
    path("delete/", views.DeleteAccountView.as_view(), name="account-delete"),
    path("export/", views.DataExportView.as_view(), name="data-export"),
    path("export/download/", views.DataExportDownloadView.as_view(), name="data-export-download"),
]
