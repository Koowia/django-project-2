import re
import shutil
import tempfile
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Category, Product, ProductSize, Size
from users.forms import CustomUserCreationForm


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

    def create_product_for_category(self, category, number):
        return Product.objects.create(
            name=f'{category.slug} Product {number}',
            slug=f'{category.slug}-product-{number}',
            category=category,
            color='Black',
            price=Decimal('100.00') + number,
            description=f'Catalog product {number}.',
            main_image=SimpleUploadedFile(
                f'{category.slug}-{number}.jpg',
                b'test-image-content',
                content_type='image/jpeg',
            ),
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

    def count_catalog_category_cards(self, content):
        return len(re.findall(r'class="catalog-card(?:\s|")', content))

    def assert_ordered(self, content, expected_items):
        positions = [content.index(item) for item in expected_items]
        self.assertEqual(positions, sorted(positions))

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

    def test_footer_legal_links_have_current_labels_and_order(self):
        response = self.client.get(reverse('main:index'))
        content = response.content.decode()

        expected_links = (
            'ОБРАБОТКА ПЕРСОНАЛЬНЫХ ДАННЫХ',
            'ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ',
            'ПОЛЬЗОВАТЕЛЬСКОЕ СОГЛАШЕНИЕ',
            'ОПЛАТА И ДОСТАВКА',
            'ПУБЛИЧНАЯ ОФЕРТА',
            'ВОЗВРАТ И ОБМЕН',
        )
        self.assert_ordered(content, expected_links)
        self.assertContains(response, reverse('main:personal_data_consent'))
        self.assertContains(response, reverse('main:privacy_policy'))
        self.assertContains(response, reverse('main:user_agreement'))
        self.assertContains(response, reverse('main:payment_delivery'))
        self.assertContains(response, reverse('main:public_offer'))
        self.assertContains(response, reverse('main:returns_exchange'))
        self.assertNotContains(response, 'СОГЛАСИЕ НА ОБРАБОТКУ ПЕРСОНАЛЬНЫХ ДАННЫХ</a>')

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

    def test_full_get_login_contains_shared_layout(self):
        response = self.client.get(reverse('users:login'))
        content = response.content.decode()

        self.assert_full_page(response)
        self.assertIn('<header', content)
        self.assertContains(response, 'id="loginForm"')
        self.assertContains(response, 'ВХОД')
        self.assertContains(response, 'Введите email')
        self.assertContains(response, 'Введите пароль')
        self.assertNotContains(response, '← НА ГЛАВНУЮ')

    def test_full_get_register_contains_shared_layout(self):
        response = self.client.get(reverse('users:register'))
        content = response.content.decode()

        self.assert_full_page(response)
        self.assertIn('<header', content)
        self.assertContains(response, 'id="createAccountForm"')
        self.assertContains(response, 'РЕГИСТРАЦИЯ')
        self.assertContains(response, 'Введите имя')
        self.assertContains(response, 'Повторите пароль')
        self.assertContains(response, 'personal_data_consent')
        self.assertContains(response, 'user_agreement_consent')
        self.assertContains(response, reverse('main:personal_data_consent'))
        self.assertContains(response, reverse('main:user_agreement'))
        self.assertContains(response, reverse('main:privacy_policy'))
        self.assertNotContains(response, '← НА ГЛАВНУЮ')

    def test_full_get_legal_document(self):
        response = self.client.get(reverse('main:personal_data_consent'))

        self.assert_full_page(response)
        self.assertContains(response, 'СОГЛАСИЕ НА ОБРАБОТКУ ПЕРСОНАЛЬНЫХ ДАННЫХ')
        self.assertContains(response, 'Документ находится в подготовке')

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

    def test_catalog_index_hides_invisible_categories(self):
        Category.objects.create(
            name='Hidden Category',
            slug='hidden-category',
            is_visible=False,
        )

        response = self.client.get(reverse('main:catalog_all'), HTTP_HX_REQUEST='true')

        self.assertContains(response, self.category.name)
        self.assertNotContains(response, 'Hidden Category')

    def test_catalog_index_orders_categories_by_display_order(self):
        self.category.display_order = 20
        self.category.save(update_fields=['display_order'])
        early_category = Category.objects.create(
            name='Early Category',
            slug='early-category',
            display_order=5,
        )

        response = self.client.get(reverse('main:catalog_all'), HTTP_HX_REQUEST='true')
        content = response.content.decode()

        self.assertLess(content.index(early_category.name), content.index(self.category.name))

    def test_catalog_index_category_counts_are_dynamic(self):
        self.create_product_for_category(self.category, 2)

        response = self.client.get(reverse('main:catalog_all'), HTTP_HX_REQUEST='true')

        self.assertContains(response, '2 товара')
        self.assertNotContains(response, '01 ТОВАР')

    def test_catalog_index_renders_without_category_image(self):
        self.category.catalog_image = ''
        self.category.save(update_fields=['catalog_image'])

        response = self.client.get(reverse('main:catalog_all'), HTTP_HX_REQUEST='true')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'catalog-card__fallback')
        self.assertContains(response, self.category.name)

    def test_catalog_index_handles_zero_one_five_eight_and_ten_categories(self):
        for category_count in (0, 1, 5, 8, 10):
            with self.subTest(category_count=category_count):
                Product.objects.all().delete()
                Category.objects.all().delete()

                for number in range(category_count):
                    category = Category.objects.create(
                        name=f'Category {number + 1}',
                        slug=f'category-{number + 1}',
                        display_order=number,
                    )
                    if number == 0:
                        self.create_product_for_category(category, number + 1)

                response = self.client.get(reverse('main:catalog_all'), HTTP_HX_REQUEST='true')
                content = response.content.decode()

                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.count_catalog_category_cards(content), category_count)
                self.assertNotIn('<html', content)
                self.assertNotIn('<footer', content)

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

    def test_htmx_get_login_returns_partial_without_shared_layout(self):
        response = self.client.get(reverse('users:login'), HTTP_HX_REQUEST='true')
        content = response.content.decode()

        self.assert_htmx_partial(response)
        self.assertNotIn('<header', content)
        self.assertNotIn('id="main-content"', content)
        self.assertContains(response, 'id="loginForm"')
        self.assertContains(response, 'ВХОД')
        self.assertContains(response, 'Введите email')
        self.assertContains(response, 'Введите пароль')
        self.assertNotContains(response, '← НА ГЛАВНУЮ')

    def test_htmx_get_register_returns_partial_without_shared_layout(self):
        response = self.client.get(reverse('users:register'), HTTP_HX_REQUEST='true')
        content = response.content.decode()

        self.assert_htmx_partial(response)
        self.assertNotIn('<header', content)
        self.assertNotIn('id="main-content"', content)
        self.assertContains(response, 'id="createAccountForm"')
        self.assertContains(response, 'РЕГИСТРАЦИЯ')
        self.assertContains(response, 'Введите имя')
        self.assertContains(response, 'Повторите пароль')
        self.assertContains(response, 'personal_data_consent')
        self.assertContains(response, 'user_agreement_consent')
        self.assertNotContains(response, '← НА ГЛАВНУЮ')

    def test_htmx_get_legal_document_returns_partial_without_shared_layout(self):
        response = self.client.get(
            reverse('main:personal_data_consent'),
            HTTP_HX_REQUEST='true',
        )
        content = response.content.decode()

        self.assert_htmx_partial(response)
        self.assertNotIn('<header', content)
        self.assertNotIn('id="main-content"', content)
        self.assertContains(response, 'СОГЛАСИЕ НА ОБРАБОТКУ ПЕРСОНАЛЬНЫХ ДАННЫХ')
        self.assertContains(response, 'Документ находится в подготовке')

    def test_login_full_and_htmx_show_same_form_content(self):
        full_response = self.client.get(reverse('users:login'))
        htmx_response = self.client.get(reverse('users:login'), HTTP_HX_REQUEST='true')

        for expected in (
            'id="loginForm"',
            'ВХОД',
            'Добро пожаловать.',
            'Войдите в свой аккаунт',
            'Введите email',
            'Введите пароль',
            'ВОЙТИ В АККАУНТ',
        ):
            self.assertContains(full_response, expected)
            self.assertContains(htmx_response, expected)

    def test_register_full_and_htmx_show_same_form_content(self):
        full_response = self.client.get(reverse('users:register'))
        htmx_response = self.client.get(reverse('users:register'), HTTP_HX_REQUEST='true')

        for expected in (
            'id="createAccountForm"',
            'РЕГИСТРАЦИЯ',
            'Создайте аккаунт, чтобы получить',
            'Введите имя',
            'Введите фамилию',
            'Создайте пароль',
            'Повторите пароль',
            'СОЗДАТЬ АККАУНТ',
        ):
            self.assertContains(full_response, expected)
            self.assertContains(htmx_response, expected)

    def test_registration_form_requires_legal_consents(self):
        form = CustomUserCreationForm(data={
            'first_name': 'Artem',
            'last_name': 'Noctis',
            'email': 'artem@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('personal_data_consent', form.errors)
        self.assertIn('user_agreement_consent', form.errors)

    def test_registration_form_accepts_required_legal_consents(self):
        form = CustomUserCreationForm(data={
            'first_name': 'Artem',
            'last_name': 'Noctis',
            'email': 'artem@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'personal_data_consent': 'on',
            'user_agreement_consent': 'on',
        })

        self.assertTrue(form.is_valid(), form.errors)

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
