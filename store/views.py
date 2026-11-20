"""Store views."""

from decimal import Decimal

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


def _cart_context(request):
    """Build cart context for rendering."""
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
    return {"items": items, "total": total}


def cart_count(request):
    """Context processor for cart item count."""
    return {"cart_count": sum(_cart(request).values())}


def cart_view(request):
    """Show the shopping cart."""
    ctx = _cart_context(request)
    return render(request, "store/cart.html", ctx)


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
def apply_coupon(request):
    """Apply a coupon code to the current session."""
    if request.method == "POST":
        code = request.POST.get("coupon_code", "").strip()
        if code:
            try:
                coupon = Coupon.objects.get(code=code, active=True)
                if coupon.is_valid():
                    request.session["coupon_code"] = code
                    messages.success(request, f"Coupon {code} applied!")
                else:
                    messages.error(request, "This coupon is not currently valid.")
            except Coupon.DoesNotExist:
                messages.error(request, "Invalid coupon code.")
        else:
            messages.error(request, "Please enter a coupon code.")
    return redirect("store:checkout")


@login_required
def checkout(request):
    """Create an order from the cart."""
    if request.method == "POST":
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
                    discount = total * (Decimal(coupon.discount_percent) / Decimal(100))
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
        request.session.pop("coupon_code", None)
        request.session.modified = True
        messages.success(request, f"Order #{order.pk} placed successfully.")
        return redirect("store:order_list")

    # GET: render checkout page with cart context
    ctx = _cart_context(request)
    coupon_code = request.session.get("coupon_code")
    if coupon_code:
        try:
            ctx["coupon"] = Coupon.objects.get(code=coupon_code, active=True)
        except Coupon.DoesNotExist:
            pass
    return render(request, "store/checkout.html", ctx)


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