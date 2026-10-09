# Restaurant Management API

A role-based REST API for restaurant management (Little Lemon course project), built with **Django**, **Django REST Framework** and **Djoser**, using **SQLite**. Customers can browse the menu, fill a cart and place orders. Managers manage the menu and assign delivery crew, and the crew mark orders as delivered.

## Features

- Token authentication and user registration (Djoser)
- Three roles: **Manager**, **Delivery crew** and **Customer** (any user not in a group)
- Menu and category management (managers/admin only for writes)
- Cart and order flow: the cart becomes an order, then is emptied
- Filtering, search, sorting and pagination on menu items and orders
- Throttling for anonymous and authenticated users
- Consistent HTTP status codes and error messages
- Automated tests (`python manage.py test`)

## Tech stack

Python, Django 5.2, Django REST Framework, Djoser, SQLite, pipenv

## Project structure

```
RestaurantManagement/                 project directory
├── RestaurantManagement/             settings and root URLs
├── RestaurantManagementAPI/          the single app holding all endpoints
│   ├── models.py            Category, MenuItem, Cart, Order, OrderItem
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py       manager-only write permission
│   ├── roles.py             group/role helpers
│   ├── pagination.py
│   ├── urls.py
│   ├── tests.py
│   └── management/commands/seed_demo.py
├── db.sqlite3               included, pre-loaded with demo data
├── notes.txt                credentials and endpoint cheat sheet
├── Pipfile / Pipfile.lock
└── manage.py
```

## Getting started

```bash
cd RestaurantManagement
pipenv shell
pipenv install
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

The included `db.sqlite3` already contains the demo users and data, so you can skip straight to `runserver`.

To rebuild the demo data on a fresh database:

```bash
python manage.py migrate
python manage.py seed_demo
```

Run the tests:

```bash
python manage.py test
```

## Demo accounts

All accounts use the password `Lemon@2026pass`.

| Username | Role |
|---|---|
| admin | Superuser (Django admin at `/admin/`) |
| manager1, manager2 | Manager |
| delivery1, delivery2 | Delivery crew |
| customer1, customer2, customer3 | Customer |

Groups are named **Manager** and **Delivery crew**. Matching is case-insensitive, so recreated groups such as "delivery crew" also work.

## Authentication

1. Log in: `POST /token/login/` with `username` and `password`. The response is `{"auth_token": "..."}`.
2. Send the token on every request: `Authorization: Token <auth_token>`.
3. Register: `POST /api/users` with `username`, `email` and `password`.
4. Current user: `GET /api/users/me/`.

For the browsable API in a browser, log in at `/api-auth/login/`.

## API endpoints

Trailing slashes are optional on every route.

### Categories

| Method | Endpoint | Role | Purpose |
|---|---|---|---|
| GET | `/api/categories` | Any logged-in user | List categories |
| POST | `/api/categories` | Manager/admin | Create a category |

### Menu items

| Method | Endpoint | Role | Purpose |
|---|---|---|---|
| GET | `/api/menu-items` | Any logged-in user | List items |
| POST | `/api/menu-items` | Manager/admin | Create an item (201) |
| GET | `/api/menu-items/{id}` | Any logged-in user | Single item |
| PUT, PATCH | `/api/menu-items/{id}` | Manager/admin | Update (PATCH `featured` sets the item of the day) |
| DELETE | `/api/menu-items/{id}` | Manager/admin | Delete |

Everyone else gets 403 on writes.

**Query parameters for `GET /api/menu-items`**

| Parameter | Example | Effect |
|---|---|---|
| `category` | `?category=mains` or `?category=2` | Filter by category slug, title or id |
| `ordering` | `?ordering=price` or `?ordering=-price` | Sort (also `title`) |
| `page`, `perpage` | `?page=2&perpage=3` | Pagination (default 6 per page) |
| `search` | `?search=lemon` | Search title and category |
| `featured` | `?featured=true` | Item-of-the-day filter |
| `from_price`, `to_price` | `?from_price=5&to_price=15` | Price range |

### Group management (manager/admin only)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/groups/manager/users` | List managers |
| POST | `/api/groups/manager/users` | Add a manager, body `{"username": "..."}` (201) |
| DELETE | `/api/groups/manager/users/{userId}` | Remove a manager (200, or 404) |
| GET | `/api/groups/delivery-crew/users` | List delivery crew |
| POST | `/api/groups/delivery-crew/users` | Add crew, body `{"username": "..."}` (201) |
| DELETE | `/api/groups/delivery-crew/users/{userId}` | Remove crew (200, or 404) |

### Cart (current user)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/cart/menu-items` | Items in my cart |
| POST | `/api/cart/menu-items` | Add an item, body `{"menuitem": 1, "quantity": 2}` |
| DELETE | `/api/cart/menu-items` | Empty my cart |

Adding an item that is already in the cart increases its quantity.

### Orders

| Method | Endpoint | Role | Purpose |
|---|---|---|---|
| GET | `/api/orders` | All | Customer: own orders. Delivery crew: assigned orders. Manager: all orders |
| POST | `/api/orders` | Customer | Turn the cart into an order, then empty the cart |
| GET | `/api/orders/{id}` | Owner, assigned crew, manager | Order with its items (403 for other users) |
| PUT, PATCH | `/api/orders/{id}` | Manager | Set `delivery_crew` and `status` |
| PATCH | `/api/orders/{id}` | Delivery crew | Update `status` only |
| DELETE | `/api/orders/{id}` | Manager | Delete the order |

Order status: `0` is out for delivery, `1` is delivered. Order lists support `?status=0|1`, `?date=YYYY-MM-DD`, `?ordering=-date` or `total`, `?search=`, and `?page=` / `?perpage=`.

## Status codes

| Code | Meaning |
|---|---|
| 200 | Successful GET, PUT, PATCH, DELETE |
| 201 | Successful POST |
| 400 | Validation failed |
| 401 | Not authenticated or bad token |
| 403 | Authenticated but not allowed |
| 404 | Resource not found |
| 429 | Throttled |

## Throttling

Anonymous users: 20 requests per minute. Authenticated users: 60 requests per minute. Change these in `RestaurantManagement/settings.py` under `DEFAULT_THROTTLE_RATES`.

## Example walkthrough

1. Log in as `admin` and add `customer3` to the manager group: `POST /api/groups/manager/users` with `{"username": "customer3"}`.
2. Log in as `manager1` and set an item of the day: `PATCH /api/menu-items/1` with `{"featured": true}`.
3. Log in as `customer2`, add items with `POST /api/cart/menu-items`, then place the order with `POST /api/orders`.
4. As `manager1`, assign it: `PATCH /api/orders/{id}` with `{"delivery_crew": 5, "status": 0}`.
5. As `delivery1`, deliver it: `PATCH /api/orders/{id}` with `{"status": 1}`.
