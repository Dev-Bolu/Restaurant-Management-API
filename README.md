# Restaurant Management API

A Django REST Framework API for running a restaurant's ordering system: menu and categories, customer carts, order placement, and role-based access for managers, delivery crew, and customers.

## Features

- Token authentication with user registration and login (Djoser)
- Role-based access for three roles: **manager**, **delivery crew**, and **customer**
- Menu items and categories, with filtering by category (id, slug or title), featured items, and price range, plus search, ordering, and pagination
- Managers add and remove users from the manager and delivery-crew groups
- Per-user cart: adding an item already in the cart increases its quantity, and the price is recorded at the time of adding
- Order placement from the cart inside a database transaction (the order, its items, and the cart clearing succeed or fail together)
- Order visibility by role: customers see their own orders, delivery crew see orders assigned to them, managers see all orders
- Managers assign orders to delivery crew; delivery crew can only update the status of their assigned orders
- Order filtering by status, date, user, and delivery crew
- Rate limiting: 20 requests/minute for anonymous users, 60 requests/minute for authenticated users

## Tech stack

Django, Django REST Framework, Djoser (token authentication), [database]

## Roles and permissions

| Action | Customer | Delivery crew | Manager |
| --- | --- | --- | --- |
| Browse menu items and categories | Yes | Yes | Yes |
| Create, edit, delete menu items and categories | No | No | Yes |
| Manage manager and delivery-crew groups | No | No | Yes |
| Use own cart | Yes | Yes | Yes |
| Place an order | Yes | Yes | Yes |
| View orders | Own orders | Assigned orders | All orders |
| Update an order | No | Status only (PATCH) | Any field, including assigning delivery crew |
| Delete an order | No | No | Yes |

All endpoints require authentication.

## Order status

`0` means out for delivery (once a crew member is assigned). `1` means delivered.

## Setup

```bash
git clone https://github.com/Dev-Bolu/Restaurant-Management-API.git
cd Restaurant-Management-API
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file next to `settings.py` with these variables (see `.env.example`):

```
SECRET_KEY=
DEBUG=
[other variables]
```

Then run:

```bash
cd RestaurantManagement         # the folder containing manage.py
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Authentication

Register, log in, and send the token with every request.

| Method | URL | Description |
| --- | --- | --- |
| POST | `/api/users/` | Register (`username`, `password`, `email`) |
| GET | `/api/users/me/` | View your profile |
| POST | `/api/token/login/` | Log in (`username`, `password`); returns `auth_token` |
| POST | `/api/token/logout/` | Log out and invalidate the token |

Send the token as `Authorization: Token <auth_token>`.

## Endpoints

Base prefix: `/api/`. Every route works with or without a trailing slash. Lists are paginated: `?page=` and `?perpage=` (default page size 6).

### Categories

| Method | URL | Access |
| --- | --- | --- |
| GET | `/api/categories` | Any logged-in user |
| POST | `/api/categories` | Manager |
| GET | `/api/categories/<id>` | Any logged-in user |
| PUT, PATCH, DELETE | `/api/categories/<id>` | Manager |

### Menu items

| Method | URL | Access |
| --- | --- | --- |
| GET | `/api/menu-items` | Any logged-in user |
| POST | `/api/menu-items` | Manager |
| GET | `/api/menu-items/<id>` | Any logged-in user |
| PUT, PATCH, DELETE | `/api/menu-items/<id>` | Manager |

Query parameters for `GET /api/menu-items`: `category` (id, slug or title), `featured` (true/false), `from_price`, `to_price`, `search`, `ordering` (`price`, `-price`, `title`), `page`, `perpage`.

### User groups (manager only)

| Method | URL | Description |
| --- | --- | --- |
| GET | `/api/groups/manager/users` | List managers |
| POST | `/api/groups/manager/users` | Add a user to the manager group (`username` or `user_id`) |
| DELETE | `/api/groups/manager/users/<id>` | Remove a user from the manager group |
| GET | `/api/groups/delivery-crew/users` | List delivery crew |
| POST | `/api/groups/delivery-crew/users` | Add a user to the delivery-crew group |
| DELETE | `/api/groups/delivery-crew/users/<id>` | Remove a user from the delivery-crew group |

### Cart

| Method | URL | Description |
| --- | --- | --- |
| GET | `/api/cart/menu-items` | List your cart items |
| POST | `/api/cart/menu-items` | Add an item (`menuitem`, `quantity`); adding the same item again increases its quantity |
| DELETE | `/api/cart/menu-items` | Clear your cart |

### Orders

| Method | URL | Description |
| --- | --- | --- |
| GET | `/api/orders` | List orders visible to your role |
| POST | `/api/orders` | Place an order from your current cart (the cart is then cleared) |
| GET | `/api/orders/<id>` | View one order (owner, assigned crew, or manager) |
| PUT, PATCH | `/api/orders/<id>` | Manager: update any field. Delivery crew: PATCH `status` only |
| DELETE | `/api/orders/<id>` | Manager only |

Query parameters for `GET /api/orders`: `status` (`0` or `1`), `date` (`YYYY-MM-DD`), `user` and `delivery_crew` (managers only), `search`, `ordering` (`date`, `total`, `status`, `-date`), `page`, `perpage`.

## Example

```bash
# Log in
curl -X POST http://localhost:8000/api/token/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "you", "password": "yourpassword"}'

# Add an item to your cart
curl -X POST http://localhost:8000/api/cart/menu-items \
  -H "Authorization: Token <auth_token>" \
  -H "Content-Type: application/json" \
  -d '{"menuitem": 1, "quantity": 2}'

# Place the order
curl -X POST http://localhost:8000/api/orders \
  -H "Authorization: Token <auth_token>"
```

## Project structure

```
RestaurantManagement/              Project settings and root URLs
RestaurantManagementAPI/
  models.py                        Category, MenuItem, Cart, Order, OrderItem
  views.py                         Menu, cart, order, and group-management views
  permissions.py                   IsManager and ManagerWriteMixin
  roles.py                         Group helpers (manager, delivery crew)
  pagination.py                    Page-size pagination (?page=, ?perpage=)
  urls.py                          Routes
```

## Author

Akanbi Boluwatife Emmanuel — [GitHub](https://github.com/Dev-Bolu)
