import uuid
from django.db import models

def certificate_upload_path(instance, filename):
    return f"sertificate/{instance.id}-{instance.uuid}/{filename}"

class Certificate(models.Model):
    title = models.CharField(max_length=255)
    pdf = models.FileField(upload_to=certificate_upload_path)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    qr_code = models.ImageField(upload_to="qr_codes/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title