import re
import shutil
import tempfile
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Category, Product, ProductSize, Size


TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class MainRenderingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Hoodies', slug='hoodies')
        cls.size = Size.objects.create(name='M')
        cls.product = Product.objects.create(
            name='Noctis Hoodie',
            slug='noctis-hoodie',
            category=cls.category,
            color='Black',
            price=Decimal('120.00'),
            description='Dark cotton hoodie.',
            main_image=SimpleUploadedFile(
                'noctis.jpg',
                b'test-image-content',
                content_type='image/jpeg',
            ),
            is_featured=True,
        )
        ProductSize.objects.create(
            product=cls.product,
            size=cls.size,
            stock=3,
        )

    def create_featured_product(self, number):
        return Product.objects.create(
            name=f'Featured Piece {number}',
            slug=f'featured-piece-{number}',
            category=self.category,
            color='Black',
            price=Decimal('150.00') + number,
            description=f'Featured product {number}.',
            main_image=SimpleUploadedFile(
                f'featured-{number}.jpg',
                b'test-image-content',
                content_type='image/jpeg',
            ),
            is_featured=True,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def assert_full_page(self, response):
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn('<html', content)
        self.assertIn('<footer', content)
        self.assertEqual(content.count('id="main-content"'), 1)

    def assert_htmx_partial(self, response):
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('<html', content)
        self.assertNotIn('<footer', content)

    def assert_no_duplicate_ids(self, response):
        content = response.content.decode()
        ids = re.findall(r'id="([^"]+)"', content)
        self.assertEqual(len(ids), len(set(ids)))

    def assert_home_has_no_removed_editorial_copy(self, response):
        self.assertNotContains(response, 'NEW DROP / 01')
        self.assertNotContains(response, 'OBSCURA')
        self.assertNotContains(response, 'AUTUMN — WINTER 2026')
        self.assertNotContains(response, 'MANIFESTO / 02')
        self.assertNotContains(response, 'BORN IN DARKNESS')
        self.assertNotContains(response, 'DESIGNED FOR THOSE WHO REFUSE TO DISAPPEAR')

    def count_home_product_cards(self, content):
        return len(re.findall(r'class="home-product-card(?:\s|")', content))

    def test_full_get_home(self):
        response = self.client.get(reverse('main:index'))

        self.assert_full_page(response)
        self.assertContains(response, 'РОЖДЕНО В ТЕМНОТЕ')
        self.assertContains(response, 'НОВАЯ КОЛЛЕКЦИЯ')
        self.assertNotContains(response, 'СМОТРЕТЬ ПО КАТЕГОРИЯМ')
        self.assertNotContains(response, 'home-categories')
        self.assertNotContains(response, 'home-category-link')
        self.assert_home_has_no_removed_editorial_copy(response)
        self.assert_no_duplicate_ids(response)

    def test_full_get_catalog(self):
        response = self.client.get(reverse('main:catalog_all'))

        self.assert_full_page(response)
        self.assertContains(response, 'КАТАЛОГ')
        self.assertNotContains(response, 'РОЖДЕНО В ТЕМНОТЕ')

    def test_full_get_category(self):
        response = self.client.get(
            reverse('main:catalog', kwargs={'category_slug': self.category.slug})
        )

        self.assert_full_page(response)
        self.assertContains(response, self.product.name)
        self.assertNotContains(response, 'РОЖДЕНО В ТЕМНОТЕ')

    def test_full_get_product_detail(self):
        response = self.client.get(
            reverse('main:product_detail', kwargs={'slug': self.product.slug})
        )

        self.assert_full_page(response)
        self.assertContains(response, self.product.name.upper())
        self.assertContains(response, self.product.description)
        self.assertNotContains(response, 'РОЖДЕНО В ТЕМНОТЕ')

    def test_htmx_get_home(self):
        response = self.client.get(
            reverse('main:index'),
            HTTP_HX_REQUEST='true',
        )

        self.assert_htmx_partial(response)
        self.assertContains(response, 'РОЖДЕНО В ТЕМНОТЕ')
        self.assertContains(response, 'НОВАЯ КОЛЛЕКЦИЯ')
        self.assertNotContains(response, 'СМОТРЕТЬ ПО КАТЕГОРИЯМ')
        self.assertNotContains(response, 'home-categories')
        self.assertNotContains(response, 'home-category-link')
        self.assert_home_has_no_removed_editorial_copy(response)
        self.assertNotContains(response, 'href="#"')
        self.assert_no_duplicate_ids(response)

    def test_htmx_get_catalog(self):
        response = self.client.get(
            reverse('main:catalog_all'),
            HTTP_HX_REQUEST='true',
        )

        self.assert_htmx_partial(response)
        self.assertContains(response, 'КАТАЛОГ')

    def test_htmx_get_category(self):
        response = self.client.get(
            reverse('main:catalog', kwargs={'category_slug': self.category.slug}),
            HTTP_HX_REQUEST='true',
        )

        self.assert_htmx_partial(response)
        self.assertContains(response, self.product.name)

    def test_htmx_get_product_detail(self):
        response = self.client.get(
            reverse('main:product_detail', kwargs={'slug': self.product.slug}),
            HTTP_HX_REQUEST='true',
        )

        self.assert_htmx_partial(response)
        self.assertContains(response, self.product.name.upper())
        self.assertContains(response, self.product.description)

    def test_home_featured_empty_state(self):
        Product.objects.update(is_featured=False)

        response = self.client.get(reverse('main:index'), HTTP_HX_REQUEST='true')

        self.assertContains(response, 'ТОВАРЫ ПОЯВЯТСЯ СКОРО')
        self.assertNotContains(response, 'class="home-product-card')
        self.assertNotContains(response, 'СМОТРЕТЬ ВСЕ →')

    def test_home_featured_one_product_state(self):
        Product.objects.update(is_featured=False)
        product = self.create_featured_product(1)

        response = self.client.get(reverse('main:index'), HTTP_HX_REQUEST='true')
        content = response.content.decode()

        self.assertContains(response, product.name.upper())
        self.assertEqual(self.count_home_product_cards(content), 1)

    def test_home_featured_two_products_state(self):
        Product.objects.update(is_featured=False)
        self.create_featured_product(1)
        self.create_featured_product(2)

        response = self.client.get(reverse('main:index'), HTTP_HX_REQUEST='true')
        content = response.content.decode()

        self.assertEqual(self.count_home_product_cards(content), 2)

    def test_home_featured_uses_max_three_products(self):
        Product.objects.update(is_featured=False)
        for number in range(1, 5):
            self.create_featured_product(number)

        response = self.client.get(reverse('main:index'), HTTP_HX_REQUEST='true')
        content = response.content.decode()

        self.assertEqual(self.count_home_product_cards(content), 3)
