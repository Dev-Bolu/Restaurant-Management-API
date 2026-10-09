from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from RestaurantManagementAPI.models import Cart, Category, MenuItem, Order, OrderItem
from RestaurantManagementAPI.roles import MANAGER, DELIVERY_CREW, get_or_create_group

PASSWORD = 'Lemon@2026pass'

USERS = {
    'manager1': MANAGER, 'manager2': MANAGER,
    'delivery1': DELIVERY_CREW, 'delivery2': DELIVERY_CREW,
    'customer1': None, 'customer2': None, 'customer3': None,
}

CATALOG = {
    ('starters', 'Starters'): [('Greek Salad', '8.50', True), ('Bruschetta', '6.75', False),
                               ('Hummus & Pita', '7.25', False)],
    ('mains', 'Mains'): [('Lemon Chicken', '16.00', False), ('Grilled Sea Bass', '21.50', False),
                         ('Moussaka', '15.25', False), ('Lamb Souvlaki', '18.75', False)],
    ('desserts', 'Desserts'): [('Lemon Cake', '6.50', False), ('Baklava', '5.95', False),
                               ('Gelato', '4.99', False)],
    ('drinks', 'Drinks'): [('Fresh Lemonade', '3.50', False), ('Sparkling Water', '2.25', False)],
}


class Command(BaseCommand):
    help = 'Create demo groups, users, categories, menu items and one sample order.'

    def handle(self, *args, **options):
        manager_group = get_or_create_group(MANAGER)
        crew_group = get_or_create_group(DELIVERY_CREW)

        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@restaurant.test', PASSWORD)

        for username, role in USERS.items():
            user, _ = User.objects.get_or_create(
                username=username, defaults={'email': f'{username}@restaurant.test'})
            user.set_password(PASSWORD)
            user.save()
            if role == MANAGER:
                manager_group.user_set.add(user)
            elif role == DELIVERY_CREW:
                crew_group.user_set.add(user)

        for (slug, title), items in CATALOG.items():
            category, _ = Category.objects.get_or_create(slug=slug, defaults={'title': title})
            for name, price, featured in items:
                MenuItem.objects.get_or_create(
                    title=name,
                    defaults={'price': Decimal(price), 'featured': featured, 'category': category})

        # One sample order: customer1 -> assigned to delivery1 (out for delivery)
        if not Order.objects.exists():
            customer = User.objects.get(username='customer1')
            crew = User.objects.get(username='delivery1')
            order = Order.objects.create(user=customer, delivery_crew=crew, status=False)
            total = Decimal('0')
            for title, qty in (('Lemon Chicken', 2), ('Fresh Lemonade', 2)):
                item = MenuItem.objects.get(title=title)
                OrderItem.objects.create(order=order, menuitem=item, quantity=qty,
                                         unit_price=item.price, price=item.price * qty)
                total += item.price * qty
            order.total = total
            order.save()

        # One item waiting in customer2's cart so "view cart" shows data
        if not Cart.objects.exists():
            customer2 = User.objects.get(username='customer2')
            item = MenuItem.objects.get(title='Greek Salad')
            Cart.objects.create(user=customer2, menuitem=item, quantity=1,
                                unit_price=item.price, price=item.price)

        self.stdout.write(self.style.SUCCESS('Demo data ready.'))
