from django.urls import path
from . import views

app_name = 'blogs'

urlpatterns = [
    path('', views.BlogListView.as_view(), name='post_list'),
    path('post/<int:pk>/', views.BlogDetailView.as_view(), name='post_detail'), 
    path('post/new/', views.PostCreateView.as_view(), name='post_create'),
    path('post/<int:pk>/edit/', views.PostUpdateView.as_view(), name='post_update'),
    path('post/<int:pk>/delete/', views.PostDeleteView.as_view(), name='post_delete'),
    path('author/<str:username>/', views.AuthorPostsListView.as_view(), name='author_posts'),
    path('like/', views.like_dislike, name='like_dislike'),
]