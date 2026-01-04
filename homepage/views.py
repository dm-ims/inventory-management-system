from django.shortcuts import render, redirect
from django.views.generic import View, TemplateView, ListView, CreateView
from inventory.models import Stock
from django.contrib.auth.models import User
# from django.contrib.auth.forms import UserCreationForm
from .forms import UserCreationForm
from transactions.models import SaleBill, PurchaseBill, SaleItem, PurchaseItem
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import UserUpdateForm
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.db.models import Sum, Count, F, Avg, Max, Min, Q
from django.utils import timezone
from datetime import timedelta
import json

class HomeView(View):
    template_name = "home.html"
    
    def get(self, request):
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Get date range (default: last 30 days)
            days = int(request.GET.get('days', 30))
            start_date = timezone.now() - timedelta(days=days)
            
            # Stock chart data - Top 10 items
            labels = []
            data = []
            stockqueryset = Stock.objects.filter(is_deleted=False).order_by('-quantity')[:10]
            for item in stockqueryset:
                labels.append(item.name)
                data.append(item.quantity)
            
            # KPI Calculations
            # Total inventory value
            total_stock_value = Stock.objects.filter(
                is_deleted=False
            ).aggregate(
                total=Sum(F('quantity') * F('unit_price'))
            )['total'] or 0
            
            # Low stock items
            low_stock_items = Stock.objects.filter(
                is_deleted=False,
                quantity__lte=10
            ).order_by('quantity')  # Order by quantity ascending to show most critical first
            low_stock_count = low_stock_items.count()
            
            # Out of stock items
            out_of_stock_count = Stock.objects.filter(
                is_deleted=False,
                quantity=0
            ).count()
            
            # Monthly sales (last 30 days)
            total_sales = SaleItem.objects.filter(
                billno__time__gte=start_date
            ).aggregate(
                total=Sum('totalprice')
            )['total'] or 0
            
            sales_count = SaleBill.objects.filter(time__gte=start_date).count()
            
            # Monthly purchases (last 30 days)
            total_purchases = PurchaseItem.objects.filter(
                billno__time__gte=start_date
            ).aggregate(
                total=Sum('totalprice')
            )['total'] or 0
            
            purchases_count = PurchaseBill.objects.filter(time__gte=start_date).count()
            
            # Profit calculation
            profit = total_sales - total_purchases
            
            # Previous period for comparison (30 days before start_date)
            prev_start_date = start_date - timedelta(days=days)
            prev_total_sales = SaleItem.objects.filter(
                billno__time__gte=prev_start_date,
                billno__time__lt=start_date
            ).aggregate(total=Sum('totalprice'))['total'] or 0
            
            prev_total_purchases = PurchaseItem.objects.filter(
                billno__time__gte=prev_start_date,
                billno__time__lt=start_date
            ).aggregate(total=Sum('totalprice'))['total'] or 0
            
            # Calculate percentage changes
            sales_change = ((total_sales - prev_total_sales) / prev_total_sales * 100) if prev_total_sales > 0 else 0
            purchases_change = ((total_purchases - prev_total_purchases) / prev_total_purchases * 100) if prev_total_purchases > 0 else 0
            
            # Top selling items (last 30 days)
            top_selling = SaleItem.objects.filter(
                billno__time__gte=start_date
            ).values('stock__name').annotate(
                total_sold=Sum('quantity'),
                revenue=Sum('totalprice')
            ).order_by('-total_sold')[:5]
            
            # Sales trend (last 7 days)
            sales_trend = []
            sales_labels = []
            for i in range(6, -1, -1):
                date = timezone.now() - timedelta(days=i)
                day_sales = SaleItem.objects.filter(
                    billno__time__date=date.date()
                ).aggregate(total=Sum('totalprice'))['total'] or 0
                sales_trend.append(float(day_sales))
                sales_labels.append(date.strftime('%b %d'))
            
            # Purchase trend (last 7 days)
            purchase_trend = []
            for i in range(6, -1, -1):
                date = timezone.now() - timedelta(days=i)
                day_purchases = PurchaseItem.objects.filter(
                    billno__time__date=date.date()
                ).aggregate(total=Sum('totalprice'))['total'] or 0
                purchase_trend.append(float(day_purchases))
            
            # Stock value distribution (for pie chart)
            stock_value_data = []
            stock_value_labels = []
            high_value_stocks = Stock.objects.filter(
                is_deleted=False
            ).annotate(
                value=F('quantity') * F('unit_price')
            ).order_by('-value')[:5]
            
            for stock in high_value_stocks:
                stock_value_labels.append(stock.name)
                stock_value_data.append(float(stock.quantity * stock.unit_price))
            
            # Recent transactions
            sales = SaleBill.objects.prefetch_related('saleitem_set__stock').order_by('-time')[:5]
            purchases = PurchaseBill.objects.select_related('supplier').prefetch_related(
                'purchaseitem_set__stock'
            ).order_by('-time')[:5]
            
            context = {
                'labels': labels,
                'data': data,
                'sales': sales,
                'purchases': purchases,
                'total_stock_value': total_stock_value,
                'low_stock_items': low_stock_items[:5],  # Top 5 low stock items
                'low_stock_count': low_stock_count,
                'out_of_stock_count': out_of_stock_count,
                'total_sales': total_sales,
                'total_purchases': total_purchases,
                'profit': profit,
                'sales_count': sales_count,
                'purchases_count': purchases_count,
                'sales_change': sales_change,
                'purchases_change': purchases_change,
                'top_selling': top_selling,
                'sales_trend': sales_trend,
                'sales_labels': sales_labels,
                'purchase_trend': purchase_trend,
                'stock_value_labels': stock_value_labels,
                'stock_value_data': stock_value_data,
                'days': days,
            }
            return render(request, self.template_name, context)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading home view: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading the dashboard.")
            # Return minimal context on error
            context = {
                'labels': [],
                'data': [],
                'sales': [],
                'purchases': [],
                'total_stock_value': 0,
                'low_stock_count': 0,
                'out_of_stock_count': 0,
                'total_sales': 0,
                'total_purchases': 0,
                'profit': 0,
            }
            return render(request, self.template_name, context)

class DashboardDataView(View):
    """AJAX endpoint for dashboard data updates"""
    def get(self, request):
        try:
            from django.http import JsonResponse
            days = int(request.GET.get('days', 30))
            start_date = timezone.now() - timedelta(days=days)
            
            # Quick stats
            total_stock_value = Stock.objects.filter(
                is_deleted=False
            ).aggregate(total=Sum(F('quantity') * F('unit_price')))['total'] or 0
            
            total_sales = SaleItem.objects.filter(
                billno__time__gte=start_date
            ).aggregate(total=Sum('totalprice'))['total'] or 0
            
            total_purchases = PurchaseItem.objects.filter(
                billno__time__gte=start_date
            ).aggregate(total=Sum('totalprice'))['total'] or 0
            
            low_stock_count = Stock.objects.filter(
                is_deleted=False,
                quantity__lte=10
            ).count()
            
            data = {
                'total_stock_value': float(total_stock_value),
                'total_sales': float(total_sales),
                'total_purchases': float(total_purchases),
                'profit': float(total_sales - total_purchases),
                'low_stock_count': low_stock_count,
            }
            
            return JsonResponse(data)
        except Exception as e:
            logger.error(f"Error generating dashboard data: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

class AboutView(TemplateView):
    template_name = "about.html"

def stock(request):
    stocks = Stock.objects.filter(is_deleted=False)

    context = {
        'stocks': stocks
    }

    return render(request, 'home.html', context)

# list all users
def UserView(request):
    try:
        users = User.objects.all().order_by('-date_joined')
        context = {
            'users': users,
        }
        return render(request, 'user.html', context)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading users: {str(e)}", exc_info=True)
        messages.error(request, "An error occurred while loading users.")
        return redirect('home')

def register(request):
    form = UserCreationForm()

    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('users')

    context = {
        'form': form
    }

    return render(request, 'user_create.html', context)

# def register(request):  
#     if request.method == 'POST':  
#         form = CustomUserCreationForm(request.POST)  
        
#         if form.is_valid():  
#             form.save()
#             return redirect('users')
#     else:  
#         form = CustomUserCreationForm()  
    
#     context = {  
#         'form':form  
#     } 

#     return render(request, 'user_create.html', context)  

def user_delete(request, pk):
    user = User.objects.get(id=pk)

    if request.method == 'POST':
        user.delete()
        return redirect('users')
    
    return render(request, 'user_delete.html')