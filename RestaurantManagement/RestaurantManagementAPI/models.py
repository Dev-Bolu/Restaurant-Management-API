from django.contrib.auth.models import User
from django.db import models


class Category(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255, db_index=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['id']

    def __str__(self):
        return self.title


class MenuItem(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, db_index=True)
    featured = models.BooleanField(default=False, db_index=True)  # "item of the day"
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='menu_items'
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.title


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    menuitem = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        unique_together = ('menuitem', 'user')
        ordering = ['id']

    def __str__(self):
        return f'{self.user} - {self.menuitem} x{self.quantity}'


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    delivery_crew = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='delivery_orders',
    )
    # 0 = out for delivery (once a crew member is assigned), 1 = delivered
    status = models.BooleanField(default=False, db_index=True)
    total = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    date = models.DateField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'Order #{self.pk} ({self.user})'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    menuitem = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        unique_together = ('order', 'menuitem')
        ordering = ['id']

    def __str__(self):
        return f'{self.menuitem} x{self.quantity}'
