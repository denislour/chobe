from collections import Counter
from uuid import NAMESPACE_URL, uuid5

from accounts.models import AccountDataExport, DeletionRequest, ViewingHistory
from accounts.services.demo import DEMO_PASSWORD, DEMO_PEOPLE
from listings.models import Favorite, Notification, Report, SavedSearch
from listings.services.demo.catalog import DEMO_PRODUCTS, DEMO_SPECIAL_STORIES
from listings.services.search import public_listings
from shops.models import ShopFollow

STORY_LABELS = {
    "active": "Đã duyệt, đang bán",
    "pending": "Tin mới chờ admin duyệt",
    "rejected": "Tin mới bị từ chối",
    "draft": "Nháp chưa đủ thông tin, chưa có ảnh",
    "hidden": "Chủ shop tự ẩn",
    "sold": "Chủ shop đánh dấu đã bán",
    "pending_edit": "Bản sửa chờ duyệt; bản cũ vẫn công khai",
    "rejected_edit": "Bản sửa bị từ chối; bản cũ vẫn công khai",
    "draft_edit": "Nháp sửa chưa gửi; bản cũ vẫn công khai",
    "report_hold": "Admin ẩn sau báo cáo; chủ shop không thể tự bật lại",
    "due_soon": "Sắp đến hạn 6 tháng; thử gia hạn",
    "expired": "Quá hạn, đã bị loại khỏi public trước khi cleanup",
    "retention_deleted": "Đã xóa nội dung/ảnh do retention",
    "owner_deleted": "Đã xóa nội dung/ảnh theo yêu cầu của chủ",
    "reapproved": "Admin duyệt → từ chối lại → khiếu nại → duyệt lại",
    "phone_hidden": "Không đồng ý công khai phone ở riêng tin này",
    "phone_withdrawn": "Rút consent phone ở nháp; snapshot cũ không được làm lộ số",
    "negotiable": "Giá thỏa thuận, không nhập số tiền",
    "free": "Cho tặng miễn phí",
    "retired_category": "Đã duyệt trước khi danh mục bị retire; hiện không public",
}
ROLE_LABELS = {
    "seller": "Chủ shop",
    "buyer": "Chỉ xem hàng, không có shop",
    "moderator": "Nhân viên duyệt tin + báo cáo + khóa shop",
    "catalog": "Nhân viên danh mục, không có quyền duyệt tin",
    "reports": "Nhân viên báo cáo, không có quyền ẩn tin/khóa shop",
    "inactive": "Tài khoản đã vô hiệu hóa trong kịch bản xóa",
}


def line(value):
    return str(value).replace("|", "/").replace("\n", " ")


def write_demo_guide(path, users, shops, listings, categories):
    visible = set(
        public_listings()
        .filter(pk__in=[item.pk for item in listings.values()])
        .values_list("pk", flat=True)
    )
    title_by_id = {
        item.pk: item.title or DEMO_PRODUCTS[username][index][0]
        for (username, index), item in listings.items()
    }
    category_names = {str(item.pk): item.name for item in categories.values()}
    rows = [
        "# Bộ dữ liệu demo Chobe",
        "",
        "> Đây là dữ liệu giả lập để review portfolio. Không có người bán, món hàng, cáo buộc, lượt xem hoặc giao dịch thật. Nội dung runtime dùng tiếng Anh và có nhãn Demo.",
        "",
        "## Đăng nhập nhanh",
        "",
        "- Trang đăng nhập: `http://localhost:4200/login` (đổi port nếu frontend của bạn dùng port khác).",
        f"- Mật khẩu chung của **tài khoản demo mới tạo**: `{DEMO_PASSWORD}`. Nếu bạn tự đổi mật khẩu sau đó, seed không đổi lại.",
        "- Các email dùng miền `demo.chobe.invalid`; phone dùng dải số hư cấu `+1 202 555 01xx`, không phải số người bán Việt Nam thật.",
        "- Tài khoản `admin` và các tài khoản có sẵn trước seed không bị đổi thông tin đăng nhập.",
        "- Không gọi AI, SMTP/SMS, không enqueue outbox, không bật worker. Export/deletion ở trạng thái chờ là snapshot mô phỏng, không phải tác vụ đang chạy thật.",
        "",
        "## Tổng quan",
        "",
        f"- {len(users)} tài khoản demo: 10 chủ shop, 5 người chỉ xem hàng, 3 staff có quyền khác nhau và 3 tài khoản vô hiệu hóa cho kịch bản xóa.",
        f"- {len(shops)} shop: "
        + ", ".join(
            f"{key}={value}"
            for key, value in sorted(
                Counter(shop.status for shop in shops.values()).items()
            )
        )
        + ".",
        f"- {len(listings)} kịch bản tin; hiện {len(visible)} tin đủ điều kiện công khai.",
        "- 8 danh mục gốc có sẵn được giữ lại; bổ sung nhánh demo và danh mục draft/restricted/retired.",
        "- Ảnh hàng là stock/ảnh minh họa được tái sử dụng từ prototype, không chứng minh mẫu hàng thật. Avatar/logo là hình minh họa; tên hiển thị và banner có nhãn Demo.",
        "- Lượt view/call/copy là số đếm giả lập. Các dòng favorite/follow trên nội dung nay không còn public mô phỏng việc người dùng đã lưu/theo dõi trước khi nội dung bị ẩn.",
        "",
        "## Danh sách tài khoản",
        "",
        "| Username | Tên hiển thị | Vai trò | Shop / trạng thái |",
        "|---|---|---|---|",
    ]
    for username, name, area, role, _, _ in DEMO_PEOPLE:
        user = users[username]
        shop = shops.get(username)
        rows.append(
            f"| `{username}` | {line(user.profile.display_name)} | {ROLE_LABELS[role]} | {line(shop.name) + ' / ' + shop.status if shop else 'Không có shop'} |"
        )
    rows.extend(
        [
            "",
            "## Review nhanh theo kịch bản",
            "",
            "1. **Khám phá/tìm kiếm:** mở `/`, `/search`, thử `Pixel`, `sofa`, `bicycle`, `books`; dùng bộ lọc danh mục/giá/khu vực. Các tin khác nhau có đủ để xem phân trang.",
            "2. **So sánh:** ba tin đầu của `demo_minh` cùng danh mục Phones, mở `/compare?ids=1101,1102,1103`. Chọn thêm một tin Furniture để xem lỗi khác danh mục.",
            "3. **Bản công khai tách nháp:** đăng nhập `demo_minh`, mở tin `1109`; bản sửa chờ duyệt trong khi người mua vẫn thấy bản cũ. `demo_lan` / `1209` có bản sửa bị từ chối; `demo_huy` / `1309` có nháp sửa chưa gửi.",
            "4. **Duyệt thủ công:** đăng nhập `demo_moderator`, mở `/admin/moderation`; lọc pending/rejected và open appeals, approve/reject kèm lý do. Tin `1110` đã có lịch sử admin đảo quyết định.",
            "5. **Báo cáo:** `demo_quang` đã báo cáo tin `1409`, admin ẩn tin và đặt hold. `demo_thao` không thể tự Show tin này. Cần sửa/gửi lại rồi admin duyệt.",
            "6. **Quyền staff:** `demo_reports` xem/xử lý báo cáo nhưng không có quyền hide listing hoặc suspend shop; `demo_catalog` chỉ quản lý danh mục. Dùng `/admin/reports`, `/admin/categories`, `/admin/moderation` để đối chiếu 403.",
            "7. **Shop không public:** `demo_bao` paused, `demo_an` suspended, `demo_nam` closed. Chủ vẫn đăng nhập và xem dữ liệu riêng; người mua không thấy storefront/tin công khai.",
            "8. **Privacy:** `demo_vy` không ghi lịch sử, không nhận alert. `demo_huy` và `demo_mai` đã rút consent phone toàn tài khoản. Tin `1210` tắt phone riêng; tin `1310` mô phỏng rút consent ở nháp.",
            "9. **Retention:** `demo_duc` / `1509` sắp đến hạn, có thể Renew; `demo_mai` / `1609` đã quá hạn và không public, `1610` đã bị xóa nội dung; `demo_linh` / `1710` đã xóa bởi chủ.",
            "10. **Inbox/saved search:** `demo_ha` có email opt-in nhưng seed không gửi thư; `demo_quang` chỉ inbox, gồm thông báo về tin nay đã ẩn; `demo_tuan` có một tìm kiếm paused.",
            "11. **Empty state:** `demo_trang` chưa có hoạt động marketplace: không shop, không follow/favorite/history/saved search/notification.",
            "12. **Export/xóa tài khoản:** xem trạng thái riêng ở `/account/privacy`; các receipt xóa và account inactive nằm ở phần cuối tài liệu. Không tạo session/token đăng nhập giả.",
            "",
            "## Chi tiết từng tài khoản",
            "",
            "Kịch bản là trạng thái seed ban đầu. Nếu bạn đã tự thay đổi dữ liệu khi review, cột trạng thái/public và thông tin tài khoản bên dưới lấy từ DB hiện hành; kịch bản ban đầu có thể đã thay đổi.",
            "",
        ]
    )
    for username, name, area, role, _, _ in DEMO_PEOPLE:
        user = users[username]
        profile, privacy = user.profile, user.privacy
        rows.extend(
            [
                f"### {username} — {profile.display_name}",
                "",
                f"- Đăng nhập: `{username}` / mật khẩu chung ở đầu tài liệu. "
                + (
                    "**Không đăng nhập được: account inactive.**"
                    if not user.is_active
                    else "Account đang active."
                ),
                f"- Email giả: `{user.email}`; khu vực: {profile.area}.",
                f"- Bio: {profile.bio}",
                "- Avatar: "
                + ("có hình minh họa" if profile.avatar else "chưa có")
                + f"; phone lưu trong profile: `{profile.phone or 'chưa nhập'}`.",
                f"- Privacy: chia sẻ phone **{'bật' if privacy.share_phone else 'tắt'}**; ghi lịch sử **{'bật' if privacy.record_history else 'tắt'}**.",
                f"- Vai trò: {ROLE_LABELS[role]}.",
                f"- Profile version `{profile.version}`; privacy version `{privacy.version}`.",
            ]
        )
        following = list(
            ShopFollow.objects.filter(user=user)
            .select_related("shop")
            .order_by("shop__slug")
        )
        rows.append(
            "- Đang theo dõi shop: "
            + (
                ", ".join(
                    f"{relation.shop.name} ({relation.shop.status})"
                    for relation in following
                )
                or "không có"
            )
            + "."
        )
        favorites = list(
            Favorite.objects.filter(user=user).values_list("listing_id", flat=True)
        )
        favorite_descriptions = []
        for pk in favorites:
            title = line(title_by_id.get(pk, "Tin ngoài bộ demo"))
            availability = (
                "đang public"
                if pk in visible
                else "không còn public, bị ẩn khỏi danh sách người mua"
            )
            favorite_descriptions.append(f"`{pk}` {title} [{availability}]")
        rows.append(
            "- Tin đã lưu: " + (", ".join(favorite_descriptions) or "không có") + "."
        )
        history = list(
            ViewingHistory.objects.filter(user=user).values_list(
                "listing_id", flat=True
            )
        )
        rows.append(
            "- Lịch sử đã ghi: "
            + (", ".join(f"`{pk}`" for pk in history) or "không có")
            + "."
        )
        preference = user.notificationpreference
        rows.append(
            f"- Thông báo: inbox **{'bật' if preference.inbox else 'tắt'}**, email **{'bật' if preference.email else 'tắt'}**; không có email nào được seed gửi ra."
        )
        if username in shops:
            shop = shops[username]
            rows.extend(
                [
                    f"- Shop: **{shop.name}**, trạng thái `{shop.status}`, khu vực {shop.area}.",
                    f"- Đường dẫn: `/shops/{shop.slug}`; giờ liên hệ {shop.contact_hours}. Có logo và banner minh họa.",
                    "- Địa chỉ cũ: "
                    + ", ".join(
                        f"`/shops/{slug}`"
                        for slug in shop.slugs.exclude(slug=shop.slug).values_list(
                            "slug", flat=True
                        )
                    )
                    + " (redirect khi shop đủ điều kiện public).",
                    "",
                    "| ID | Tin / danh mục | Trạng thái | Kịch bản | Public? |",
                    "|---|---|---|---|---|",
                ]
            )
            for index, product in enumerate(DEMO_PRODUCTS[username]):
                item = listings[(username, index)]
                story = (
                    (
                        "active",
                        "active",
                        "active",
                        "pending",
                        "rejected",
                        "draft",
                        "hidden",
                        "sold",
                    )[index]
                    if index < 8
                    else DEMO_SPECIAL_STORIES[username][index - 8]
                )
                price = (
                    "Thỏa thuận, chưa nhập giá"
                    if item.price is None
                    else f"{item.price:,} VND"
                )
                rows.append(
                    f"| `{item.pk}` | {line(item.title or 'Đã xóa: ' + product[0])}<br>{line(item.category.name if item.category_id else 'Nội dung/danh mục đã xóa')}<br>{price} | `{item.status}` | {STORY_LABELS[story]} | {'Có' if item.pk in visible else 'Không'} |"
                )
            rows.append("")
        else:
            rows.append("- Không có shop, không có tin bán.")
        searches = list(SavedSearch.objects.filter(user=user))
        if searches:
            rows.extend(["", "**Tìm kiếm đã lưu:**", ""])
            for search in searches:
                filters = {
                    key: category_names.get(value, value)
                    if key == "category"
                    else value
                    for key, value in search.filters.items()
                }
                rows.append(
                    f"- {search.name}: {line(filters)}; {'mỗi ngày' if search.frequency == 'daily' else 'khi có tin mới'}; {'đang bật' if search.active else 'tạm dừng'}."
                )
        for notification in Notification.objects.filter(user=user).select_related(
            "listing", "search"
        ):
            rows.append(
                f"- Inbox `{notification.pk}`: {notification.search.name} → tin `{notification.listing_id}`, {'đã đọc' if notification.read_at else 'chưa đọc'}, {'còn public' if notification.listing_id in visible else 'không còn public'}; email `{notification.email_status}` (trạng thái giả lập, không gửi thư)."
            )
        for report in Report.objects.filter(reporter=user):
            rows.append(
                f"- Báo cáo `{report.pk}`: {report.reason}, `{report.status}`, đối tượng "
                + (
                    f"tin `{report.listing_id}`"
                    if report.listing_id
                    else f"shop `{report.shop.slug}`"
                )
                + "."
            )
        for export in AccountDataExport.objects.filter(user=user):
            rows.append(
                f"- Export `{export.pk}`: `{export.status}`"
                + (
                    " — tải được snapshot dữ liệu của chính tài khoản này trong thời hạn."
                    if export.status == "ready"
                    else " — trạng thái mô phỏng, không có job nền tự chạy."
                )
            )
        if user.is_staff:
            rows.append(
                "- Quyền Django: "
                + ", ".join(
                    f"`{permission}`"
                    for permission in sorted(user.get_all_permissions())
                )
                + "."
            )
        rows.append("")
    rows.extend(
        [
            "## Danh mục và mô hình dữ liệu",
            "",
            "| Danh mục | Trạng thái | Nháp / public version |",
            "|---|---|---|",
        ]
    )
    for category in categories.values():
        rows.append(
            f"| {line(category.name)} (`{category.slug}`) | `{category.status}`"
            + (" / restricted" if category.restricted else "")
            + f" | {category.version} / {category.published.get('version', 'chưa publish')} |"
        )
    rows.extend(
        [
            "",
            "**Các model nghiệp vụ có dữ liệu:**",
            "",
            "- Accounts: User, Profile, PrivacySettings, ConsentEvent, ViewingHistory, AccountDataExport (đủ 5 trạng thái), DeletionRequest (đủ 4 trạng thái).",
            "- Shops: Shop (đủ 4 trạng thái), ShopSlug (địa chỉ cũ/mới), ShopAuditEvent, ShopFollow.",
            "- Categories: Category, CategoryRevision, CategoryAuditEvent; có nháp chưa publish, restricted, retired và public snapshot khác nháp.",
            "- Listings: Listing (đủ 7 trạng thái), ListingImage, ListingRevision, ModerationCase, ListingAuditEvent, Favorite, SavedSearch, NotificationPreference, Notification, Report, ReportDecision, ListingMetric.",
            "- Notification có đủ blocked/queued/sending/sent/failed dưới dạng trạng thái **mô phỏng**; kể cả sent cũng không phải bằng chứng gửi thư thật. Không có outbox chạy các dòng queued/sending này.",
            "- Không tạo session, access token, mật khẩu reset, kết quả AI giả, hoặc job outbox có thể gửi thông tin ra ngoài. Bảng hạ tầng không phải dữ liệu demo nghiệp vụ.",
            "",
            "## Receipt xóa tài khoản",
            "",
            "| Receipt | Account | Trạng thái |",
            "|---|---|---|",
        ]
    )
    for receipt in DeletionRequest.objects.filter(
        pk__in=[
            uuid5(NAMESPACE_URL, f"chobe-demo-v1/deletion/{status}")
            for status in ("requested", "processing", "failed", "completed")
        ]
    ).select_related("user"):
        rows.append(
            f"| `{receipt.pk}` | {receipt.user.username if receipt.user else 'Account đã xóa; receipt không giữ user'} | `{receipt.status}` |"
        )
    rows.extend(
        [
            "",
            "## Chạy lại seed",
            "",
            "Từ thư mục `backend`:",
            "",
            "```bash",
            "DJANGO_DEMO_MODE=true uv run python manage.py seed_demo_marketplace",
            "```",
            "",
            "- Command tự backup SQLite vào `backend/backups/` trước khi ghi. Không flush/xóa DB, không đổi tài khoản có sẵn.",
            "- Chạy lại không nhân đôi dữ liệu và không reset mật khẩu/profile/tin đã chỉnh khi review; tài liệu này được render lại từ DB hiện hành.",
            "- Các quan hệ follow/favorite/history hoặc dữ liệu demo đã xóa có thể được bổ sung lại khi chạy seed; các bản ghi còn tồn tại không bị cập nhật đè. Đây là seed bổ sung, không phải chức năng reset về nguyên trạng.",
            "- Nếu đổi tên/xóa tay một phần dữ liệu demo, seed không có chức năng reset phá hủy. Xung đột namespace với dữ liệu không thuộc demo sẽ dừng và rollback.",
            "- Nếu chạy worker thật sau đó, các dữ liệu đã quá hạn có thể được cleanup theo policy. Đó là hành vi hệ thống thật; bộ seed không tự giữ tin quá hạn ở public.",
            "",
            "## Số liệu snapshot",
            "",
            "- Trạng thái tin: "
            + ", ".join(
                f"{key}={value}"
                for key, value in sorted(
                    Counter(item.status for item in listings.values()).items()
                )
            )
            + ".",
            f"- Tin có thể xem công khai lúc ghi tài liệu: {len(visible)}.",
            "- Dữ liệu và timestamp là kịch bản giả lập; không phải lịch sử giao dịch hoặc bằng chứng hoạt động thật.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows), encoding="utf-8")
