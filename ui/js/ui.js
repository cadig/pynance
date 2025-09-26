/**
 * UI rendering functions for the Alpaca Trading Dashboard
 */

/**
 * Render positions list
 */
function renderPositions() {
    console.log('renderPositions called');
    const container = document.getElementById('positions-list');
    const positions = getPositions();
    console.log('Positions data:', positions);
    
    // Apply P&L sorting if available
    const sortedPositions = typeof sortPositionsByPnl === 'function' ? sortPositionsByPnl(positions) : positions;
    
    if (sortedPositions.length === 0) {
        container.innerHTML = '<div class="loading">No current positions</div>';
        return;
    }

    container.innerHTML = sortedPositions.map(position => {
        const hasStopLoss = hasStopLossOrder(position.symbol);
        const warningClass = hasStopLoss ? '' : 'no-stop-loss';
        const stopLossIndicator = hasStopLoss ? '🛡️' : '⚠️';
        
        const pnl = parseFloat(position.unrealized_pl);
        const pnlColor = pnl > 0 ? 'green' : pnl < 0 ? 'red' : 'neutral';
        const pnlSign = pnl > 0 ? '+' : '';
        
        // Calculate P/L percentage
        const avgEntryPrice = parseFloat(position.avg_entry_price);
        const currentPrice = parseFloat(position.current_price);
        const pnlPercentage = avgEntryPrice > 0 ? ((currentPrice - avgEntryPrice) / avgEntryPrice) * 100 : 0;
        const pnlPercentageSign = pnlPercentage > 0 ? '+' : '';
        const pnlPercentageColor = pnlPercentage > 0 ? 'green' : pnlPercentage < 0 ? 'red' : 'neutral';
        
        return `
            <div class="ticker-item ${warningClass}" onclick="selectTicker('${position.symbol}')">
                <div class="ticker-symbol">
                    ${position.symbol} ${stopLossIndicator} ${!hasStopLoss ? '<span>NO STOP LOSS</span>' : ''}
                </div>
                <div class="ticker-info">
                    Qty: ${position.qty} | 
                    Avg Price: $${avgEntryPrice.toFixed(2)} | 
                    P&L: <span class="pnl-value pnl-${pnlColor}">${pnlSign}$${pnl.toFixed(2)}</span> | 
                    P&L%: <span class="pnl-value pnl-${pnlPercentageColor}">${pnlPercentageSign}${pnlPercentage.toFixed(2)}%</span>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Render trades list
 */
function renderTrades() {
    console.log('renderTrades called');
    const container = document.getElementById('trades-list');
    const historicalTrades = getHistoricalTrades();
    console.log('Trades data:', historicalTrades);
    
    if (historicalTrades.length === 0) {
        container.innerHTML = '<div class="loading">No historical trades</div>';
        return;
    }

    container.innerHTML = historicalTrades.map(trade => `
        <div class="ticker-item" onclick="selectTicker('${trade.symbol}')">
            <div class="ticker-symbol">${trade.symbol}</div>
            <div class="ticker-info">
                ${trade.orders.length} orders | 
                Last: ${new Date(trade.orders[trade.orders.length - 1].created_at).toLocaleDateString()}
            </div>
        </div>
    `).join('');
}

/**
 * Show error message
 */
function showError(message) {
    console.error(message);
    // You could add a toast notification here
}

/**
 * Update selected symbol display
 */
function updateSelectedSymbol(symbol, status = '') {
    const element = document.getElementById('selected-symbol');
    if (status) {
        element.textContent = `${symbol} - ${status}`;
    } else {
        element.textContent = `Loading ${symbol}...`;
    }
}

/**
 * Update ticker selection in UI
 */
function updateTickerSelection(selectedElement) {
    // Update UI
    document.querySelectorAll('.ticker-item').forEach(item => {
        item.classList.remove('selected');
    });
    selectedElement.classList.add('selected');
}

/**
 * Show loading state for positions
 */
function showPositionsLoading() {
    document.getElementById('positions-list').innerHTML = '<div class="loading">Loading positions...</div>';
}

/**
 * Show error state for positions
 */
function showPositionsError() {
    document.getElementById('positions-list').innerHTML = '<div class="error">Failed to load positions</div>';
}

/**
 * Show loading state for trades
 */
function showTradesLoading() {
    document.getElementById('trades-list').innerHTML = '<div class="loading">Loading trades...</div>';
}

/**
 * Show error state for trades
 */
function showTradesError() {
    document.getElementById('trades-list').innerHTML = '<div class="error">Failed to load trades</div>';
}

/**
 * Toggle collapsible section
 */
function toggleSection(sectionId) {
    const section = document.querySelector(`.${sectionId}`);
    if (!section) return;
    
    const header = section.querySelector('.collapsible-header');
    const content = section.querySelector('.section-content');
    
    if (!header || !content) return;
    
    // Toggle collapsed state
    const isCollapsed = header.classList.contains('collapsed');
    
    if (isCollapsed) {
        // Expand
        header.classList.remove('collapsed');
        content.classList.remove('collapsed');
    } else {
        // Collapse
        header.classList.add('collapsed');
        content.classList.add('collapsed');
    }
}

// Make toggleSection globally available
window.toggleSection = toggleSection;

/**
 * Update Portfolio Metrics with current data
 */
function updatePortfolioMetrics() {
    const positions = getPositions();
    
    // Calculate total open P&L
    const totalPnL = positions.reduce((sum, position) => {
        return sum + (parseFloat(position.unrealized_pl) || 0);
    }, 0);
    
    // Calculate total risk to stop using real stop loss data
    let totalRisk = 0;
    let positionsWithoutStopLoss = 0;
    
    positions.forEach(position => {
        const currentPrice = parseFloat(position.current_price) || 0;
        const qty = parseFloat(position.qty) || 0;
        
        if (currentPrice > 0 && qty > 0) {
            // Check if position has a stop loss order
            const stopLossOrder = getCurrentOrders().find(order => 
                order.symbol === position.symbol && 
                order.order_type === 'stop' && 
                order.side === 'sell' && 
                (order.status === 'new' || order.status === 'accepted' || order.status === 'partially_filled')
            );
            
            if (stopLossOrder && stopLossOrder.stop_price) {
                const stopPrice = parseFloat(stopLossOrder.stop_price);
                const riskPerShare = Math.abs(currentPrice - stopPrice);
                const totalPositionRisk = riskPerShare * Math.abs(qty);
                totalRisk += totalPositionRisk;
            } else {
                // Position has no stop loss
                positionsWithoutStopLoss++;
            }
        }
    });
    
    // Count positions
    const positionCount = positions.length;
    
    // Calculate percentage P&L (mock calculation)
    const totalValue = positions.reduce((sum, position) => {
        return sum + (parseFloat(position.qty) * parseFloat(position.avg_entry_price));
    }, 0);
    const pnlPercentage = totalValue > 0 ? (totalPnL / totalValue) * 100 : 0;
    
    // Calculate capital usage using real account equity
    const totalCapital = getAccountEquity();
    const capitalUsage = totalCapital > 0 ? (totalValue / totalCapital) * 100 : 0;
    const capitalUsageAmount = totalValue;
    
    // Handle case where account data is not available
    const capitalUsageDisplay = totalCapital > 0 ? capitalUsage.toFixed(1) : 'N/A';
    const capitalUsageAmountDisplay = totalCapital > 0 ? `$${capitalUsageAmount.toFixed(0)}` : 'N/A';
    
    // Total equity is now included in the metrics container update below
    
    // Log account data for debugging
    console.log('Account equity:', totalCapital);
    console.log('Total position value:', totalValue);
    console.log('Capital usage:', capitalUsage.toFixed(1) + '%');
    console.log('Total risk to stop:', totalRisk);
    console.log('Positions without stop loss:', positionsWithoutStopLoss);
    
    // Update the metrics display
    const metricsContainer = document.querySelector('.portfolio-metrics .section-content');
    if (metricsContainer) {
        const formattedEquity = totalCapital > 0 ? 
            `$${totalCapital.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 
            'Loading...';
            
        metricsContainer.innerHTML = `
            <div class="account-equity">
                <span class="equity-label">Total Equity:</span>
                <span class="equity-value" id="total-equity">${formattedEquity}</span>
            </div>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-label">Total Open P&L</div>
                    <div class="metric-value ${pnlPercentage >= 0 ? 'positive' : 'negative'}">
                        ${pnlPercentage >= 0 ? '+' : ''}${pnlPercentage.toFixed(1)}%
                    </div>
                    <div class="metric-percentage ${totalPnL >= 0 ? 'pnl-positive' : 'pnl-negative'}">
                        ${totalPnL >= 0 ? '+' : ''}$${totalPnL.toFixed(2)}
                    </div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Risk to Stop ${positionsWithoutStopLoss > 0 ? '⚠️' : ''}</div>
                    <div class="metric-value ${totalCapital > 0 ? ((totalRisk / totalCapital) * 100) < 1 ? 'risk-low' : ((totalRisk / totalCapital) * 100) < 2 ? 'risk-medium' : 'risk-high' : 'risk-low'}" ${positionsWithoutStopLoss > 0 ? 'title="Some positions do not have a stop loss"' : ''}>
                        ${totalCapital > 0 ? ((totalRisk / totalCapital) * 100).toFixed(1) : '0.0'}%
                    </div>
                    <div class="metric-percentage">
                        $${totalRisk.toFixed(0)}
                    </div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Capital Usage</div>
                    <div class="metric-value ${totalCapital > 0 ? (capitalUsage < 50 ? 'capital-low' : capitalUsage < 80 ? 'capital-medium' : 'capital-high') : 'capital-medium'}">
                        ${capitalUsageDisplay}%
                    </div>
                    <div class="metric-percentage">
                        ${capitalUsageAmountDisplay}
                    </div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Positions</div>
                    <div class="metric-value positions-count">${positionCount}</div>
                    <div class="metric-subtitle">Active</div>
                </div>
            </div>
        `;
    }
}
