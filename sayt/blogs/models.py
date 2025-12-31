# blogs/models.py
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse
from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType


# ------------------------------------------------------------------
# Kategoriyalar va Teglar (oldingidek)
# ------------------------------------------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Kategoriya nomi")
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=70, unique=True, verbose_name="Teg nomi")
    slug = models.SlugField(max_length=90, unique=True, blank=True)

    class Meta:
        verbose_name = "Teg"
        verbose_name_plural = "Teglar"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ------------------------------------------------------------------
# Like / Dislike uchun universal model (Post va Comment ga ham ishlaydi)
# ------------------------------------------------------------------
class LikeDislike(models.Model):
    LIKE = 1
    DISLIKE = -1
    VALUE_CHOICES = (
        (LIKE, 'Like'),
        (DISLIKE, 'Dislike'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    value = models.SmallIntegerField(choices=VALUE_CHOICES)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericRelation('LikeDislike', related_query_name='likes')  # Generic relation

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.user} → {self.value}"


# ------------------------------------------------------------------
# Post (Maqola) — like, dislike, views, comments_count bilan
# ------------------------------------------------------------------
class Post(models.Model):
    title = models.CharField(max_length=250, verbose_name="Sarlavha")
    slug = models.SlugField(max_length=270, unique=True, blank=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_posts',
        verbose_name="Muallif"
    )

    main_image = models.ImageField(
        upload_to='blog/main_images/{author.id}',
        verbose_name="Asosiy rasm",
        help_text="Majburiy muqova rasmi",
        blank=False,
        null=False 
    )

    body = RichTextUploadingField(verbose_name="Matn")

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')

    is_published = models.BooleanField(default=True, verbose_name="Nashr qilingan")
    is_featured = models.BooleanField(default=False, verbose_name="Tanlangan")

    published_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Statistikalar
    views = models.PositiveIntegerField(default=0, verbose_name="Ko‘rishlar soni")
    likes = GenericRelation(LikeDislike, related_query_name='post_likes')

    class Meta:
        verbose_name = "Maqola"
        verbose_name_plural = "Maqolalar"
        ordering = ['-published_at']

    def save(self, *args, **kwargs):
        if not self.slug:  # Agar slug bo‘sh bo‘lsa (yangi maqola)
            base_slug = slugify(self.title, allow_unicode=True)
            slug = base_slug
            counter = 1
            
            # Takrorlansa -1, -2, -3 qo‘shib boramiz
            while Post.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'slug': self.slug})

    # Helper metodlar
    def total_likes(self):
        return self.likes.filter(value=1).count()

    def total_dislikes(self):
        return self.likes.filter(value=-1).count()

    def total_comments(self):
        return self.comments.filter(is_approved=True).count()

    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])


# ------------------------------------------------------------------
# Izohlar — o‘ziga ham like/dislike qo‘shildi
# ------------------------------------------------------------------
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name="Maqola")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_comments',
        verbose_name="Izoh muallifi"
    )
    content = models.TextField(verbose_name="Izoh matni")
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=True, verbose_name="Tasdiqlangan")

    # Izohga ham like/dislike
    likes = GenericRelation(LikeDislike, related_query_name='comment_likes')

    class Meta:
        verbose_name = "Izoh"
        verbose_name_plural = "Izohlar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.author} → {self.post.title[:30]}"

    def total_likes(self):
        return self.likes.filter(value=1).count()

    def total_dislikes(self):
        return self.likes.filter(value=-1).count()