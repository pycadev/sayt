from django.urls import path
from .views import leadership_view, student_view

urlpatterns = [
    path('leadership/', leadership_view, name='leadership'),
    path('student/', student_view, name='students'),
]
