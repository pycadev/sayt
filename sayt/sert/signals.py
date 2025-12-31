import qrcode
from io import BytesIO
from django.core.files import File
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Certificate

def generate_qr_for_instance(instance):
    """Berilgan sertifikat uchun QR kod yaratish"""
    if not instance.qr_code:
        url = f"https://airforce.uz/c/{instance.uuid}/"
        qr = qrcode.make(url)

        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        buffer.seek(0)

        instance.qr_code.save(
            f"qr_{instance.id}.png",
            File(buffer),
            save=True
        )

# 1️⃣ Signals - yangi Certificate yaratilganda
@receiver(post_save, sender=Certificate)
def generate_qr_on_save(sender, instance, created, **kwargs):
    if created:
        generate_qr_for_instance(instance)

# 2️⃣ Management script - bazadagi barcha QR-larsiz Certificate-larni yaratish
def generate_qr_for_all_missing():
    for cert in Certificate.objects.filter(qr_code__isnull=True):
        generate_qr_for_instance(cert)
        print(f"QR kod yaratildi: {cert.id} - {cert.title}")
