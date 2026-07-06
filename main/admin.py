from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from .models import Category, Size, Product, ProductImage, ProductSize


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'color', 'price']
    list_filter = ['category', 'color']
    search_fields = ['name', 'color', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductSizeInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'slug',
        'display_order',
        'is_visible',
        'products_count',
        'catalog_image_preview',
    ]
    list_editable = ['display_order', 'is_visible']
    list_filter = ['is_visible']
    search_fields = ['name', 'slug']
    ordering = ['display_order', 'id']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['catalog_image_preview']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(products_total=Count('products'))

    @admin.display(description='Товаров', ordering='products_total')
    def products_count(self, obj):
        return obj.products_total

    @admin.display(description='Обложка')
    def catalog_image_preview(self, obj):
        if not obj.catalog_image:
            return '—'
        return format_html(
            '<img src="{}" alt="" style="width: 56px; height: 72px; object-fit: cover; border-radius: 4px;">',
            obj.catalog_image.url,
        )


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['name']
