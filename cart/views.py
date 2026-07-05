from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View 
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.db import transaction
from main.models import Product, ProductSize
from .models import Cart, CartItem
from .forms import AddToCartForm, UpdateCartItemForm


class CartMixin:
    @staticmethod
    def get_cart(request):
        if hasattr(request, 'cart'):
            return request.cart

        if not request.session.session_key:
            request.session.create()

        cart, _ = Cart.objects.get_or_create(
            session_key=request.session.session_key
        )
        request.session.modified = True
        return cart

    @staticmethod
    def cart_context(cart):
        total_items = cart.total_items
        last_two = total_items % 100
        last_digit = total_items % 10
        if last_two in range(11, 15):
            item_word = 'ТОВАРОВ'
        elif last_digit == 1:
            item_word = 'ТОВАР'
        elif last_digit in (2, 3, 4):
            item_word = 'ТОВАРА'
        else:
            item_word = 'ТОВАРОВ'

        return {
            'cart': cart,
            'cart_items': cart.items.select_related(
                'product',
                'product_size__size',
                'product__category',
            ).order_by('-added_at'),
            'cart_items_count': total_items,
            'cart_items_count_label': f'{total_items} {item_word}',
        }


class CartModalView(CartMixin, View):
    def get(self, request):
        cart = self.get_cart(request)
        return TemplateResponse(request, 'cart/cart_modal.html', self.cart_context(cart))


class AddToCartView(CartMixin, View):
    @transaction.atomic
    def post(self, request, slug):
        cart = self.get_cart(request)
        product = get_object_or_404(Product, slug=slug)
        form = AddToCartForm(request.POST, product=product)

        if not form.is_valid():
            return JsonResponse({
                'error': 'Invalid form data.',
                'errors': form.errors,
            }, status=400)

        size_id = form.cleaned_data.get('size_id')
        if size_id:
            product_size = get_object_or_404(
                ProductSize,
                id=size_id,
                product=product,
            )
        else:
            product_size = product.product_sizes.filter(stock__gt=0).first()
            if not product_size:
                return JsonResponse({'error': 'No sizes available.'}, status=400)

        quantity = form.cleaned_data['quantity']

        existing_item = cart.items.filter(
            product=product,
            product_size=product_size,
        ).first()

        total_quantity = (existing_item.quantity if existing_item else 0) + quantity
        if total_quantity > product_size.stock:
            available = product_size.stock - (existing_item.quantity if existing_item else 0)
            return JsonResponse({
                'error': f"Only {available} more items available."
            }, status=400)

        cart_item = cart.add_product(product, product_size, quantity)

        if request.headers.get('HX-Request'):
            return redirect('cart:cart_modal')

        return JsonResponse({
            'success': True,
            'total_items': cart.total_items,
            'message': f"{product.name} added to cart.",
            'cart_item_id': cart_item.id,
        })


class UpdateCartItemView(CartMixin, View):
    @transaction.atomic
    def post(self, request, item_id):
        cart = self.get_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        form = UpdateCartItemForm(request.POST, instance=cart_item)
        if not form.is_valid():
            return JsonResponse({'error': 'Invalid quantity.', 'errors': form.errors}, status=400)

        quantity = form.cleaned_data['quantity']

        if quantity > cart_item.product_size.stock:
            return JsonResponse({
                'error': f"Only {cart_item.product_size.stock} items available."
            }, status=400)

        if quantity == 0:
            cart_item.delete()
        else:
            form.save()

        request.session.modified = True

        return TemplateResponse(request, 'cart/cart_modal.html', self.cart_context(cart))


class RemoveCartItemView(CartMixin, View):
    def post(self, request, item_id):
        cart = self.get_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()

        request.session.modified = True

        return TemplateResponse(request, 'cart/cart_modal.html', self.cart_context(cart))


class CartCountView(CartMixin, View):
    def get(self, request):
        cart = self.get_cart(request)
        return JsonResponse({
            'total_items': cart.total_items,
            'subtotal': float(cart.subtotal)
        })


class ClearCartView(CartMixin, View):
    def post(self, request):
        cart = self.get_cart(request)
        cart.clear()

        request.session.modified = True

        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'cart/cart_modal.html', self.cart_context(cart))

        return JsonResponse({'success': True, 'message': 'Cart cleared.'})


class CartSummaryView(CartMixin, View):
    def get(self, request):
        cart = self.get_cart(request)
        return TemplateResponse(request, 'cart/cart_summary.html', self.cart_context(cart))
