from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import User
from .serializers import (
    ProfileSerializer,
    RegisterSerializer,
    DepositSerializer,
    UserProfileSerializer,
)
from django.db.models import F


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class ProfileView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class DepositView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DepositSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]

        user = request.user
        user.balance = F("balance") + amount
        user.save(update_fields=["balance"])
        user.refresh_from_db()

        return Response(ProfileSerializer(user).data, status=status.HTTP_200_OK)
