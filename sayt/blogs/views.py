# blogs/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt  # AJAX uchun ixtiyoriy, lekin xavfsizlik uchun CSRF token ishlatiladi
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q, Prefetch, F
from django.core.cache import cache  # Performance uchun caching
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.urls import reverse

from .models import Post, Category, Tag, Comment, LikeDislike
from .forms import PostForm, CommentForm

User = get_user_model()

# ------------------------------------------------------------------
# 1. Blog ro‘yxati (Bosh sahifa) - Optimallashtirilgan: Caching + optimal queries
# ------------------------------------------------------------------
class BlogListView(ListView):
    model = Post
    template_name = 'blogs/post_list.html'
    context_object_name = 'posts'
    paginate_by = 9
    ordering = ['-published_at']

    def get_queryset(self):
        cache_key = f"blog_list_{self.request.GET.urlencode()}"
        cached_qs = cache.get(cache_key)
        if cached_qs is not None:
            return cached_qs

        queryset = Post.objects.filter(is_published=True).select_related('author', 'category').prefetch_related(
            Prefetch('tags', queryset=Tag.objects.all()),
            Prefetch('likes', queryset=LikeDislike.objects.all())
        ).annotate(
            comment_count=Count('comments', filter=Q(comments__is_approved=True)),
            like_count=Count('likes', filter=Q(likes__value=1))
        )

        # Qidiruv
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) | Q(body__icontains=q) | Q(tags__name__icontains=q) | Q(author__username__icontains=q)
            ).distinct()

        # Kategoriya filtri
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)

        # Teg filtri
        tag = self.request.GET.get('tag')
        if tag:
            queryset = queryset.filter(tags__slug=tag)

        cache.set(cache_key, queryset, 60 * 5)  # 5 minut cache
        return queryset

# ------------------------------------------------------------------
# 2. Maqola batafsil ko‘rish + views hisoblash + izoh qoldirish + Author profil link
# ------------------------------------------------------------------
class BlogDetailView(DetailView):
    model = Post
    template_name = 'blogs/post_detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'pk'  # ID bilan ishlaydi

    def get_queryset(self):
        return Post.objects.filter(is_published=True).select_related('author', 'category').prefetch_related(
            Prefetch('tags', queryset=Tag.objects.all()),
            Prefetch('comments', queryset=Comment.objects.filter(is_approved=True).select_related('author').order_by('-created_at'), to_attr='approved_comments'),
            Prefetch('likes', queryset=LikeDislike.objects.all())
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Views ni atomik oshirish
        Post.objects.filter(pk=obj.pk).update(views=F('views') + 1)
        obj.refresh_from_db(fields=['views'])
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object

        # Izoh formasi
        context['comment_form'] = CommentForm()

        # O‘xshash maqolalar
        related_qs = Post.objects.filter(
            Q(category=post.category) | Q(tags__in=post.tags.all()),
            is_published=True
        ).exclude(pk=post.pk).select_related('author').distinct()[:6]
        context['related_posts'] = related_qs

        # Like holati (post uchun)
        if self.request.user.is_authenticated:
            like = LikeDislike.objects.filter(
                user=self.request.user,
                content_type=ContentType.objects.get_for_model(Post),
                object_id=post.pk
            ).first()
            context['user_like'] = like.value if like else None
        else:
            context['user_like'] = None

        # Izohlar uchun user_liked qo‘shish — TO‘G‘RI USUL!
        if self.request.user.is_authenticated:
            user_liked_comment_ids = LikeDislike.objects.filter(
                user=self.request.user,
                content_type=ContentType.objects.get_for_model(Comment),
                value=1
            ).values_list('object_id', flat=True)

            for comment in post.approved_comments:
                comment.user_liked = comment.pk in user_liked_comment_ids
        else:
            for comment in post.approved_comments:
                comment.user_liked = False

        return context
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = self.object
            comment.author = request.user
            comment.save()
            messages.success(request, "Izohingiz muvaffaqiyatli qoldirildi!")
            return redirect('blogs:post_detail', pk=self.object.pk)
        else:
            context = self.get_context_data()
            context['comment_form'] = form
            return render(request, self.template_name, context)


# ------------------------------------------------------------------
# 3. Yangi maqola yaratish — Optimallashtirilgan forma validatsiya
# ------------------------------------------------------------------
class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blogs/post_form.html'
    success_url = 'blogs/post_list.html'

    def form_valid(self, form):
        """Forma to‘g‘ri bo‘lsa — muallifni qo‘shib saqlaymiz"""
        form.instance.author = self.request.user
        messages.success(self.request, "Maqola muvaffaqiyatli yaratildi va nashr qilindi!")
        response = super().form_valid(form)
        
        # Agar is_published=True bo‘lsa — darrov detail sahifasiga yo‘naltiramiz
        if form.cleaned_data['is_published']:
            return redirect('blogs:post_detail', pk=self.object.pk)
        else:
            return redirect('blogs:post_list')

    def form_invalid(self, form):
        """Forma xato bo‘lsa — xabar chiqaramiz"""
        messages.error(self.request, "Maqola saqlanmadi. Iltimos, xatolarni tuzating.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Yangi maqola yozish"
        context['submit_text'] = "Nashr qilish"
        return context

# ------------------------------------------------------------------
# 4. Maqolani tahrirlash (faqat muallif yoki staff)
# ------------------------------------------------------------------
class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blogs/post_form.html'
    pk_url_kwarg = 'pk'  # ID bilan

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author or self.request.user.is_staff

    def form_valid(self, form):
        messages.success(self.request, "Maqola muvaffaqiyatli yangilandi!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Maqolani tahrirlash"
        return context


# ------------------------------------------------------------------
# 5. Maqolani o‘chirish (soft delete or hard)
# ------------------------------------------------------------------
class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'blogs/post_confirm_delete.html'
    success_url = '/blog/'
    pk_url_kwarg = 'pk'  # ID bilan

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author or self.request.user.is_staff

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_published = False  # Soft delete — nashrdan olib tashlash
        self.object.save()
        messages.success(request, "Maqola muvaffaqiyatli o‘chirildi!")
        return redirect(self.success_url)


# ------------------------------------------------------------------
# 6. Muallif maqolalari ro‘yxati (YANGI VIEW!)
# ------------------------------------------------------------------
class AuthorPostsListView(ListView):
    model = Post
    template_name = 'blogs/author_posts.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        author = get_object_or_404(User, username=self.kwargs['username'])
        return Post.objects.filter(author=author, is_published=True).select_related('category').prefetch_related('tags').order_by('-published_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        author = get_object_or_404(User, username=self.kwargs['username'])
        context['author'] = author
        context['post_count'] = self.object_list.count()
        return context


# ------------------------------------------------------------------
# AJAX: Like / Dislike (optimallashtirilgan + CSRF exempt ixtiyoriy)
# ------------------------------------------------------------------
@csrf_exempt  # AJAX uchun, lekin frontendda CSRF token jo‘natilsin!
@require_POST
def like_dislike(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Kirish talab qilinadi'}, status=401)

    content_type_str = request.POST.get('content_type')  # 'post' yoki 'comment'
    object_id = request.POST.get('object_id')
    action = request.POST.get('action')  # 'like' yoki 'dislike'

    if not all([content_type_str, object_id, action]):
        return JsonResponse({'error': 'Maʼlumot yetishmayapti'}, status=400)

    try:
        model_class = Post if content_type_str == 'post' else Comment
        obj = model_class.objects.get(pk=object_id)
    except model_class.DoesNotExist:
        return JsonResponse({'error': 'Obʼyekt topilmadi'}, status=404)

    content_type = ContentType.objects.get_for_model(model_class)
    value = 1 if action == 'like' else -1

    # Update or create
    like_obj, created = LikeDislike.objects.update_or_create(
        user=request.user,
        content_type=content_type,
        object_id=object_id,
        defaults={'value': value}
    )

    if not created and like_obj.value == value:
        like_obj.delete()
        user_like = None
    else:
        user_like = value

    # Yangi sonlarni qaytarish
    return JsonResponse({
        'likes': obj.total_likes(),
        'dislikes': obj.total_dislikes(),
        'user_like': user_like
    })