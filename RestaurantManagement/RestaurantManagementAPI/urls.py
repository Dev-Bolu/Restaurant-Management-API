from django.urls import re_path

from . import views

# Every route works with or without a trailing slash.
def route(pattern, view, name):
    return re_path(rf'^{pattern}/?$', view.as_view(), name=name)


urlpatterns = [
    route('categories', views.CategoriesView, 'categories'),
    route(r'categories/(?P<pk>\d+)', views.SingleCategoryView, 'category'),

    route('menu-items', views.MenuItemsView, 'menu-items'),
    route(r'menu-items/(?P<pk>\d+)', views.SingleMenuItemView, 'menu-item'),

    route('groups/manager/users', views.ManagerUsersView, 'manager-users'),
    route(r'groups/manager/users/(?P<pk>\d+)', views.ManagerSingleUserView, 'manager-user'),
    route('groups/delivery-crew/users', views.DeliveryCrewUsersView, 'delivery-crew-users'),
    route(r'groups/delivery-crew/users/(?P<pk>\d+)', views.DeliveryCrewSingleUserView,
          'delivery-crew-user'),

    route('cart/menu-items', views.CartView, 'cart'),

    route('orders', views.OrdersView, 'orders'),
    route(r'orders/(?P<pk>\d+)', views.SingleOrderView, 'order'),
]
