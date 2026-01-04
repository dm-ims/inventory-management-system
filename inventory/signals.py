"""
Django signals for inventory app to track stock changes automatically.
"""
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from .models import Stock, StockHistory
import logging

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Stock)
def track_stock_changes(sender, instance, **kwargs):
    """Track stock changes (quantity, name, price) before save"""
    if instance.pk:  # Only for existing instances
        try:
            old_instance = Stock.objects.get(pk=instance.pk)
            # Track quantity changes
            if old_instance.quantity != instance.quantity:
                instance._quantity_changed = True
                instance._previous_quantity = old_instance.quantity
            # Track name changes
            if old_instance.name != instance.name:
                instance._name_changed = True
                instance._previous_name = old_instance.name
            # Track price changes
            if old_instance.unit_price != instance.unit_price:
                instance._price_changed = True
                instance._previous_price = old_instance.unit_price
            instance._old_is_deleted = old_instance.is_deleted
        except Stock.DoesNotExist:
            pass

@receiver(post_save, sender=Stock)
def log_stock_changes(sender, instance, created, **kwargs):
    """Log stock changes to StockHistory"""
    if created:
        # New stock item created
        StockHistory.objects.create(
            stock=instance,
            previous_quantity=0,
            new_quantity=instance.quantity,
            change_type='edit',
            changed_by=getattr(instance, '_changed_by', 'System'),
            reason='Stock item created',
            changed_at=timezone.now()
        )
    else:
        # Check for any changes
        quantity_changed = hasattr(instance, '_quantity_changed') and instance._quantity_changed
        name_changed = hasattr(instance, '_name_changed') and instance._name_changed
        price_changed = hasattr(instance, '_price_changed') and instance._price_changed
        is_deleted_changed = hasattr(instance, '_old_is_deleted') and instance._old_is_deleted != instance.is_deleted
        
        if quantity_changed or name_changed or price_changed or is_deleted_changed:
            # Determine change type
            change_type = 'edit'
            if is_deleted_changed:
                if instance.is_deleted:
                    change_type = 'delete'
                else:
                    change_type = 'restore'
            
            # Build reason message
            changes = []
            if name_changed:
                changes.append(f"Name: {instance._previous_name} → {instance.name}")
            if price_changed:
                changes.append(f"Price: ${instance._previous_price} → ${instance.unit_price}")
            if quantity_changed:
                changes.append(f"Quantity: {instance._previous_quantity} → {instance.quantity}")
            
            reason = getattr(instance, '_change_reason', None)
            if not reason:
                if changes:
                    reason = '; '.join(changes)
                else:
                    reason = 'Stock updated'
            
            # Create history entry
            StockHistory.objects.create(
                stock=instance,
                previous_quantity=getattr(instance, '_previous_quantity', None) if quantity_changed else None,
                new_quantity=instance.quantity if quantity_changed else None,
                previous_name=getattr(instance, '_previous_name', None) if name_changed else None,
                new_name=instance.name if name_changed else None,
                previous_price=getattr(instance, '_previous_price', None) if price_changed else None,
                new_price=instance.unit_price if price_changed else None,
                change_type=change_type,
                changed_by=getattr(instance, '_changed_by', instance.modified_by or 'System'),
                reason=reason,
                changed_at=timezone.now()
            )
            
            # Clean up temporary attributes
            for attr in ['_quantity_changed', '_previous_quantity', '_name_changed', '_previous_name', 
                        '_price_changed', '_previous_price', '_old_is_deleted']:
                if hasattr(instance, attr):
                    delattr(instance, attr)

def log_stock_transaction(stock, previous_quantity, new_quantity, change_type, changed_by, reason=''):
    """Helper function to log stock transactions (purchases, sales)"""
    try:
        StockHistory.objects.create(
            stock=stock,
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            change_type=change_type,
            changed_by=changed_by,
            reason=reason,
            changed_at=timezone.now()
        )
    except Exception as e:
        logger.error(f"Error logging stock history: {str(e)}", exc_info=True)

