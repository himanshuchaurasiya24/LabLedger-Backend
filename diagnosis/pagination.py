from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class for the API.
    Sets the default page size to 40.
    """
    page_size = 40
    page_size_query_param = 'page_size'
    max_page_size = 100