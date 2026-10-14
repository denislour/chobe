from django.conf import settings
from django.core.exceptions import ValidationError
from unfold.forms import AuthenticationForm

from accounts.constants import DEMO_ADMIN_PASSWORD, DEMO_ADMIN_USERNAME
from backoffice.throttles import AdminLoginAccountThrottle, AdminLoginIPThrottle


class AdminLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.DEMO_MODE:
            self.fields["username"].widget.attrs["placeholder"] = DEMO_ADMIN_USERNAME
            self.fields["password"].widget.attrs["placeholder"] = DEMO_ADMIN_PASSWORD

    def clean(self):
        if self.request is not None:
            allowed = [
                throttle().allow_request(self.request, None)
                for throttle in (AdminLoginIPThrottle, AdminLoginAccountThrottle)
            ]
            if not all(allowed):
                raise ValidationError(
                    "Too many login attempts. Please try again later.",
                    code="throttled",
                )
        return super().clean()
