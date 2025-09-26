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
        
        return `
            <div class="ticker-item ${warningClass}" onclick="selectTicker('${position.symbol}')">
                <div class="ticker-symbol">
                    ${position.symbol} ${stopLossIndicator}
                </div>
                <div class="ticker-info">
                    Qty: ${position.qty} | 
                    Avg Price: $${parseFloat(position.avg_entry_price).toFixed(2)} | 
                    P&L: <span class="pnl-value pnl-${pnlColor}">${pnlSign}$${pnl.toFixed(2)}</span>
                    ${!hasStopLoss ? '<br><strong>⚠️ NO STOP LOSS</strong>' : ''}
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
