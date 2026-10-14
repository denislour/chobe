import io

from django.http import FileResponse, Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from accounts.schemas.profile import ProfileSchema
from accounts.serializers.profile import ProfileSerializer
from accounts.services.profile import profile_for
from accounts.throttles import AccountMutationThrottle


@method_decorator(never_cache, name="dispatch")
class ProfileViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (AccountMutationThrottle,)
    serializer_class = ProfileSerializer
    schema = ProfileSchema()

    def get_object(self):
        return profile_for(self.request.user)

    def avatar(self, request):
        profile = self.get_object()
        if not profile.avatar:
            raise Http404
        response = FileResponse(
            io.BytesIO(bytes(profile.avatar)), content_type="image/jpeg"
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response
