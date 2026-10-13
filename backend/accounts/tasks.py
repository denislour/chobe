from django.tasks import task

from accounts.emails import send_account_email
from accounts.models import User


@task
def send_welcome_email(user_id: int) -> int:
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None or not user.email:
        return 0
    return send_account_email("welcome", user)
