from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart, Category, MenuItem, Order, OrderItem
from .permissions import IsManager, ManagerWriteMixin
from .roles import (DELIVERY_CREW, MANAGER, find_group, get_or_create_group,
                    is_delivery_crew, is_manager)
from .serializers import (CartSerializer, CategorySerializer,
                          MenuItemSerializer, OrderSerializer, UserSerializer)


def _to_decimal(value, name):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        raise ValidationError({name: 'Enter a valid number.'})


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
class CategoriesView(ManagerWriteMixin, generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = None
    search_fields = ['title', 'slug']
    ordering_fields = ['id', 'title']


class SingleCategoryView(ManagerWriteMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


# ---------------------------------------------------------------------------
# Menu items
# ---------------------------------------------------------------------------
class MenuItemsView(ManagerWriteMixin, generics.ListCreateAPIView):
    """
    GET  ?category=<id|slug|title> &featured=true &from_price= &to_price=
         &search=<text> &ordering=price|-price|title &page= &perpage=
    """
    serializer_class = MenuItemSerializer
    search_fields = ['title', 'category__title']
    ordering_fields = ['price', 'title', 'id']

    def get_queryset(self):
        qs = MenuItem.objects.select_related('category').order_by('id')
        params = self.request.query_params

        category = params.get('category')
        if category:
            if category.isdigit():
                qs = qs.filter(category_id=int(category))
            else:
                qs = qs.filter(Q(category__title__iexact=category) |
                               Q(category__slug__iexact=category))

        featured = params.get('featured')
        if featured is not None:
            qs = qs.filter(featured=featured.lower() in ('1', 'true', 'yes'))

        if params.get('from_price'):
            qs = qs.filter(price__gte=_to_decimal(params['from_price'], 'from_price'))
        if params.get('to_price'):
            qs = qs.filter(price__lte=_to_decimal(params['to_price'], 'to_price'))
        return qs


class SingleMenuItemView(ManagerWriteMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.select_related('category')
    serializer_class = MenuItemSerializer

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response({'message': 'Menu item deleted.'}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Group management (manager only)
# ---------------------------------------------------------------------------
class GroupUsersView(APIView):
    permission_classes = [IsAuthenticated, IsManager]
    role = None

    def get(self, request):
        group = find_group(self.role)
        users = group.user_set.order_by('id') if group else User.objects.none()
        return Response(UserSerializer(users, many=True).data)

    def post(self, request):
        username = request.data.get('username')
        user_id = request.data.get('user_id')
        if username:
            user = get_object_or_404(User, username=username)
        elif user_id:
            user = get_object_or_404(User, pk=user_id)
        else:
            raise ValidationError({'username': 'This field is required.'})
        group = get_or_create_group(self.role)
        group.user_set.add(user)
        return Response({'message': f'{user.username} added to {group.name}.'},
                        status=status.HTTP_201_CREATED)


class GroupSingleUserView(APIView):
    permission_classes = [IsAuthenticated, IsManager]
    role = None

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        group = find_group(self.role)
        if group is None or not group.user_set.filter(pk=user.pk).exists():
            return Response({'detail': 'User is not in this group.'},
                            status=status.HTTP_404_NOT_FOUND)
        group.user_set.remove(user)
        return Response({'message': f'{user.username} removed from {group.name}.'},
                        status=status.HTTP_200_OK)


class ManagerUsersView(GroupUsersView):
    role = MANAGER


class ManagerSingleUserView(GroupSingleUserView):
    role = MANAGER


class DeliveryCrewUsersView(GroupUsersView):
    role = DELIVERY_CREW


class DeliveryCrewSingleUserView(GroupSingleUserView):
    role = DELIVERY_CREW


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------
class CartView(generics.ListCreateAPIView):
    serializer_class = CartSerializer
    pagination_class = None

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).select_related('menuitem')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.validated_data['menuitem']
        quantity = serializer.validated_data['quantity']

        cart_item, created = Cart.objects.get_or_create(
            user=request.user, menuitem=item,
            defaults={'quantity': quantity, 'unit_price': item.price,
                      'price': item.price * quantity},
        )
        if not created:  # same item added again -> increase quantity
            cart_item.quantity += quantity
            cart_item.unit_price = item.price
            cart_item.price = item.price * cart_item.quantity
            cart_item.save()
        return Response(CartSerializer(cart_item).data, status=status.HTTP_201_CREATED)

    def delete(self, request, *args, **kwargs):
        Cart.objects.filter(user=request.user).delete()
        return Response({'message': 'Cart cleared.'}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
def _orders_base():
    return (Order.objects.select_related('user', 'delivery_crew')
            .prefetch_related('order_items__menuitem').order_by('id'))


class OrdersView(generics.ListCreateAPIView):
    """
    Customer: own orders | Delivery crew: assigned orders | Manager: all orders.
    Filters: ?status=0|1 &date=YYYY-MM-DD &user=<username> &delivery_crew=<id>
    Also: ?search= ?ordering=date|total|status|-date ... ?page= &perpage=
    """
    serializer_class = OrderSerializer
    search_fields = ['user__username', 'delivery_crew__username']
    ordering_fields = ['id', 'date', 'total', 'status']

    def get_queryset(self):
        user = self.request.user
        qs = _orders_base()
        if is_manager(user):
            pass
        elif is_delivery_crew(user):
            qs = qs.filter(delivery_crew=user)
        else:
            qs = qs.filter(user=user)

        params = self.request.query_params
        if params.get('status') is not None:
            if params['status'] not in ('0', '1'):
                raise ValidationError({'status': 'Use 0 or 1.'})
            qs = qs.filter(status=params['status'] == '1')
        if params.get('date'):
            qs = qs.filter(date=params['date'])
        if is_manager(user):
            if params.get('user'):
                qs = qs.filter(user__username=params['user'])
            if params.get('delivery_crew'):
                qs = qs.filter(delivery_crew_id=params['delivery_crew'])
        return qs

    def create(self, request, *args, **kwargs):
        cart_items = list(Cart.objects.filter(user=request.user).select_related('menuitem'))
        if not cart_items:
            return Response({'message': 'Your cart is empty.'},
                            status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            order = Order.objects.create(user=request.user, total=0)
            total = Decimal('0')
            for c in cart_items:
                line_price = c.menuitem.price * c.quantity
                OrderItem.objects.create(
                    order=order, menuitem=c.menuitem, quantity=c.quantity,
                    unit_price=c.menuitem.price, price=line_price,
                )
                total += line_price
            order.total = total
            order.save()
            Cart.objects.filter(user=request.user).delete()
        return Response(OrderSerializer(_orders_base().get(pk=order.pk)).data,
                        status=status.HTTP_201_CREATED)


class SingleOrderView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    queryset = _orders_base()

    def get_object(self):
        order = get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])
        user = self.request.user
        if (is_manager(user) or order.user_id == user.id or
                (is_delivery_crew(user) and order.delivery_crew_id == user.id)):
            return order
        raise PermissionDenied('This order does not belong to you.')

    def update(self, request, *args, **kwargs):
        user = request.user
        self.get_object()  # 404 / 403 checks first
        if is_manager(user):
            pass
        elif is_delivery_crew(user):
            if request.method != 'PATCH':
                raise PermissionDenied('Delivery crew can only PATCH the order status.')
            disallowed = set(request.data) - {'status'}
            if disallowed:
                raise PermissionDenied('Delivery crew can only update the status field.')
        else:
            raise PermissionDenied('Only managers or delivery crew can update orders.')
        kwargs['partial'] = True  # PUT behaves like PATCH here
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        order = self.get_object()
        if not is_manager(request.user):
            raise PermissionDenied('Only managers can delete orders.')
        order.delete()
        return Response({'message': 'Order deleted.'}, status=status.HTTP_200_OK)
