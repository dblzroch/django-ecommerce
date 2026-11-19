"""Store views."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from .models import Category, Coupon, Order, OrderItem, Product


def product_list(request):
    """List active products."""
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.all()
    return render(
        request,
        "store/product_list.html",
        {"products": products, "categories": categories},
    )


def product_detail(request, slug):
    """Show a single product."""
    product = get_object_or_404(Product, slug=slug, is_active=True)
    return render(request, "store/product_detail.html", {"product": product})


def _cart(request):
    return request.session.setdefault("cart", {})


def cart_view(request):
    """Show the shopping cart."""
    cart = _cart(request)
    items = []
    total = 0
    for pid, qty in cart.items():
        product = Product.objects.filter(pk=pid).first()
        if product:
            subtotal = product.price * qty
            total += subtotal
            items.append(
                {
                    "product": product,
                    "quantity": qty,
                    "subtotal": subtotal,
                }
            )
    return render(
        request,
        "store/cart.html",
        {"items": items, "total": total},
    )


def cart_add(request, product_id):
    """Add a product to the cart."""
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    cart = _cart(request)
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    request.session.modified = True
    messages.success(request, f"{product.name} added to cart.")
    return redirect("store:cart_view")


def cart_remove(request, product_id):
    """Remove a product from the cart."""
    cart = _cart(request)
    cart.pop(str(product_id), None)
    request.session.modified = True
    messages.info(request, "Item removed from cart.")
    return redirect("store:cart_view")


@login_required
def checkout(request):
    """Create an order from the cart."""
    cart = _cart(request)
    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect("store:cart_view")

    total = 0
    for pid, qty in cart.items():
        product = Product.objects.filter(pk=pid).first()
        if product:
            total += product.price * qty

    coupon = None
    coupon_code = request.session.get("coupon_code")
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code, active=True)
            if coupon.is_valid() and total >= coupon.min_order:
                discount = total * (coupon.discount_percent / 100)
                total -= discount
            else:
                coupon = None
                request.session.pop("coupon_code", None)
        except Coupon.DoesNotExist:
            request.session.pop("coupon_code", None)

    order = Order.objects.create(user=request.user, coupon=coupon, total=total)
    for pid, qty in cart.items():
        product = Product.objects.get(pk=pid)
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=qty,
            price=product.price,
        )
        product.stock = max(0, product.stock - qty)
        product.save()

    cart.clear()
    request.session.modified = True
    messages.success(request, f"Order #{order.pk} placed successfully.")
    return redirect("store:order_list")


@login_required
def order_list(request):
    """List the user's orders."""
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "store/order_list.html", {"orders": orders})


@login_required
def dashboard(request):
    """Sales dashboard."""
    total_sales = (
        Order.objects.filter(status="paid").aggregate(total=Sum("total"))["total"] or 0
    )
    orders_count = Order.objects.count()
    products_count = Product.objects.count()
    recent_orders = Order.objects.order_by("-created_at")[:10]
    return render(
        request,
        "store/dashboard.html",
        {
            "total_sales": total_sales,
            "orders_count": orders_count,
            "products_count": products_count,
            "recent_orders": recent_orders,
        },
    )
