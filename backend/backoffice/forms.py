from django.conf import settings
from unfold.forms import AuthenticationForm

from accounts.constants import DEMO_ADMIN_PASSWORD, DEMO_ADMIN_USERNAME


class AdminLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.DEMO_MODE:
            self.fields["username"].widget.attrs["placeholder"] = DEMO_ADMIN_USERNAME
            self.fields["password"].widget.attrs["placeholder"] = DEMO_ADMIN_PASSWORD
