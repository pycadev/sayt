from django.shortcuts import get_object_or_404
from django.http import FileResponse
from .models import Certificate

def certificate_view(request, uuid):
    cert = get_object_or_404(Certificate, uuid=uuid)
    return FileResponse(cert.pdf.open(), content_type='application/pdf')