from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from . import services
from .models import SavedSearch
from .serializers import SavedSearchSerializer


class SavedSearchViewSet(viewsets.ModelViewSet):
    serializer_class = SavedSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        try:
            services.check_can_create(self.request.user)
        except services.PlanLimitExceeded as exc:
            raise ValidationError({"detail": str(exc)})
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        search = self.get_object()
        try:
            deactivated = services.activate_search(search)
        except services.PlanLimitExceeded as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        data = self.get_serializer(search).data
        if deactivated is not None:
            data["deactivated_previous"] = self.get_serializer(deactivated).data
        return Response(data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        search = self.get_object()
        services.deactivate_search(search)
        return Response(self.get_serializer(search).data)
