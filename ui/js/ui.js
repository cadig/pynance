/**
 * UI rendering functions for the Alpaca Trading Dashboard
 */

/**
 * Clean symbol by removing emojis and warning text
 */
function cleanSymbol(symbol) {
    if (!symbol) return '';
    
    // Remove stop loss indicator (🛡️) and warning text
    let cleaned = symbol.replace(/🛡️/g, '').replace(/⚠️/g, '').replace(/NO STOP LOSS/g, '').trim();
    
    // Remove any extra whitespace
    cleaned = cleaned.replace(/\s+/g, ' ').trim();
    
    return cleaned;
}

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
            <div class="ticker-item ${warningClass}" onclick="selectTickerFromElement(this)" data-symbol="${position.symbol}" tabindex="0">
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
 * Toggle orders section (Open Orders)
 */
function toggleOrdersSection(sectionId) {
    const header = document.getElementById(`${sectionId}-header`);
    const content = document.getElementById(`${sectionId}-content`);
    const ordersSection = header ? header.closest('.orders-section') : null;
    
    if (!header || !content || !ordersSection) return;
    
    // Toggle collapsed state
    const isCollapsed = header.classList.contains('collapsed');
    
    if (isCollapsed) {
        // Expand
        header.classList.remove('collapsed');
        content.classList.remove('collapsed');
        ordersSection.classList.remove('collapsed');
    } else {
        // Collapse
        header.classList.add('collapsed');
        content.classList.add('collapsed');
        ordersSection.classList.add('collapsed');
    }
}

/**
 * Render open orders list
 */
function renderOpenOrders() {
    console.log('renderOpenOrders called');
    const container = document.getElementById('open-orders-list');
    const orders = getCurrentOrders();
    console.log('Orders data:', orders);
    
    // Check if orders data is loaded
    if (!orders || !Array.isArray(orders)) {
        console.log('Orders data not loaded yet:', orders);
        container.innerHTML = '<div class="loading">Loading orders...</div>';
        return;
    }
    
    // Filter for open buy orders (not filled)
    const openBuyOrders = orders.filter(order => 
        order.side === 'buy' && 
        (order.status === 'new' || order.status === 'accepted' || order.status === 'partially_filled')
    );
    
    console.log('Open buy orders found:', openBuyOrders.length, openBuyOrders);
    
    // Auto-collapse if no orders
    const header = document.getElementById('open-orders-header');
    const content = document.getElementById('open-orders-content');
    const ordersSection = header ? header.closest('.orders-section') : null;
    
    if (openBuyOrders.length === 0) {
        container.innerHTML = '<div class="loading">No open buy orders</div>';
        // Auto-collapse the section when there are no orders
        if (header && content && ordersSection) {
            header.classList.add('collapsed');
            content.classList.add('collapsed');
            ordersSection.classList.add('collapsed');
        }
        return;
    } else {
        // Auto-expand if there are orders
        if (header && content && ordersSection) {
            header.classList.remove('collapsed');
            content.classList.remove('collapsed');
            ordersSection.classList.remove('collapsed');
        }
    }

    container.innerHTML = openBuyOrders.map(order => {
        const orderDate = new Date(order.created_at);
        const statusClass = order.status.replace('_', '-');
        
        return `
            <div class="order-item" onclick="selectTickerFromElement(this)" data-symbol="${order.symbol}" tabindex="0">
                <div class="order-symbol">${order.symbol}</div>
                <div class="order-info">
                    Qty: ${order.qty} | 
                    Price: $${order.limit_price || 'Market'} | 
                    ${orderDate.toLocaleDateString()}
                    <span class="order-status ${statusClass}">${order.status.toUpperCase()}</span>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Render stop loss orders list
 */
function renderStopLossOrders() {
    console.log('renderStopLossOrders called');
    const container = document.getElementById('stop-loss-orders-list');
    const orders = getCurrentOrders();
    console.log('Orders data:', orders);
    
    // Check if orders data is loaded
    if (!orders || !Array.isArray(orders)) {
        console.log('Orders data not loaded yet:', orders);
        container.innerHTML = '<div class="loading">Loading orders...</div>';
        return;
    }
    
    // Filter for stop loss orders
    const stopLossOrders = orders.filter(order => 
        order.order_type === 'stop' && 
        order.side === 'sell' &&
        (order.status === 'new' || order.status === 'accepted' || order.status === 'partially_filled')
    );
    
    console.log('Stop loss orders found:', stopLossOrders.length, stopLossOrders);
    
    if (stopLossOrders.length === 0) {
        container.innerHTML = '<div class="loading">No stop loss orders</div>';
        return;
    }

    container.innerHTML = stopLossOrders.map(order => {
        const orderDate = new Date(order.created_at);
        const statusClass = order.status.replace('_', '-');
        
        return `
            <div class="order-item" onclick="selectTickerFromElement(this)" data-symbol="${order.symbol}" tabindex="0">
                <div class="order-symbol">${order.symbol}</div>
                <div class="order-info">
                    Qty: ${order.qty} | 
                    Stop: $${order.stop_price} | 
                    ${orderDate.toLocaleDateString()}
                    <span class="order-status ${statusClass}">${order.status.toUpperCase()}</span>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Calculate PnL for completed trades by matching buy and sell orders
 */
function calculateTradePnL(orders) {
    if (!orders || orders.length === 0) {
        return { pnl: 0, isCompleted: false, matchedTrades: [] };
    }
    
    // Separate buy and sell orders
    const buyOrders = orders.filter(order => order.side === 'buy' && order.status === 'filled');
    const sellOrders = orders.filter(order => order.side === 'sell' && order.status === 'filled');
    
    if (buyOrders.length === 0 || sellOrders.length === 0) {
        return { pnl: 0, isCompleted: false, matchedTrades: [] };
    }
    
    // Sort orders by creation time
    buyOrders.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    sellOrders.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    
    let totalPnL = 0;
    const matchedTrades = [];
    const usedBuyOrders = new Set();
    const usedSellOrders = new Set();
    
    // Try to match buy and sell orders with same quantity
    for (let i = 0; i < buyOrders.length; i++) {
        if (usedBuyOrders.has(i)) continue;
        
        const buyOrder = buyOrders[i];
        const buyQty = parseFloat(buyOrder.qty);
        const buyPrice = parseFloat(buyOrder.filled_avg_price);
        
        if (isNaN(buyQty) || isNaN(buyPrice) || buyQty <= 0 || buyPrice <= 0) continue;
        
        // Look for matching sell order with same quantity
        for (let j = 0; j < sellOrders.length; j++) {
            if (usedSellOrders.has(j)) continue;
            
            const sellOrder = sellOrders[j];
            const sellQty = parseFloat(sellOrder.qty);
            const sellPrice = parseFloat(sellOrder.filled_avg_price);
            
            if (isNaN(sellQty) || isNaN(sellPrice) || sellQty <= 0 || sellPrice <= 0) continue;
            
            // Check if quantities match (allowing for small floating point differences)
            if (Math.abs(buyQty - sellQty) < 0.01) {
                // Calculate PnL for this matched trade
                const tradePnL = (sellPrice - buyPrice) * buyQty;
                totalPnL += tradePnL;
                
                matchedTrades.push({
                    buyOrder,
                    sellOrder,
                    qty: buyQty,
                    buyPrice,
                    sellPrice,
                    pnl: tradePnL
                });
                
                // Mark these orders as used
                usedBuyOrders.add(i);
                usedSellOrders.add(j);
                break;
            }
        }
    }
    
    // Check if we have any completed trades
    const isCompleted = matchedTrades.length > 0;
    
    return {
        pnl: totalPnL,
        isCompleted,
        matchedTrades
    };
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

    container.innerHTML = historicalTrades.map(trade => {
        const tradeAnalysis = calculateTradePnL(trade.orders);
        const pnl = tradeAnalysis.pnl;
        const isCompleted = tradeAnalysis.isCompleted;
        
        // Determine styling based on PnL
        let itemClass = 'ticker-item';
        let pnlDisplay = '';
        
        if (isCompleted) {
            if (pnl > 0) {
                itemClass += ' trade-win';
                pnlDisplay = ` | PnL: <span class="pnl-value pnl-green">+$${pnl.toFixed(2)}</span>`;
            } else if (pnl < 0) {
                itemClass += ' trade-loss';
                pnlDisplay = ` | PnL: <span class="pnl-value pnl-red">$${pnl.toFixed(2)}</span>`;
            } else {
                pnlDisplay = ` | PnL: <span class="pnl-value pnl-neutral">$${pnl.toFixed(2)}</span>`;
            }
        }
        
        return `
            <div class="${itemClass}" onclick="selectTickerFromElement(this)" data-symbol="${trade.symbol}" tabindex="0">
                <div class="ticker-symbol">${trade.symbol}</div>
                <div class="ticker-info">
                    ${trade.orders.length} orders | 
                    Last: ${new Date(trade.orders[trade.orders.length - 1].created_at).toLocaleDateString()}${pnlDisplay}
                </div>
            </div>
        `;
    }).join('');
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
    // Update UI - handle both ticker items and order items
    document.querySelectorAll('.ticker-item, .order-item').forEach(item => {
        item.classList.remove('selected');
    });
    if (selectedElement) {
        selectedElement.classList.add('selected');
    }
}

/**
 * Get all selectable items in the current active tab
 */
function getCurrentSelectableItems() {
    const activePanel = document.querySelector('.tab-panel.active');
    if (!activePanel) return [];
    
    // Get all selectable items in the active panel
    return Array.from(activePanel.querySelectorAll('.ticker-item, .order-item'));
}

/**
 * Get the currently selected item index
 */
function getCurrentSelectedIndex() {
    const items = getCurrentSelectableItems();
    const selectedItem = document.querySelector('.ticker-item.selected, .order-item.selected');
    if (!selectedItem) return -1;
    
    return items.indexOf(selectedItem);
}

/**
 * Navigate to the next/previous item using keyboard
 */
function navigateItems(direction) {
    const items = getCurrentSelectableItems();
    if (items.length === 0) return;
    
    const currentIndex = getCurrentSelectedIndex();
    let newIndex;
    
    // If no item is currently selected, start with the first item
    if (currentIndex === -1) {
        newIndex = 0;
    } else if (direction === 'up') {
        newIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1;
    } else if (direction === 'down') {
        newIndex = currentIndex >= items.length - 1 ? 0 : currentIndex + 1;
    }
    
    if (newIndex >= 0 && newIndex < items.length) {
        const newItem = items[newIndex];
        
        // Extract symbol from the data attribute first
        const symbol = newItem.getAttribute('data-symbol');
        if (symbol) {
            // Focus the new item for keyboard navigation (blue border)
            newItem.focus();
            
            // Call selectTicker with the element to handle both chart loading and visual selection
            selectTicker(symbol, newItem);
            
            // Scroll the selected item into view
            newItem.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'nearest' 
            });
        }
    }
}

/**
 * Handle keyboard navigation
 */
function handleKeyboardNavigation(event) {
    // Only handle arrow keys when no input is focused
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
    }
    
    if (event.key === 'ArrowUp') {
        event.preventDefault();
        navigateItems('up');
    } else if (event.key === 'ArrowDown') {
        event.preventDefault();
        navigateItems('down');
    }
}

/**
 * Select ticker from element using data attribute
 */
function selectTickerFromElement(element) {
    const symbol = element.getAttribute('data-symbol');
    if (symbol) {
        // Focus the element for consistency (blue border)
        element.focus();
        
        // Call selectTicker with the element to handle both chart loading and visual selection
        selectTicker(symbol, element);
    }
}

// Make functions globally available
window.handleKeyboardNavigation = handleKeyboardNavigation;
window.cleanSymbol = cleanSymbol;
window.selectTickerFromElement = selectTickerFromElement;
window.toggleOrdersSection = toggleOrdersSection;

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
 * Show loading state for orders
 */
function showOrdersLoading() {
    document.getElementById('open-orders-list').innerHTML = '<div class="loading">Loading open orders...</div>';
    document.getElementById('stop-loss-orders-list').innerHTML = '<div class="loading">Loading stop loss orders...</div>';
}

/**
 * Show error state for orders
 */
function showOrdersError() {
    document.getElementById('open-orders-list').innerHTML = '<div class="error">Failed to load orders</div>';
    document.getElementById('stop-loss-orders-list').innerHTML = '<div class="error">Failed to load orders</div>';
}

/**
 * Switch between tabs
 */
function switchTab(tabName) {
    // Remove active class from all tab headers
    document.querySelectorAll('.tab-header').forEach(header => {
        header.classList.remove('active');
    });
    
    // Remove active class from all tab panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    
    // Add active class to selected tab header
    const selectedHeader = document.getElementById(`${tabName}-tab`);
    if (selectedHeader) {
        selectedHeader.classList.add('active');
    }
    
    // Add active class to selected tab panel
    const selectedPanel = document.getElementById(`${tabName}-panel`);
    if (selectedPanel) {
        selectedPanel.classList.add('active');
    }
}

// Make switchTab globally available
window.switchTab = switchTab;

/**
 * Toggle collapsible section (for Portfolio Metrics)
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

// ============================================================================
// THEME MANAGEMENT
// ============================================================================

/**
 * Initialize theme system
 */
function initializeTheme() {
    // Check for saved theme preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        setTheme(savedTheme);
    } else {
        // Auto-detect system theme
        setTheme('auto');
    }
    
    // Listen for system theme changes
    if (window.matchMedia) {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', handleSystemThemeChange);
    }
}

/**
 * Set the current theme
 * @param {string} theme - 'auto', 'light', or 'dark'
 */
function setTheme(theme) {
    const root = document.documentElement;
    
    // Remove existing theme classes
    root.removeAttribute('data-theme');
    
    if (theme === 'auto') {
        // Use system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            root.setAttribute('data-theme', 'dark');
        }
        // If light mode or no preference, don't set data-theme (uses light by default)
    } else if (theme === 'dark') {
        root.setAttribute('data-theme', 'dark');
    }
    // For light mode, don't set data-theme (uses light by default)
    
    // Save preference
    localStorage.setItem('theme', theme);
    
    // Update theme toggle button if it exists
    updateThemeToggleButton(theme);
}

/**
 * Get the current effective theme (resolves 'auto' to actual theme)
 */
function getCurrentTheme() {
    const savedTheme = localStorage.getItem('theme') || 'auto';
    
    if (savedTheme === 'auto') {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }
    
    return savedTheme;
}

/**
 * Toggle between light and dark themes
 */
function toggleTheme() {
    const current = getCurrentTheme();
    const newTheme = current === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
}

/**
 * Handle system theme changes when in 'auto' mode
 */
function handleSystemThemeChange(e) {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'auto') {
        setTheme('auto');
    }
}

/**
 * Update theme toggle button appearance
 */
function updateThemeToggleButton(theme) {
    const button = document.getElementById('theme-toggle');
    if (button) {
        const icon = button.querySelector('.theme-icon');
        if (icon) {
            if (theme === 'auto') {
                icon.textContent = '🌓';
                icon.title = 'Auto (System)';
            } else if (theme === 'dark') {
                icon.textContent = '🌙';
                icon.title = 'Dark Mode';
            } else {
                icon.textContent = '☀️';
                icon.title = 'Light Mode';
            }
        }
    }
}

/**
 * Create theme toggle button
 */
function createThemeToggle() {
    const currentTheme = getCurrentTheme();
    const icon = currentTheme === 'dark' ? '🌙' : currentTheme === 'light' ? '☀️' : '🌓';
    const title = currentTheme === 'dark' ? 'Dark Mode' : currentTheme === 'light' ? 'Light Mode' : 'Auto (System)';
    
    return `
        <button id="theme-toggle" onclick="toggleTheme()" class="theme-toggle-btn" title="${title}">
            <span class="theme-icon">${icon}</span>
        </button>
    `;
}
