import graphene
from graphene_django import DjangoObjectType
from .models import Customer, Product, Order
from django.db import transaction, IntegrityError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from graphene_django.filter import DjangoFilterConnectionField
from datetime import datetime
from django.utils import timezone
from graphene_django.filter import DjangoFilterConnectionField
from graphene import relay
from .filters import CustomerFilter, ProductFilter, OrderFilter
from .types import CustomerType, ProductType, OrderType 
import re
from crm.models import Product

# ----------------------------
# DjangoObjectType Definitions
# ----------------------------
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "total_amount", "order_date")


# ----------------------------
# CreateCustomer Mutation# ----------------------------
class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String(required=False)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    def mutate(self, info, name, email, phone=None):
        # Email validation
        try:
            validate_email(email)
        except ValidationError:
            raise Exception("Invalid email format")

        # Check unique email
        if Customer.objects.filter(email=email).exists():
            raise Exception("Email already exists")

        # Optional phone validation
        if phone and not (phone.startswith("+") or phone.replace("-", "").isdigit()):
            raise Exception("Invalid phone format")

        customer = Customer.objects.create(name=name, email=email, phone=phone)
        return CreateCustomer(customer=customer, message="Customer created successfully")


# ----------------------------
# BulkCreateCustomers Mutation
# ----------------------------
class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(
            graphene.NonNull(
                graphene.InputObjectType(
                    "CustomerInput",
                    name=graphene.String(required=True),
                    email=graphene.String(required=True),
                    phone=graphene.String(),
                )
            )
        )

# ============================
# GRAPHQL TYPES
# ============================
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = "__all__"


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = "__all__"


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = "__all__"

# ============INPUT TYPES================
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)


class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Float(required=True)
    stock = graphene.Int(required=False, default_value=0)


class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime(required=False)


# ============================
# MUTATIONS
# ============================
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    @staticmethod
    def mutate(root, info, input):
        # Validate email uniqueness
        if Customer.objects.filter(email=input.email).exists():
            raise ValidationError("Email already exists")

        # Validate phone format if provided
        if input.phone:
            pattern = r"^\+?\d{7,15}$|^\d{3}-\d{3}-\d{4}$"
            if not re.match(pattern, input.phone):
                raise ValidationError("Invalid phone number format")

        # Create customer
        customer = Customer.objects.create(
            name=input.name,
            email=input.email,
            phone=input.phone or ""
        )
        customer.save()
        return CreateCustomer(customer=customer, message="Customer created successfully.")


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, input):
        created_customers = []
        errors = []

        with transaction.atomic():
            for entry in input:
                try:
                    if Customer.objects.filter(email=entry.email).exists():
                        raise ValidationError(f"Email already exists: {entry.email}")

                    if entry.phone:
                        pattern = r"^\+?\d{7,15}$|^\d{3}-\d{3}-\d{4}$"
                        if not re.match(pattern, entry.phone):
                            raise ValidationError(f"Invalid phone format: {entry.phone}")

                    customer = Customer.objects.create(
                        name=entry.name,
                        email=entry.email,
                        phone=entry.phone or ""
                    )
                    created_customers.append(customer)

                except ValidationError as e:
                    errors.append(str(e))

        return BulkCreateCustomers(customers=created_customers, errors=errors)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)
    message = graphene.String()

    @staticmethod
    def mutate(root, info, input):
        if input.price <= 0:
            raise ValidationError("Price must be positive.")
        if input.stock < 0:
            raise ValidationError("Stock cannot be negative.")

        product = Product.objects.create(
            name=input.name,
            price=input.price,
            stock=input.stock
        )
        product.save() 
        return CreateProduct(product=product, message="Product created successfully.")


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)
    message = graphene.String()

    @staticmethod
    def mutate(root, info, input):
        try:
            customer = Customer.objects.get(pk=input.customer_id)
        except Customer.DoesNotExist:
            raise ValidationError("Customer not found.")

        products = Product.objects.filter(pk__in=input.product_ids)
        if not products.exists():
            raise ValidationError("No valid products found.")
        if len(products) != len(input.product_ids):
            raise ValidationError("One or more product IDs are invalid.")

        total_amount = sum([p.price for p in products])

        order = Order.objects.create(
            customer=customer,
            total_amount=total_amount,
            order_date=input.order_date or timezone.now()
        )
        order.products.set(products)
        order.save()  # ✅ Save before adding M2M
        return CreateOrder(order=order, message="Order created successfully.")

# ============================
# NEW MUTATION: UpdateLowStockProducts
# ============================
class UpdateLowStockProducts(graphene.Mutation):
    success = graphene.Boolean()
    message = graphene.String()
    updated_products = graphene.List(ProductType)

    @staticmethod
    def mutate(root, info):
        low_stock_products = Product.objects.filter(stock__lt=10)
        updated = []

        for product in low_stock_products:
            product.stock += 10
            product.save()
            updated.append(product)

        if updated:
            msg = f"Updated {len(updated)} low-stock products (+10 each)."
        else:
            msg = "No low-stock products found."

        return UpdateLowStockProducts(success=True, message=msg, updated_products=updated)



# ============================
# ROOT MUTATION
# ============================
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, input):
        customers = []
        errors = []
        with transaction.atomic():
            for data in input:
                try:
                    validate_email(data.email)
                    if Customer.objects.filter(email=data.email).exists():
                        raise Exception(f"Email '{data.email}' already exists")

                    cust = Customer.objects.create(
                        name=data.name,
                        email=data.email,
                        phone=data.phone or ""
                    )
                    customers.append(cust)

                except Exception as e:
                    errors.append(str(e))
        return BulkCreateCustomers(customers=customers, errors=errors)


# ----------------------------
# CreateProduct Mutation
# ----------------------------
class CreateProduct(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        stock = graphene.Int(required=False, default_value=0)

    product = graphene.Field(ProductType)

    def mutate(self, info, name, price, stock=0):
        if price <= 0:
            raise Exception("Price must be positive")
        if stock < 0:
            raise Exception("Stock cannot be negative")

        product = Product.objects.create(name=name, price=price, stock=stock)
        return CreateProduct(product=product)


# ----------------------------
# CreateOrder Mutation
# ----------------------------
class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.NonNull(graphene.ID), required=True)
        order_date = graphene.DateTime(required=False)

    order = graphene.Field(OrderType)

    def mutate(self, info, customer_id, product_ids, order_date=None):
        # Validate customer
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            raise Exception("Invalid customer ID")

        # Validate products
        products = Product.objects.filter(id__in=product_ids)
        if not products.exists():
            raise Exception("Invalid product IDs")
        if len(products) != len(product_ids):
            raise Exception("One or more product IDs are invalid")

        total = sum([p.price for p in products])
        order = Order.objects.create(
            customer=customer,
            total_amount=total,
            order_date=order_date or datetime.now()
        )
        order.products.set(products)
        return CreateOrder(order=order)


# ----------------------------
# Schema Mutation
# ----------------------------
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

class Query(graphene.ObjectType):
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)

    def resolve_customers(root, info):
        return Customer.objects.all()

    def resolve_products(root, info):
        return Product.objects.all()

    def resolve_orders(root, info):
        return Order.objects.all()
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        filter_fields = ['name', 'email']  # 👈 add filterable fields
        interfaces = (relay.Node,)

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        filter_fields = ['name', 'price', 'stock']
        interfaces = (relay.Node,)

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        filter_fields = ['customer__name', 'product__name', 'quantity']
        interfaces = (relay.Node,)
class Query(graphene.ObjectType):
    customer = relay.Node.Field(CustomerType)
    all_customers = DjangoFilterConnectionField(CustomerType)

    product = relay.Node.Field(ProductType)
    all_products = DjangoFilterConnectionField(ProductType)

    order = relay.Node.Field(OrderType)
    all_orders = DjangoFilterConnectionField(OrderType)
