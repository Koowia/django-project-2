from django.urls import path
from . import views


app_name = 'main'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('catalog/', views.CatalogView.as_view(), name='catalog_all'),
    path('catalog/<slug:category_slug>/', views.CatalogView.as_view(), name='catalog'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('search/', views.CatalogView.as_view(), name='search'),
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
    path(
        'legal/privacy-policy/',
        views.LegalDocumentView.as_view(),
        {'document_key': 'privacy_policy'},
        name='privacy_policy',
    ),
    path(
        'legal/personal-data-consent/',
        views.LegalDocumentView.as_view(),
        {'document_key': 'personal_data_consent'},
        name='personal_data_consent',
    ),
    path(
        'legal/user-agreement/',
        views.LegalDocumentView.as_view(),
        {'document_key': 'user_agreement'},
        name='user_agreement',
    ),
    path(
        'legal/public-offer/',
        views.LegalDocumentView.as_view(),
        {'document_key': 'public_offer'},
        name='public_offer',
    ),
    path(
        'legal/payment-delivery/',
        views.LegalDocumentView.as_view(),
        {'document_key': 'payment_delivery'},
        name='payment_delivery',
    ),
    path(
        'legal/returns-exchange/',
        views.LegalDocumentView.as_view(),
        {'document_key': 'returns_exchange'},
        name='returns_exchange',
    ),
]
