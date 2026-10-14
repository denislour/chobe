from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from accounts.schemas.base import CSRFSchema
from accounts.serializers.privacy import PrivacySerializer
from accounts.services.privacy import privacy_for
from accounts.throttles import AccountMutationThrottle


@method_decorator(never_cache, name="dispatch")
class PrivacyViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (AccountMutationThrottle,)
    serializer_class = PrivacySerializer
    schema = CSRFSchema()

    def get_object(self):
        return privacy_for(self.request.user)
