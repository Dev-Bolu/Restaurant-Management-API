from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Cart, Category, MenuItem, Order, OrderItem
from .roles import is_delivery_crew


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'slug', 'title']


class MenuItemSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source='category', queryset=Category.objects.all(), write_only=True
    )

    class Meta:
        model = MenuItem
        fields = ['id', 'title', 'price', 'featured', 'category', 'category_id']

    def to_internal_value(self, data):
        # Be lenient: accept {"category": 1} as well as {"category_id": 1}.
        if hasattr(data, 'copy'):
            data = data.copy()
        if ('category' in data and 'category_id' not in data
                and not isinstance(data['category'], dict)):
            data['category_id'] = data['category']
        return super().to_internal_value(data)

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('Price must be greater than zero.')
        return value

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError('Title cannot be blank.')
        return value


class CartSerializer(serializers.ModelSerializer):
    menuitem = serializers.PrimaryKeyRelatedField(queryset=MenuItem.objects.all())
    menuitem_title = serializers.CharField(source='menuitem.title', read_only=True)
    quantity = serializers.IntegerField(min_value=1, max_value=99)

    class Meta:
        model = Cart
        fields = ['id', 'menuitem', 'menuitem_title', 'quantity', 'unit_price', 'price']
        read_only_fields = ['unit_price', 'price']


class OrderItemSerializer(serializers.ModelSerializer):
    menuitem_title = serializers.CharField(source='menuitem.title', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'menuitem', 'menuitem_title', 'quantity', 'unit_price', 'price']


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username', read_only=True)
    status = serializers.IntegerField(min_value=0, max_value=1, required=False)
    delivery_crew = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    delivery_crew_username = serializers.SerializerMethodField()
    order_items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'delivery_crew', 'delivery_crew_username',
                  'status', 'total', 'date', 'order_items']
        read_only_fields = ['total', 'date']

    def get_delivery_crew_username(self, obj):
        return obj.delivery_crew.username if obj.delivery_crew else None

    def validate_delivery_crew(self, value):
        if value is not None and not is_delivery_crew(value):
            raise serializers.ValidationError(
                'This user is not in the delivery crew group.'
            )
        return value
