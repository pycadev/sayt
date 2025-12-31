from django.contrib import admin
from django.utils.html import format_html
from .models import Certificate

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("title", "uuid", "created_at", "qr_preview")
    readonly_fields = ("uuid", "qr_preview")

    # QR kodni ko'rsatish
    def qr_preview(self, obj):
        if obj.qr_code:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" width="100" height="100" style="object-fit:contain;"/>'
                '</a>',
                obj.qr_code.url,  # link orqali ochish / yuklab olish mumkin
                obj.qr_code.url
            )
        return "QR kod hali yaratilmagan"

    qr_preview.short_description = "QR Kod"