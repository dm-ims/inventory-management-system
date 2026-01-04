from django import forms
from .models import Stock, StockAdjustment

class StockForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):                                                        # used to set css classes to the various fields
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'textinput form-control'})
        self.fields['quantity'].widget.attrs.update({'class': 'textinput form-control', 'min': '0'})
        self.fields['unit_price'].widget.attrs.update({'class': 'textinput form-control', 'min': '1.00'})

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity < 0:
            raise forms.ValidationError("Quantity cannot be negative.")
        return quantity
    
    def clean_unit_price(self):
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price is not None and unit_price <= 0:
            raise forms.ValidationError("Unit price must be greater than zero.")
        return unit_price

    class Meta:
        model = Stock
        fields = ['name', 'quantity', 'unit_price']


class StockEditDetailsForm(forms.ModelForm):
    """Form for editing only name and price (not quantity)"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'textinput form-control'})
        self.fields['unit_price'].widget.attrs.update({'class': 'textinput form-control', 'min': '1.00'})
    
    def clean_unit_price(self):
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price is not None and unit_price <= 0:
            raise forms.ValidationError("Unit price must be greater than zero.")
        return unit_price
    
    class Meta:
        model = Stock
        fields = ['name', 'unit_price']


class StockAdjustmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.stock = kwargs.pop('stock', None)
        super().__init__(*args, **kwargs)
        self.fields['adjustment_type'].widget.attrs.update({'class': 'form-control'})
        self.fields['adjusted_quantity'].widget.attrs.update({'class': 'form-control', 'min': '0'})
        self.fields['reason'].widget.attrs.update({'class': 'form-control', 'rows': '4'})
        
        if self.stock:
            self.fields['adjusted_quantity'].label = f'New Quantity (Current: {self.stock.quantity})'
    
    def clean_adjusted_quantity(self):
        adjusted_quantity = self.cleaned_data.get('adjusted_quantity')
        if adjusted_quantity is not None and adjusted_quantity < 0:
            raise forms.ValidationError("Adjusted quantity cannot be negative.")
        return adjusted_quantity
    
    class Meta:
        model = StockAdjustment
        fields = ['adjustment_type', 'adjusted_quantity', 'reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4}),
        }
