"""Tests for django-ecommerce store app."""

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from store.models import Category, Coupon, Order, OrderItem, Product


# ------------------------------------------------------------------
# Models: Category
# ------------------------------------------------------------------
@pytest.mark.django_db
def test_category_str():
    cat = Category.objects.create(name="Eletrônics", slug="electronics")
    assert str(cat) == "Eletrônics"


# ------------------------------------------------------------------
# Models: Product
# ------------------------------------------------------------------
@pytest.mark.django_db
def test_product_str_and_url():
    cat = Category.objects.create(name="Books", slug="books")
    product = Product.objects.create(
        name="Django Book",
        slug="django-book",
        description="Learn Django",
        price=29.99,
        stock=5,
        category=cat,
    )
    assert str(product) == "Django Book"
    assert product.get_absolute_url() == "/product/django-book/"


# ------------------------------------------------------------------
# Models: Coupon
# ------------------------------------------------------------------
@pytest.mark.django_db
def test_coupon_validity():

    coupon = Coupon.objects.create(
        code="SAVE10",
        discount_percent=10,
        min_order=50.00,
        active=True,
        valid_from=timezone.now(),
        valid_to=None,
    )
    assert coupon.is_valid() is True

    coupon.active = False
    coupon.save()
    assert coupon.is_valid() is False


# ------------------------------------------------------------------
# Models: Order and OrderItem
# ------------------------------------------------------------------
@pytest.mark.django_db
def test_order_and_items():
    user = User.objects.create_user(username="buyer", password="pass123")
    product = Product.objects.create(
        name="Widget", slug="widget", price=10.00, stock=10
    )
    order = Order.objects.create(user=user, total=0)
    item = OrderItem.objects.create(
        order=order, product=product, quantity=2, price=10.00
    )
    assert item.subtotal() == 20.00
    assert str(order) == f"Order #{order.pk}"


# ------------------------------------------------------------------
# Views: product_list
# ------------------------------------------------------------------
@pytest.mark.django_db
def test_product_list_view(client):
    Product.objects.create(name="A", slug="a", price=1.00, stock=1, is_active=True)
    Product.objects.create(name="B", slug="b", price=2.00, stock=0, is_active=False)
    url = reverse("store:product_list")
    response = client.get(url)
    assert response.status_code == 200
    assert b"A" in response.content
    assert b"B" not in response.content  # inactive not shown


# ------------------------------------------------------------------
# Views: product_detail
# ------------------------------------------------------------------
@pytest.mark.django_db
def test_product_detail_view(client):
    product = Product.objects.create(name="Thing", slug="thing", price=5.00, stock=3)
    url = reverse("store:product_detail", args=[product.slug])
    response = client.get(url)
    assert response.status_code == 200
    assert b"Thing" in response.content


# ------------------------------------------------------------------
# Views: cart add / view
# ------------------------------------------------------------------
@pytest.mark.django_db
def test_cart_add_and_view(client):
    product = Product.objects.create(name="Gadget", slug="gadget", price=7.00, stock=4)
    client.post(reverse("store:cart_add", args=[product.id]))
    response = client.get(reverse("store:cart_view"))
    assert response.status_code == 200
    assert b"Gadget" in response.content


# ------------------------------------------------------------------
# Views: checkout requires login
# ------------------------------------------------------------------
@pytest.mark.django_db
def test_checkout_redirects_when_anonymous(client):
    url = reverse("store:checkout")
    response = client.get(url)
    assert response.status_code == 302  # redirect to login


# ------------------------------------------------------------------
# Views: dashboard requires login
# ------------------------------------------------------------------
@pytest.mark.django_db
def test_dashboard_redirects_when_anonymous(client):
    url = reverse("store:dashboard")
    response = client.get(url)
    assert response.status_code == 302


# ------------------------------------------------------------------
# Models: Coupon validity with date
# ------------------------------------------------------------------
@pytest.mark.django_db
def test_coupon_valid_to_expired():

    past = timezone.now() - timezone.timedelta(days=1)
    coupon = Coupon.objects.create(
        code="EXPIRED",
        discount_percent=10,
        min_order=0.00,
        active=True,
        valid_from=timezone.now(),
        valid_to=past,
    )
    assert coupon.is_valid() is False


# ------------------------------------------------------------------
# Models: OrderItem subtotal
# ------------------------------------------------------------------
@pytest.mark.django_db
def test_order_item_subtotal():
    product = Product.objects.create(
        name="Widget", slug="widget", price=10.00, stock=10
    )
    order = Order.objects.create(total=0)
    item = OrderItem.objects.create(
        order=order, product=product, quantity=3, price=10.00
    )
    assert item.subtotal() == 30.00


# ------------------------------------------------------------------
# Views: cart remove
# ------------------------------------------------------------------
@pytest.mark.django_db
def test_cart_remove(client):
    product = Product.objects.create(
        name="Removable", slug="removable", price=7.00, stock=4
    )
    client.post(reverse("store:cart_add", args=[product.id]))
    response = client.get(reverse("store:cart_view"))
    assert b"Removable" in response.content

    client.post(reverse("store:cart_remove", args=[product.id]))
    response = client.get(reverse("store:cart_view"))
    assert b"Removable" not in response.content


# ------------------------------------------------------------------
# Views: checkout (logged in)
# ------------------------------------------------------------------
@pytest.mark.django_db
def test_checkout_creates_order(client):
    user = User.objects.create_user(username="buyer2", password="pass123")
    client.login(username="buyer2", password="pass123")

    product = Product.objects.create(
        name="CheckoutItem", slug="checkout-item", price=10.00, stock=10
    )
    # Add to cart via session
    session = client.session
    session["cart"] = {str(product.id): 2}
    session.save()

    url = reverse("store:checkout")
    response = client.post(url, {"coupon_code": ""})
    assert response.status_code == 302  # redirect to order_list

    orders = Order.objects.filter(user=user)
    assert orders.count() == 1
    assert orders.first().total == 20.00


# ------------------------------------------------------------------
# Views: dashboard (logged in)
# ------------------------------------------------------------------
@pytest.mark.django_db
def test_dashboard_view(client):
    User.objects.create_user(username="viewer", password="pass123")
    client.login(username="viewer", password="pass123")

    url = reverse("store:dashboard")
    response = client.get(url)
    assert response.status_code == 200
    assert b"Sales Dashboard" in response.content


# ------------------------------------------------------------------
# CLI / management
# ------------------------------------------------------------------
def test_manage_py_exists():
    import os

    assert os.path.exists("manage.py")
