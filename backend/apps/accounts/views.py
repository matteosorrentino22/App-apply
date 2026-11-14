from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework.views import APIView

from .models import User
from .serializers import LoginSerializer, RegisterSerializer, UserOnboardingSerializer
from .throttling import LoginEmailRateThrottle
from .tokens import create_token


def _user_agent(request):
    return request.META.get("HTTP_USER_AGENT", "")


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "register"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"token": create_token(user, _user_agent(request))}, status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle, LoginEmailRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = create_token(serializer.validated_data["user"], _user_agent(request))
        return Response({"token": token})


class LogoutView(APIView):
    """Revoca il solo token della richiesta (questo dispositivo)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserOnboardingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
