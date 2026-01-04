from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import F

class StockHistory(models.Model):
    """Audit trail for stock changes"""
    CHANGE_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('adjustment', 'Adjustment'),
        ('edit', 'Edit'),
        ('delete', 'Delete'),
        ('restore', 'Restore'),
    ]
    
    stock = models.ForeignKey('Stock', on_delete=models.CASCADE, related_name='history')
    # Quantity changes
    previous_quantity = models.IntegerField(null=True, blank=True)
    new_quantity = models.IntegerField(null=True, blank=True)
    # Name changes
    previous_name = models.CharField(max_length=30, null=True, blank=True)
    new_name = models.CharField(max_length=30, null=True, blank=True)
    # Price changes
    previous_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    new_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPES)
    changed_by = models.CharField(max_length=100)
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['stock', '-changed_at']),
            models.Index(fields=['change_type', '-changed_at']),
        ]
        verbose_name_plural = 'Stock Histories'
    
    def __str__(self):
        return f"{self.stock.name} - {self.change_type} - {self.changed_at}"


class StockAdjustment(models.Model):
    """Model for stock adjustments (corrections, damages, losses)"""
    ADJUSTMENT_TYPES = [
        ('correction', 'Correction'),
        ('damage', 'Damage'),
        ('loss', 'Loss'),
        ('found', 'Found'),
        ('other', 'Other'),
    ]
    
    stock = models.ForeignKey('Stock', on_delete=models.CASCADE, related_name='adjustments')
    previous_quantity = models.IntegerField()
    adjusted_quantity = models.IntegerField()
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPES)
    reason = models.TextField()
    adjusted_by = models.CharField(max_length=100)
    adjusted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-adjusted_at']
        indexes = [
            models.Index(fields=['stock', '-adjusted_at']),
            models.Index(fields=['adjustment_type', '-adjusted_at']),
        ]
    
    def __str__(self):
        return f"{self.stock.name} - {self.get_adjustment_type_display()} - {self.adjusted_at}"

class Stock(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30, unique=True, db_index=True)
    quantity = models.IntegerField(default=1, db_index=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    last_modified = models.DateTimeField(auto_now=True, db_index=True)
    last_modification = models.CharField(max_length=30, default='')
    modified_by = models.CharField(max_length=30, null=True, blank=True)
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['quantity', 'is_deleted']),
            models.Index(fields=['last_modified']),
        ]

    def clean(self):
        """Validate stock data"""
        if self.quantity < 0:
            raise ValidationError({'quantity': 'Quantity cannot be negative.'})
        if self.unit_price <= 0:
            raise ValidationError({'unit_price': 'Unit price must be greater than zero.'})
    
    def save(self, *args, **kwargs):
        """Override save to run validation and auto-populate last_modification"""
        # Auto-populate last_modification with current date/time whenever stock is saved
        from django.utils import timezone
        self.last_modification = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        self.full_clean()
        super().save(*args, **kwargs)

    def check_stock_availability(self, requested_quantity):
        """Check if requested quantity is available"""
        if self.is_deleted:
            return False, "Stock item is deleted"
        if self.quantity < requested_quantity:
            return False, f"Insufficient stock. Available: {self.quantity}, Requested: {requested_quantity}"
        return True, "Stock available"

    def reserve_stock(self, quantity):
        """Reserve stock (decrease quantity)"""
        if not self.check_stock_availability(quantity)[0]:
            raise ValidationError("Cannot reserve stock: insufficient quantity")
        self.quantity -= quantity
        self.save()

    def release_stock(self, quantity):
        """Release stock (increase quantity)"""
        self.quantity += quantity
        self.save()

    def __str__(self):
        return self.name