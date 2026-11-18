import requests
from django.utils.translation import gettext as _
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from . import services, wish as wish_service
from .geo import search_cities
from .models import JobWish, SavedSearch
from .serializers import JobWishSerializer, SavedSearchSerializer


class SavedSearchViewSet(viewsets.ModelViewSet):
    serializer_class = SavedSearchSerializer

    def get_queryset(self):
        # Le ricerche nascoste del lavoro dei desideri non si vedono e non si
        # modificano da qui (Sprint 84).
        return SavedSearch.objects.filter(user=self.request.user, is_wish=False)

    def perform_create(self, serializer):
        try:
            services.check_can_create(self.request.user)
        except services.PlanLimitExceeded as exc:
            raise ValidationError({"detail": str(exc)})
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        self._deactivated_previous = None
        try:
            with transaction.atomic():
                response = super().update(request, *args, **kwargs)
        except services.PlanLimitExceeded as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if self._deactivated_previous is not None:
            response.data["deactivated_previous"] = self.get_serializer(self._deactivated_previous).data
        return response

    def perform_update(self, serializer):
        # Cambiare il tipo di una ricerca attiva equivale ad attivarla nel
        # nuovo tipo (Sprint 68): stessi limiti di piano dell'attivazione —
        # su Free si spegne l'eventuale altra ricerca attiva di quel tipo
        # (restituita in `deactivated_previous`), su Pro il pool è unico e
        # non cambia. Prima un Free poteva trovarsi con 2 ricerche attive
        # dello stesso tipo.
        # Sprint 84: lo stesso controllo vale se cambiano le città di una
        # ricerca in uso (ogni città conta come una ricerca attiva).
        previous_type = serializer.instance.search_type
        previous_cities = list(serializer.instance.cities)
        search = serializer.save()
        if search.is_active and (search.search_type != previous_type or search.cities != previous_cities):
            self._deactivated_previous = services.activate_search(search)

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


@api_view(["GET"])
def search_limits(request):
    """Città attive e massimale (Sprint 84): "Città attive n di 50"."""
    return Response(
        {
            "active_cities": services.active_city_count(request.user),
            "max_active_cities": services.max_active_cities(request.user),
            "max_cities_per_search": services.MAX_CITIES_PER_SEARCH[request.user.plan],
        }
    )


def _wish_payload(wish):
    if wish is None:
        return {"exists": False, "description": "", "country": "", "cities": [], "is_active": False,
                "changes_left_today": wish_service.MAX_WISH_CHANGES_PER_DAY}
    return {
        "exists": True,
        "description": wish.description,
        "country": wish.country,
        "cities": wish.cities,
        "is_active": wish.is_active,
        "changes_left_today": wish_service.changes_left_today(wish),
    }


@api_view(["GET", "PUT"])
def job_wish(request):
    """Lavoro dei desideri (Sprint 84, A19), solo Pro in scrittura. La
    risposta non contiene mai le keyword ricavate dall'AI."""
    if request.method == "GET":
        return Response(_wish_payload(JobWish.objects.filter(user=request.user).first()))
    serializer = JobWishSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    try:
        cities = [c.strip() for c in data["cities"] if c.strip()]
        wish = wish_service.save_wish(request.user, data["description"], data["country"], cities, data["is_active"])
    except (wish_service.WishError, services.PlanLimitExceeded) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response(
            {"detail": _("Non siamo riusciti a ricavare la ricerca dalla descrizione: riprova più tardi.")},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return Response(_wish_payload(wish))


@api_view(["GET"])
def city_autocomplete(request):
    """Proxy verso Nominatim (OpenStreetMap) per l'autocomplete città/paese
    delle ricerche salvate: il frontend non chiama mai Nominatim
    direttamente, per rispettare lo User-Agent richiesto dai suoi ToS senza
    esporlo lato client."""
    query = request.query_params.get("q", "")
    # Sprint 84: città solo del paese scelto (codice ISO, facoltativo).
    country_code = request.query_params.get("country_code", "")
    try:
        results = search_cities(query, country_code=country_code)
    except requests.RequestException:
        return Response([], status=status.HTTP_200_OK)
    return Response(results)
