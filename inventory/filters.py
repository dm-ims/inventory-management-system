import django_filters
from django.db import models
from .models import Stock    

class StockFilter(django_filters.FilterSet):
    """Enhanced filter for stock items with multiple filter options"""
    name = django_filters.CharFilter(lookup_expr='icontains', label='Item Name')
    quantity_min = django_filters.NumberFilter(field_name='quantity', lookup_expr='gte', label='Min Quantity')
    quantity_max = django_filters.NumberFilter(field_name='quantity', lookup_expr='lte', label='Max Quantity')
    price_min = django_filters.NumberFilter(field_name='unit_price', lookup_expr='gte', label='Min Price')
    price_max = django_filters.NumberFilter(field_name='unit_price', lookup_expr='lte', label='Max Price')
    modified_by = django_filters.CharFilter(field_name='modified_by', lookup_expr='icontains', label='Modified By')
    last_modified_after = django_filters.DateTimeFilter(field_name='last_modified', lookup_expr='gte', label='Modified After')
    last_modified_before = django_filters.DateTimeFilter(field_name='last_modified', lookup_expr='lte', label='Modified Before')
    
    low_stock = django_filters.BooleanFilter(
        method='filter_low_stock',
        label='Show only low stock items (quantity <= 10)'
    )
    out_of_stock = django_filters.BooleanFilter(
        method='filter_out_of_stock',
        label='Show only out of stock items'
    )
    
    def filter_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(quantity__lte=10)
        return queryset
    
    def filter_out_of_stock(self, queryset, name, value):
        if value:
            return queryset.filter(quantity=0)
        return queryset
    
    class Meta:
        model = Stock
        fields = ['name', 'quantity_min', 'quantity_max', 'price_min', 'price_max', 
                  'modified_by', 'last_modified_after', 'last_modified_before', 
                  'low_stock', 'out_of_stock']