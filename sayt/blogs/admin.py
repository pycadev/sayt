# blogs/admin.py
from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from ckeditor_uploader.widgets import CKEditorUploadingWidget

from .models import Category, Tag, Post, Comment, LikeDislike


# =====================================================
# Post uchun forma — CKEditor + majburiy rasm
# =====================================================
class PostAdminForm(forms.ModelForm):
    body = forms.CharField(
        widget=CKEditorUploadingWidget(),
        label="Matn (Word kabi formatlash mumkin)"
    )

    class Meta:
        model = Post
        fields = '__all__'

    def clean_main_image(self):
        image = self.cleaned_data.get('main_image')
        if not image and not self.instance.pk:  # Yangi maqola bo‘lsa
            raise forms.ValidationError("Asosiy rasm majburiy!")
        return image


# =====================================================
# POST — Maqola admini (ENG MUHIMI!)
# =====================================================
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
    list_display = ('title', 'author_link', 'category', 'published_status', 'featured_badge', 'views', 'likes', 'comments', 'published_at')
    list_filter = ('is_published', 'is_featured', 'category', 'tags', 'published_at')
    search_fields = ('title', 'body', 'author__username', 'author__first_name', 'author__last_name')
    prepopulated_fields = {"slug": ("title",)}  # Admin avto to‘ldiradi
    filter_horizontal = ('tags',)
    readonly_fields = ('views', 'published_at', 'updated_at')
    autocomplete_fields = ['author']  # Qidiriladigan muallif!

    fieldsets = (
        ("Asosiy", {
            'fields': ('title', 'slug', 'author', 'main_image', 'category', 'tags')
        }),
        ("Matn", {
            'fields': ('body',),
        }),
        ("Nashr", {
            'fields': ('is_published', 'is_featured'),
            'classes': ('collapse',)
        }),
        ("Statistika", {
            'fields': ('views', 'published_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # MUALLIFNI LINK QILISH — Django 5.2 uchun to‘g‘ri!
    def author_link(self, obj):
        if not obj.author:
            return "-"
        url = f"/admin/auth/user/{obj.author.id}/change/"
        full_name = obj.author.get_full_name() or obj.author.username
        return format_html('<a href="{}"><strong>{}</strong></a>', url, full_name)
    author_link.short_description = "Muallif"
    author_link.admin_order_field = 'author'

    # Holat badge
    def published_status(self, obj):
        color = "success" if obj.is_published else "secondary"
        text = "Nashr qilingan" if obj.is_published else "Qoralama"
        return format_html('<span class="badge bg-{}">{}</span>', color, text)
    published_status.short_description = "Holati"

    # Tanlangan badge
    def featured_badge(self, obj):
        if obj.is_featured:
            return format_html('<span class="badge bg-warning text-dark">Tanlangan</span>')
        return "—"
    featured_badge.short_description = "Tanlangan"

    # Like va izohlar
    def likes(self, obj):
        return obj.total_likes()
    likes.short_description = "Like"

    def comments(self, obj):
        return obj.total_comments()
    comments.short_description = "Izoh"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author', 'category')


# =====================================================
# CATEGORY
# =====================================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'post_count')
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ('name',)

    def post_count(self, obj):
        count = obj.posts.count()
        url = reverse("admin:blogs_post_changelist") + f"?category__id__exact={obj.id}"
        return format_html('<a href="{}">{}</a>', url, count)
    post_count.short_description = "Maqolalar"


# =====================================================
# TAG
# =====================================================
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'post_count')
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ('name',)

    def post_count(self, obj):
        count = obj.posts.count()
        url = reverse("admin:blogs_post_changelist") + f"?tags__id__exact={obj.id}"
        return format_html('<a href="{}">{}</a>', url, count)
    post_count.short_description = "Maqolalar"


# =====================================================
# COMMENT
# =====================================================
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('post_link', 'author', 'short_content', 'created_at', 'is_approved')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('author__username', 'content', 'post__title')
    readonly_fields = ('created_at', 'post', 'author')

    def post_link(self, obj):
        url = reverse("admin:blogs_post_change", args=[obj.post.id])
        return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.post.title[:50])
    post_link.short_description = "Maqola"

    def short_content(self, obj):
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content
    short_content.short_description = "Izoh"

    def has_add_permission(self, request):
        return False  # Faqat saytda izoh qoldiriladi


# =====================================================
# LIKE/DISLIKE
# =====================================================
@admin.register(LikeDislike)
class LikeDislikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'object_id', 'value_display')
    list_filter = ('value', 'content_type')
    search_fields = ('user__username',)

    def value_display(self, obj):
        return "Like" if obj.value == 1 else "Dislike"
    value_display.short_description = "Harakat"

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False