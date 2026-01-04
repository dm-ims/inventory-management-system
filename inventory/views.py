from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    View,
    CreateView,
    UpdateView
)
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from .models import Stock, StockHistory, StockAdjustment
from .forms import StockForm, StockAdjustmentForm, StockEditDetailsForm
from django_filters.views import FilterView
from .filters import StockFilter
from django.db import transaction
from django.db.models import Max, Min, Avg, Sum, Count, F, Q
from django.utils import timezone
import datetime
import logging

logger = logging.getLogger(__name__)

class StockListView(FilterView):
    filterset_class = StockFilter
    template_name = 'inventory.html'
    paginate_by = 10
    
    def get_queryset(self):
        """Optimize query with indexes"""
        return Stock.objects.filter(is_deleted=False).order_by('-last_modified')


class StockUpdateView(SuccessMessageMixin, UpdateView):                                 # updateview class to edit stock, mixin used to display message
    model = Stock                                                                       # setting 'Stock' model as model
    form_class = StockEditDetailsForm                                                   # setting 'StockEditDetailsForm' form as form (only name and price)
    template_name = "edit_stock.html"                                                   # 'edit_stock.html' used as the template
    success_url = '/inventory'                                                          # redirects to 'inventory' page in the url after submitting the form
    success_message = "Stock details have been updated successfully"                     # displays message when form is submitted

    @transaction.atomic
    def post(self, request, pk):
        try:
            stock = get_object_or_404(Stock, pk=pk)
            old_name = stock.name
            old_price = stock.unit_price
            form = StockEditDetailsForm(request.POST, instance=stock)
            if form.is_valid():
                stock = form.save(commit=False)
                stock._changed_by = request.user.username if request.user.is_authenticated else 'System'
                
                # Track changes explicitly for history logging
                changes = []
                if old_name != stock.name:
                    stock._name_changed = True
                    stock._previous_name = old_name
                    changes.append(f"Name: {old_name} → {stock.name}")
                if old_price != stock.unit_price:
                    stock._price_changed = True
                    stock._previous_price = old_price
                    changes.append(f"Price: ${old_price} → ${stock.unit_price}")
                
                stock._change_reason = '; '.join(changes) if changes else 'Stock details updated'
                stock.last_modified = datetime.datetime.now()
                stock.last_modification = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                stock.modified_by = request.user.username
                stock.full_clean()  # Run model validation
                stock.save()
                messages.success(request, self.success_message)
                logger.info(f"Stock details for {stock.name} updated by {request.user.username}")
                return redirect('inventory')
            else:
                # Form validation errors
                context = self.get_context_data()
                context['form'] = form
                return render(request, self.template_name, context)
        except Exception as e:
            logger.error(f"Error updating stock: {str(e)}", exc_info=True)
            messages.error(request, f"An error occurred while updating stock: {str(e)}")
            return redirect('inventory')

    def get_context_data(self, **kwargs):                                               # used to send additional context
        context = super().get_context_data(**kwargs)
        context["title"] = 'Edit Stock Details'
        context["savebtn"] = 'Update Details'
        context["delbtn"] = None  # Remove delete button from edit details page
        return context


class StockDeleteView(View):                                                            # view class to delete stock
    template_name = "delete_stock.html"                                                 # 'delete_stock.html' used as the template
    success_message = "Inventory item has been deleted successfully"                             # displays message when form is submitted

    def get(self, request, pk):
        stock = get_object_or_404(Stock, pk=pk)
        return render(request, self.template_name, {'object' : stock})

    @transaction.atomic
    def post(self, request, pk):
        try:
            stock = get_object_or_404(Stock, pk=pk)
            stock.is_deleted = True
            stock.save()
            messages.success(request, self.success_message)
            logger.info(f"Stock {stock.name} deleted by {request.user.username}")
            return redirect('inventory')
        except Exception as e:
            logger.error(f"Error deleting stock: {str(e)}", exc_info=True)
            messages.error(request, f"An error occurred while deleting stock: {str(e)}")
            return redirect('inventory')

@transaction.atomic
def StockCreateView(request):
    if request.method == 'POST':
        form = StockForm(request.POST)
        if form.is_valid():
            try:
                instance = form.save(commit=False)
                instance.modified_by = request.user.username if request.user.is_authenticated else 'System'
                instance.last_modified = datetime.datetime.now()
                instance.last_modification = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                instance.full_clean()  # Run model validation
                instance.save()
                messages.success(request, 'Inventory item has been added successfully')
                logger.info(f"Stock {instance.name} created by {request.user.username if request.user.is_authenticated else 'System'}")
                return redirect('inventory')
            except Exception as e:
                logger.error(f"Error creating stock: {str(e)}", exc_info=True)
                messages.error(request, f"An error occurred while creating stock: {str(e)}")
        else:
            # Form validation errors are already handled by form
            pass
    else:
        form = StockForm()

    context = {
        'form': form,
        'title': 'New Stock',
        'savebtn': 'Add Item',
    }
    return render(request, 'edit_stock.html', context)

class StockHistoryView(View):
    """View to display stock change history"""
    template_name = 'stock_history.html'
    
    def get(self, request, pk):
        try:
            stock = get_object_or_404(Stock, pk=pk)
            history = StockHistory.objects.filter(stock=stock).order_by('-changed_at')[:50]
            context = {
                'stock': stock,
                'history': history,
            }
            return render(request, self.template_name, context)
        except Exception as e:
            logger.error(f"Error loading stock history: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading stock history.")
            return redirect('inventory')

class StockSearchView(View):
    """AJAX endpoint for stock search autocomplete"""
    def get(self, request):
        from django.http import JsonResponse
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return JsonResponse([], safe=False)
        
        stocks = Stock.objects.filter(
            is_deleted=False,
            name__icontains=query
        )[:10]
        
        results = [{
            'id': stock.id,
            'name': stock.name,
            'quantity': stock.quantity,
            'unit_price': float(stock.unit_price)
        } for stock in stocks]
        
        return JsonResponse(results, safe=False)

class CheckStockAvailabilityView(View):
    """AJAX endpoint to check stock availability"""
    def get(self, request):
        from django.http import JsonResponse
        stock_id = request.GET.get('stock_id')
        quantity = int(request.GET.get('quantity', 0))
        
        try:
            stock = Stock.objects.get(pk=stock_id, is_deleted=False)
            is_available, message = stock.check_stock_availability(quantity)
            
            return JsonResponse({
                'available': is_available,
                'message': message,
                'current_quantity': stock.quantity,
                'unit_price': float(stock.unit_price)
            })
        except Stock.DoesNotExist:
            return JsonResponse({
                'available': False,
                'message': 'Stock item not found'
            }, status=404)

class GetStockPriceView(View):
    """AJAX endpoint to get stock price"""
    def get(self, request):
        from django.http import JsonResponse
        stock_id = request.GET.get('stock_id')
        
        try:
            stock = Stock.objects.get(pk=stock_id, is_deleted=False)
            return JsonResponse({
                'unit_price': float(stock.unit_price),
                'quantity': stock.quantity
            })
        except Stock.DoesNotExist:
            return JsonResponse({
                'error': 'Stock item not found'
            }, status=404)

class BulkStockActionView(View):
    """Handle bulk operations on stock items"""
    @transaction.atomic
    def post(self, request):
        if not request.user.is_superuser:
            messages.error(request, "You don't have permission to perform this action.")
            return redirect('inventory')
        
        try:
            action = request.POST.get('action')
            stock_ids = request.POST.getlist('stock_ids')
            
            if not stock_ids:
                messages.error(request, "No items selected.")
                return redirect('inventory')
            
            stocks = Stock.objects.filter(pk__in=stock_ids, is_deleted=False)
            
            if action == 'delete':
                count = 0
                for stock in stocks:
                    stock.is_deleted = True
                    stock._changed_by = request.user.username
                    stock._change_reason = 'Bulk delete'
                    stock.save()
                    count += 1
                messages.success(request, f"{count} item(s) deleted successfully.")
                logger.info(f"Bulk delete: {count} items deleted by {request.user.username}")
            
            elif action == 'export':
                # Export functionality will be handled separately
                return redirect('export-stock-selected', stock_ids=','.join(stock_ids))
            
            else:
                messages.error(request, "Invalid action selected.")
            
            return redirect('inventory')
        except Exception as e:
            logger.error(f"Error in bulk stock action: {str(e)}", exc_info=True)
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('inventory')

class StockExportView(View):
    """Export stock to CSV"""
    def get(self, request, stock_ids=None):
        try:
            import csv
            from django.http import HttpResponse
            from datetime import datetime
            
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="stock_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Name', 'Quantity', 'Unit Price', 'Last Modified', 'Modified By'])
            
            if stock_ids:
                # Export selected items
                ids = stock_ids.split(',')
                stocks = Stock.objects.filter(pk__in=ids, is_deleted=False)
            else:
                # Export all filtered items (from query params)
                filter_params = request.GET.copy()
                filter_params.pop('export', None)  # Remove export param
                stocks = StockFilter(filter_params, queryset=Stock.objects.filter(is_deleted=False)).qs
            
            for stock in stocks:
                writer.writerow([
                    stock.name,
                    stock.quantity,
                    stock.unit_price,
                    stock.last_modified.strftime('%Y-%m-%d %H:%M:%S'),
                    stock.modified_by or 'N/A'
                ])
            
            logger.info(f"Stock export: {stocks.count()} items exported by {request.user.username if request.user.is_authenticated else 'Anonymous'}")
            return response
        except Exception as e:
            logger.error(f"Error exporting stock: {str(e)}", exc_info=True)
            messages.error(request, f"An error occurred while exporting: {str(e)}")
            return redirect('inventory')

class StockAdjustmentView(View):
    """View for creating stock adjustments"""
    template_name = 'stock_adjustment.html'
    
    def get(self, request, pk):
        try:
            stock = get_object_or_404(Stock, pk=pk, is_deleted=False)
            form = StockAdjustmentForm(stock=stock)
            context = {
                'stock': stock,
                'form': form,
            }
            return render(request, self.template_name, context)
        except Exception as e:
            logger.error(f"Error loading stock adjustment form: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading the adjustment form.")
            return redirect('inventory')
    
    @transaction.atomic
    def post(self, request, pk):
        try:
            stock = get_object_or_404(Stock, pk=pk, is_deleted=False)
            form = StockAdjustmentForm(request.POST, stock=stock)
            
            if form.is_valid():
                adjustment = form.save(commit=False)
                adjustment.stock = stock
                adjustment.previous_quantity = stock.quantity
                adjustment.adjusted_by = request.user.username if request.user.is_authenticated else 'System'
                
                # Update stock quantity
                stock.quantity = adjustment.adjusted_quantity
                stock._changed_by = adjustment.adjusted_by
                stock._change_reason = f"Stock adjustment: {adjustment.get_adjustment_type_display()}"
                stock.last_modification = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                stock.save()
                
                # Save adjustment
                adjustment.save()
                
                # Log to history
                from .signals import log_stock_transaction
                log_stock_transaction(
                    stock=stock,
                    previous_quantity=adjustment.previous_quantity,
                    new_quantity=adjustment.adjusted_quantity,
                    change_type='adjustment',
                    changed_by=adjustment.adjusted_by,
                    reason=f"{adjustment.get_adjustment_type_display()}: {adjustment.reason}"
                )
                
                messages.success(request, f"Stock adjusted successfully. New quantity: {stock.quantity}")
                logger.info(f"Stock {stock.name} adjusted by {adjustment.adjusted_by}: {adjustment.previous_quantity} -> {adjustment.adjusted_quantity}")
                return redirect('inventory')
            else:
                context = {
                    'stock': stock,
                    'form': form,
                }
                return render(request, self.template_name, context)
        except Exception as e:
            logger.error(f"Error creating stock adjustment: {str(e)}", exc_info=True)
            messages.error(request, f"An error occurred while adjusting stock: {str(e)}")
            return redirect('inventory')

class StockImportView(View):
    """Import stock from CSV file"""
    template_name = 'stock_import.html'
    
    def get(self, request):
        if not request.user.is_superuser:
            messages.error(request, "You don't have permission to import stock.")
            return redirect('inventory')
        return render(request, self.template_name, {})
    
    @transaction.atomic
    def post(self, request):
        if not request.user.is_superuser:
            messages.error(request, "You don't have permission to import stock.")
            return redirect('inventory')
        
        try:
            import csv
            from io import TextIOWrapper
            from django.core.exceptions import ValidationError
            
            if 'csv_file' not in request.FILES:
                messages.error(request, "Please select a CSV file to upload.")
                return render(request, self.template_name, {})
            
            csv_file = request.FILES['csv_file']
            decoded_file = TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.DictReader(decoded_file)
            
            errors = []
            success_count = 0
            rows_processed = []
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    name = row.get('Name') or row.get('name') or row.get('Item Name') or row.get('item_name')
                    quantity = row.get('Quantity') or row.get('quantity') or row.get('Qty') or row.get('qty')
                    unit_price = row.get('Unit Price') or row.get('unit_price') or row.get('Price') or row.get('price')
                    
                    if not name or not quantity or not unit_price:
                        errors.append(f"Row {row_num}: Missing required field")
                        continue
                    
                    try:
                        quantity = int(quantity)
                        unit_price = float(unit_price)
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid number format")
                        continue
                    
                    stock, created = Stock.objects.get_or_create(
                        name=name,
                        defaults={
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'modified_by': request.user.username if request.user.is_authenticated else 'System',
                            'last_modification': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                    )
                    
                    if not created:
                        stock.quantity += quantity
                        stock.unit_price = unit_price
                        stock.modified_by = request.user.username if request.user.is_authenticated else 'System'
                        stock.last_modification = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                        stock.full_clean()
                        stock.save()
                        rows_processed.append(f"Row {row_num}: Updated {name}")
                    else:
                        rows_processed.append(f"Row {row_num}: Created {name}")
                        success_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    logger.error(f"Error importing stock row {row_num}: {str(e)}", exc_info=True)
            
            if rows_processed:
                messages.success(request, f"Processed {len(rows_processed)} row(s). {success_count} new item(s) created.")
            if errors:
                messages.warning(request, f"Encountered {len(errors)} error(s).")
            
            context = {
                'errors': errors[:20],
                'success_count': success_count,
                'rows_processed': rows_processed[:20]
            }
            return render(request, self.template_name, context)
            
        except Exception as e:
            logger.error(f"Error importing stock: {str(e)}", exc_info=True)
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, self.template_name, {})

class StockReportView(View):
    """Comprehensive stock analysis report"""
    template_name = 'stock_report.html'
    
    def get(self, request):
        try:
            from django.db.models import Sum, Count, Avg, F, Q
            from django.utils import timezone
            from datetime import timedelta
            from transactions.models import SaleItem, PurchaseItem
            
            # Get date range
            days = int(request.GET.get('days', 30))
            start_date = timezone.now() - timedelta(days=days)
            
            # Stock valuation
            stock_analysis = Stock.objects.filter(
                is_deleted=False
            ).aggregate(
                total_items=Count('id'),
                total_quantity=Sum('quantity'),
                total_value=Sum(F('quantity') * F('unit_price')),
                avg_price=Avg('unit_price'),
                max_price=Max('unit_price'),
                min_price=Min('unit_price')
            )
            
            # Low stock analysis
            low_stock = Stock.objects.filter(
                is_deleted=False,
                quantity__lte=10
            ).order_by('quantity')
            
            # Out of stock
            out_of_stock = Stock.objects.filter(
                is_deleted=False,
                quantity=0
            )
            
            # Items sold in period
            items_sold = SaleItem.objects.filter(
                billno__time__gte=start_date
            ).values('stock__name').annotate(
                total_sold=Sum('quantity'),
                revenue=Sum('totalprice')
            ).order_by('-total_sold')[:10]
            
            # Items purchased in period
            items_purchased = PurchaseItem.objects.filter(
                billno__time__gte=start_date
            ).values('stock__name').annotate(
                total_purchased=Sum('quantity'),
                cost=Sum('totalprice')
            ).order_by('-total_purchased')[:10]
            
            # Slow moving items (not sold in last 90 days)
            ninety_days_ago = timezone.now() - timedelta(days=90)
            slow_moving = Stock.objects.filter(
                is_deleted=False
            ).exclude(
                saleitem__billno__time__gte=ninety_days_ago
            ).annotate(
                value=F('quantity') * F('unit_price')
            ).distinct()[:10]
            
            # High value items
            high_value = Stock.objects.filter(
                is_deleted=False
            ).annotate(
                value=F('quantity') * F('unit_price')
            ).order_by('-value')[:10]
            
            # Add value to low_stock items for display
            low_stock = low_stock.annotate(
                value=F('quantity') * F('unit_price')
            )
            
            context = {
                'stock_analysis': stock_analysis,
                'items_sold': items_sold,
                'items_purchased': items_purchased,
                'low_stock': low_stock,
                'out_of_stock': out_of_stock,
                'slow_moving': slow_moving,
                'high_value': high_value,
                'days': days,
                'start_date': start_date,
            }
            return render(request, self.template_name, context)
        except Exception as e:
            logger.error(f"Error generating stock report: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while generating the report.")
            return redirect('inventory')
