/**
 * Dashboard AJAX functionality for real-time updates
 */

// Auto-refresh dashboard data
var dashboardRefreshInterval;

function startDashboardAutoRefresh(intervalSeconds) {
    intervalSeconds = intervalSeconds || 30; // Default 30 seconds
    
    dashboardRefreshInterval = setInterval(function() {
        refreshDashboardData();
    }, intervalSeconds * 1000);
}

function stopDashboardAutoRefresh() {
    if (dashboardRefreshInterval) {
        clearInterval(dashboardRefreshInterval);
    }
}

function refreshDashboardData() {
    var days = $('select[name="days"]').val() || 30;
    
    $.ajax({
        url: '/api/dashboard-data/',
        data: {
            'days': days
        },
        dataType: 'json',
        success: function(data) {
            updateKPICards(data);
        },
        error: function() {
            console.error('Failed to refresh dashboard data');
        }
    });
}

function updateKPICards(data) {
    // Update KPI cards with new data
    $('.kpi-total-stock-value').text('$' + data.total_stock_value.toFixed(2));
    $('.kpi-total-sales').text('$' + data.total_sales.toFixed(2));
    $('.kpi-total-purchases').text('$' + data.total_purchases.toFixed(2));
    $('.kpi-profit').text('$' + data.profit.toFixed(2));
    $('.kpi-low-stock-count').text(data.low_stock_count);
    
    // Update profit card color
    var profitCard = $('.kpi-profit').closest('.card');
    if (data.profit >= 0) {
        profitCard.removeClass('bg-danger').addClass('bg-success');
    } else {
        profitCard.removeClass('bg-success').addClass('bg-danger');
    }
}

// Initialize on page load
$(document).ready(function() {
    // Start auto-refresh if enabled
    if (typeof enableAutoRefresh !== 'undefined' && enableAutoRefresh) {
        startDashboardAutoRefresh(30);
    }
    
    // Refresh on period change
    $('select[name="days"]').on('change', function() {
        refreshDashboardData();
    });
});

