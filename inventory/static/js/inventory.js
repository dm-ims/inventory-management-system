/**
 * AJAX enhancements for inventory management
 */

// Auto-refresh stock levels (if enabled)
function autoRefreshStock() {
    // This can be called periodically to refresh stock data
    // Implementation depends on specific requirements
}

// Real-time stock search with autocomplete
$(document).ready(function() {
    var searchTimeout;
    
    // Debounced search
    $('#stock-search-input').on('input', function() {
        clearTimeout(searchTimeout);
        var query = $(this).val();
        
        if (query.length < 2) {
            $('#search-results').hide();
            return;
        }
        
        searchTimeout = setTimeout(function() {
            $.ajax({
                url: '/inventory/api/search/',
                data: {
                    'q': query
                },
                dataType: 'json',
                success: function(data) {
                    displaySearchResults(data);
                }
            });
        }, 300);
    });
    
    function displaySearchResults(results) {
        var html = '<ul class="list-group">';
        results.forEach(function(item) {
            html += '<li class="list-group-item">' + item.name + ' (Qty: ' + item.quantity + ')</li>';
        });
        html += '</ul>';
        $('#search-results').html(html).show();
    }
});

// Dynamic formset management for sales/purchases
function addFormsetRow(formsetPrefix) {
    var totalForms = $('#id_' + formsetPrefix + '-TOTAL_FORMS');
    var formNum = parseInt(totalForms.val());
    var newForm = $('#empty-form-' + formsetPrefix).html().replace(/__prefix__/g, formNum);
    
    $('#formset-' + formsetPrefix).append(newForm);
    totalForms.val(formNum + 1);
    updateFormsetIndices(formsetPrefix);
}

function removeFormsetRow(button, formsetPrefix) {
    $(button).closest('.formset-row').remove();
    updateFormsetIndices(formsetPrefix);
}

function updateFormsetIndices(formsetPrefix) {
    $('#formset-' + formsetPrefix + ' .formset-row').each(function(index) {
        $(this).find('input, select').each(function() {
            var name = $(this).attr('name');
            if (name) {
                name = name.replace(/-\d+-/, '-' + index + '-');
                $(this).attr('name', name);
                $(this).attr('id', 'id_' + name.replace(/-/g, '_'));
            }
        });
    });
    $('#id_' + formsetPrefix + '-TOTAL_FORMS').val($('#formset-' + formsetPrefix + ' .formset-row').length);
}

// Real-time total calculation for sales/purchases
function calculateTotal(formsetPrefix) {
    var total = 0;
    $('.' + formsetPrefix + '-row').each(function() {
        var quantity = parseFloat($(this).find('.quantity-input').val()) || 0;
        var price = parseFloat($(this).find('.price-input').val()) || 0;
        var rowTotal = quantity * price;
        $(this).find('.row-total').text('$' + rowTotal.toFixed(2));
        total += rowTotal;
    });
    $('.' + formsetPrefix + '-grand-total').text('$' + total.toFixed(2));
}

// Stock availability check
function checkStockAvailability(stockId, quantity, callback) {
    $.ajax({
        url: '/inventory/api/check-stock/',
        data: {
            'stock_id': stockId,
            'quantity': quantity
        },
        dataType: 'json',
        success: function(data) {
            if (callback) callback(data);
        }
    });
}

