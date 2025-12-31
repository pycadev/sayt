from django.shortcuts import render

def leadership_view(request):
    return render(request, 'pages/leadership.html')

def student_view(request):
    return render(request, 'pages/student.html')