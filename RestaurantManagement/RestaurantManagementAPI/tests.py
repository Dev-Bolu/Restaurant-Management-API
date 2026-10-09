from django.contrib.auth.models import Group, User
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Category, MenuItem, Order


class RestaurantManagementTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager_group = Group.objects.create(name='Manager')
        cls.crew_group = Group.objects.create(name='Delivery crew')
        cls.admin = User.objects.create_superuser('admin', 'a@x.com', 'pass12345!')
        cls.manager = User.objects.create_user('mgr', password='pass12345!')
        cls.manager.groups.add(cls.manager_group)
        cls.crew = User.objects.create_user('crew', password='pass12345!')
        cls.crew.groups.add(cls.crew_group)
        cls.crew2 = User.objects.create_user('crew2', password='pass12345!')
        cls.crew2.groups.add(cls.crew_group)
        cls.cust = User.objects.create_user('cust', password='pass12345!')
        cls.cust2 = User.objects.create_user('cust2', password='pass12345!')
        cls.cat1 = Category.objects.create(slug='mains', title='Mains')
        cls.cat2 = Category.objects.create(slug='drinks', title='Drinks')
        for i in range(8):
            MenuItem.objects.create(title=f'Dish {i}', price=10 + i, category=cls.cat1)
        cls.cheap = MenuItem.objects.create(title='Water', price='1.50', category=cls.cat2)

    def as_user(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def anon(self):
        self.client.credentials()

    # --- admin / managers -------------------------------------------------
    def test_admin_assigns_manager_and_lists_group(self):  # 1, 2
        self.as_user(self.admin)
        r = self.client.post('/api/groups/manager/users', {'username': 'cust'})
        self.assertEqual(r.status_code, 201)
        self.assertTrue(self.cust.groups.filter(name='Manager').exists())
        r = self.client.get('/api/groups/manager/users')
        self.assertEqual(r.status_code, 200)
        self.assertEqual({u['username'] for u in r.json()}, {'mgr', 'cust'})

    def test_admin_adds_menu_items_and_categories(self):  # 3, 4
        self.as_user(self.admin)
        r = self.client.post('/api/categories', {'slug': 'sides', 'title': 'Sides'})
        self.assertEqual(r.status_code, 201)
        r = self.client.post('/api/menu-items', {
            'title': 'Fries', 'price': '4.00', 'featured': False,
            'category_id': r.json()['id']}, format='json')
        self.assertEqual(r.status_code, 201)

    def test_manager_login_and_item_of_the_day(self):  # 5, 6
        r = self.client.post('/token/login/', {'username': 'mgr', 'password': 'pass12345!'})
        self.assertEqual(r.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {r.json()['auth_token']}")
        r = self.client.patch(f'/api/menu-items/{self.cheap.id}', {'featured': True}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['featured'])
        self.assertEqual(self.client.delete(f'/api/menu-items/{self.cheap.id}').status_code, 200)

    def test_manager_assigns_delivery_crew_user_and_removal(self):  # 7
        self.as_user(self.manager)
        r = self.client.post('/api/groups/delivery-crew/users', {'username': 'cust2'})
        self.assertEqual(r.status_code, 201)
        r = self.client.get('/api/groups/delivery-crew/users')
        self.assertIn('cust2', [u['username'] for u in r.json()])
        self.assertEqual(self.client.delete(f'/api/groups/delivery-crew/users/{self.cust2.id}').status_code, 200)
        self.assertEqual(self.client.delete(f'/api/groups/delivery-crew/users/{self.cust2.id}').status_code, 404)
        self.assertEqual(self.client.delete('/api/groups/delivery-crew/users/9999').status_code, 404)
        self.assertEqual(self.client.post('/api/groups/manager/users', {'username': 'nobody'}).status_code, 404)

    def test_non_manager_cannot_manage_groups_or_menu(self):
        self.as_user(self.cust)
        self.assertEqual(self.client.post('/api/groups/manager/users', {'username': 'cust'}).status_code, 403)
        self.assertEqual(self.client.post('/api/menu-items', {}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/menu-items/{self.cheap.id}').status_code, 403)
        self.as_user(self.crew)
        self.assertEqual(self.client.patch(f'/api/menu-items/{self.cheap.id}', {'featured': True}).status_code, 403)
        self.anon()
        self.assertEqual(self.client.get('/api/menu-items').status_code, 401)

    # --- customers --------------------------------------------------------
    def test_customer_registration_and_login(self):  # 11, 12
        r = self.client.post('/api/users', {'username': 'newbie', 'email': 'n@x.com',
                                            'password': 'Str0ng!pass99'})
        self.assertEqual(r.status_code, 201)
        r = self.client.post('/token/login/', {'username': 'newbie', 'password': 'Str0ng!pass99'})
        self.assertEqual(r.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {r.json()['auth_token']}")
        self.assertEqual(self.client.get('/api/users/me/').json()['username'], 'newbie')
        self.assertEqual(self.client.get('/api/users/me').status_code, 200)

    def test_browse_categories_and_menu(self):  # 13-17
        self.as_user(self.cust)
        self.assertEqual(len(self.client.get('/api/categories').json()), 2)
        r = self.client.get('/api/menu-items')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['count'], 9)
        self.assertEqual(len(r.json()['results']), 6)                       # default page
        self.assertEqual(len(self.client.get('/api/menu-items?perpage=4&page=3').json()['results']), 1)
        by_cat = self.client.get('/api/menu-items?category=drinks').json()
        self.assertEqual(by_cat['count'], 1)
        self.assertEqual(self.client.get(f'/api/menu-items?category={self.cat1.id}').json()['count'], 8)
        asc = [i['price'] for i in self.client.get('/api/menu-items?ordering=price&perpage=20').json()['results']]
        self.assertEqual(asc, sorted(asc, key=float))
        desc = [i['price'] for i in self.client.get('/api/menu-items?ordering=-price&perpage=20').json()['results']]
        self.assertEqual(desc, sorted(desc, key=float, reverse=True))
        self.assertEqual(self.client.get('/api/menu-items?search=water').json()['count'], 1)
        self.assertEqual(self.client.get('/api/menu-items/999').status_code, 404)

    def test_cart_and_orders_full_flow(self):  # 18-21 + 8-10
        self.as_user(self.cust)
        r = self.client.post('/api/orders')
        self.assertEqual(r.status_code, 400)                                # empty cart
        a, b = MenuItem.objects.all()[:2]
        self.assertEqual(self.client.post('/api/cart/menu-items', {'menuitem': a.id, 'quantity': 2}).status_code, 201)
        self.assertEqual(self.client.post('/api/cart/menu-items', {'menuitem': b.id, 'quantity': 1}).status_code, 201)
        self.assertEqual(self.client.post('/api/cart/menu-items', {'menuitem': a.id, 'quantity': 1}).status_code, 201)
        self.assertEqual(self.client.post('/api/cart/menu-items', {'menuitem': a.id, 'quantity': 0}).status_code, 400)
        self.assertEqual(self.client.post('/api/cart/menu-items', {'menuitem': 9999, 'quantity': 1}).status_code, 400)
        cart = self.client.get('/api/cart/menu-items').json()
        self.assertEqual(len(cart), 2)
        self.assertEqual(sum(float(c['price']) for c in cart), float(a.price * 3 + b.price))

        r = self.client.post('/api/orders')
        self.assertEqual(r.status_code, 201)
        order_id = r.json()['id']
        self.assertEqual(len(r.json()['order_items']), 2)
        self.assertEqual(float(r.json()['total']), float(a.price * 3 + b.price))
        self.assertEqual(self.client.get('/api/cart/menu-items').json(), [])  # cart emptied
        self.assertEqual(self.client.get('/api/orders').json()['count'], 1)
        self.assertEqual(self.client.get(f'/api/orders/{order_id}').status_code, 200)
        self.assertEqual(self.client.patch(f'/api/orders/{order_id}', {'status': 1}).status_code, 403)

        self.as_user(self.cust2)                                            # someone else's order
        self.assertEqual(self.client.get(f'/api/orders/{order_id}').status_code, 403)
        self.assertEqual(self.client.get('/api/orders').json()['count'], 0)
        self.assertEqual(self.client.get('/api/orders/9999').status_code, 404)

        self.as_user(self.crew)                                             # not assigned yet
        self.assertEqual(self.client.get('/api/orders').json()['count'], 0)

        self.as_user(self.manager)                                          # manager assigns crew
        self.assertEqual(self.client.get('/api/orders').json()['count'], 1)
        r = self.client.patch(f'/api/orders/{order_id}', {'delivery_crew': self.cust.id}, format='json')
        self.assertEqual(r.status_code, 400)                                # not crew member
        r = self.client.patch(f'/api/orders/{order_id}', {'delivery_crew': self.crew.id, 'status': 0}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['delivery_crew_username'], 'crew')
        self.assertEqual(r.json()['status'], 0)

        self.as_user(self.crew2)
        self.assertEqual(self.client.get(f'/api/orders/{order_id}').status_code, 403)
        self.as_user(self.crew)                                             # crew delivers
        self.assertEqual(self.client.get('/api/orders').json()['count'], 1)
        self.assertEqual(self.client.put(f'/api/orders/{order_id}', {'status': 1}).status_code, 403)
        self.assertEqual(self.client.patch(f'/api/orders/{order_id}', {'total': 1, 'status': 1}).status_code, 403)
        self.assertEqual(self.client.patch(f'/api/orders/{order_id}', {'status': 5}).status_code, 400)
        r = self.client.patch(f'/api/orders/{order_id}', {'status': 1}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 1)
        self.assertEqual(self.client.delete(f'/api/orders/{order_id}').status_code, 403)

        self.as_user(self.manager)
        self.assertEqual(self.client.get('/api/orders?status=1').json()['count'], 1)
        self.assertEqual(self.client.get('/api/orders?status=0').json()['count'], 0)
        self.assertEqual(self.client.delete(f'/api/orders/{order_id}').status_code, 200)
        self.assertFalse(Order.objects.exists())

    def test_cart_delete_and_isolation(self):
        a = MenuItem.objects.first()
        self.as_user(self.cust)
        self.client.post('/api/cart/menu-items', {'menuitem': a.id, 'quantity': 1})
        self.as_user(self.cust2)
        self.assertEqual(self.client.get('/api/cart/menu-items').json(), [])
        self.as_user(self.cust)
        self.assertEqual(self.client.delete('/api/cart/menu-items').status_code, 200)
        self.assertEqual(self.client.get('/api/cart/menu-items').json(), [])

    def test_throttling_is_configured(self):
        from django.conf import settings
        rates = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
        self.assertIn('anon', rates)
        self.assertIn('user', rates)
