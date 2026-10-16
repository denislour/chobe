from shops.models import ShopAuditEvent


def audit_change(shop, actor, action, changes):
    ShopAuditEvent.objects.create(
        shop=shop, actor=actor, action=action, changes=changes
    )
