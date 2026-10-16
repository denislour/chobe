import io

from django.http import FileResponse, Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
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

    def get_permissions(self):
        actions = (
            self.action_map.values() if self.action == "metadata" else (self.action,)
        )
        if not any(action in ("me", "update_me", "avatar") for action in actions):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    @action(detail=False, methods=["get"])
    def me(self, request):
        return self.retrieve(request)

    @me.mapping.patch
    def update_me(self, request):
        return self.partial_update(request)

    def get_object(self):
        return profile_for(self.request.user)

    @action(detail=False, methods=["get"], url_path="me/avatar")
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
