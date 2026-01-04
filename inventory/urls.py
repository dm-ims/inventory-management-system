from django.urls import path
# Unused - django.conf.urls.url is deprecated in Django 4.0+
# from django.conf.urls import url
from . import views

urlpatterns = [
    path('', views.StockListView.as_view(), name='inventory'),
    path('new', views.StockCreateView, name='new-stock'),
    path('stock/<pk>/edit', views.StockUpdateView.as_view(), name='edit-stock'),
    path('stock/<pk>/delete', views.StockDeleteView.as_view(), name='delete-stock'),
    path('stock/<pk>/history', views.StockHistoryView.as_view(), name='stock-history'),
    path('bulk-action', views.BulkStockActionView.as_view(), name='bulk-stock-action'),
    path('export', views.StockExportView.as_view(), name='export-stock'),
    path('export/<str:stock_ids>', views.StockExportView.as_view(), name='export-stock-selected'),
    path('stock/<pk>/adjust', views.StockAdjustmentView.as_view(), name='stock-adjust'),
    path('report', views.StockReportView.as_view(), name='stock-report'),
    path('import', views.StockImportView.as_view(), name='stock-import'),
    path('api/search/', views.StockSearchView.as_view(), name='stock-search-api'),
    path('api/check-stock/', views.CheckStockAvailabilityView.as_view(), name='check-stock-api'),
    path('api/get-stock-price/', views.GetStockPriceView.as_view(), name='get-stock-price-api'),
]