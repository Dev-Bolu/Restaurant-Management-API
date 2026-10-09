from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """?page=2&perpage=3"""
    page_size = 6
    page_size_query_param = 'perpage'
    max_page_size = 100
