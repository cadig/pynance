/**
 * Main application logic for the Alpaca Trading Dashboard
 */

let selectedSymbol = null;

/**
 * Initialize the application
 */
async function init() {
    console.log('Initializing application...');
    try {
        // Load Alpaca credentials (you'll need to set these)
        console.log('Loading credentials...');
        await loadCredentials();
        
        // Load initial data
        try {
            console.log('Loading positions...');
            await loadPositions();
            console.log('Loading current orders for stop loss analysis...');
            await loadCurrentOrders();
            console.log('Rendering positions...');
            renderPositions();
        } catch (error) {
            console.error('Error loading positions:', error);
            showPositionsError();
        }
        
        try {
            console.log('Loading trades...');
            await loadHistoricalTrades();
            console.log('Rendering trades...');
            renderTrades();
        } catch (error) {
            console.error('Error loading trades:', error);
            showTradesError();
        }
        
        // Initialize chart
        console.log('Initializing chart...');
        initChart();
        console.log('Application initialized successfully');
        
    } catch (error) {
        console.error('Initialization error:', error);
        showError('Failed to initialize application');
    }
}

/**
 * Select a ticker and load its data
 */
async function selectTicker(symbol) {
    selectedSymbol = symbol;
    updateSelectedSymbol(symbol);
    
    // Clear previous overlays
    clearChartOverlays();
    
    // Update UI
    updateTickerSelection(event.target.closest('.ticker-item'));

    try {
        // Try to load chart data first
        try {
            await loadChartData(symbol);
        } catch (chartError) {
            console.warn('Chart data failed, continuing with orders:', chartError);
            updateSelectedSymbol(symbol, 'Chart data unavailable (check console for details)');
        }
        
        // Always try to load orders
        try {
            await loadOrdersForSymbol(symbol);
            await overlayOrdersOnChart(getCurrentOrders());
        } catch (orderError) {
            console.warn('Orders failed:', orderError);
            updateSelectedSymbol(symbol, 'Orders unavailable (check console for details)');
        }
    } catch (error) {
        console.error('Error loading ticker data:', error);
        showError(`Failed to load data for ${symbol}`);
    }
}

/**
 * Process and overlay orders on the chart
 */
async function overlayOrdersOnChart(orders) {
    try {
        // Clear previous overlays
        try {
            if (getStopLossSeries() && typeof getStopLossSeries().setData === 'function') {
                getStopLossSeries().setData([]);
            }
            if (getEntrySeries() && typeof getEntrySeries().setData === 'function') {
                getEntrySeries().setData([]);
            }
            if (getExitSeries() && typeof getExitSeries().setData === 'function') {
                getExitSeries().setData([]);
            }
        } catch (clearError) {
            console.warn('Error clearing previous overlays:', clearError);
        }
        
        // Process orders by type
        const entryOrders = [];
        const exitOrders = [];
        const stopLossOrders = [];
        
        orders.forEach(order => {
            const orderDate = new Date(order.created_at);
            const time = Math.floor(orderDate.getTime() / 1000);
            
            // Skip orders with invalid timestamps
            if (isNaN(time) || time <= 0) {
                console.warn('Skipping order with invalid timestamp:', order.created_at, 'parsed as:', time);
                return;
            }
            
            if (order.side === 'buy' && order.status === 'filled' && order.filled_avg_price) {
                const price = parseFloat(order.filled_avg_price);
                const qty = parseFloat(order.qty);
                
                if (!isNaN(price) && !isNaN(qty) && price > 0 && qty > 0) {
                    entryOrders.push({
                        time: time,
                        price: price,
                        qty: qty,
                        order: order
                    });
                } else {
                    console.warn('Skipping invalid entry order:', order);
                }
            } else if (order.side === 'sell' && order.status === 'filled' && order.filled_avg_price) {
                const price = parseFloat(order.filled_avg_price);
                const qty = parseFloat(order.qty);
                
                if (!isNaN(price) && !isNaN(qty) && price > 0 && qty > 0) {
                    exitOrders.push({
                        time: time,
                        price: price,
                        qty: qty,
                        order: order
                    });
                } else {
                    console.warn('Skipping invalid exit order:', order);
                }
            } else if (order.order_type === 'stop' && order.side === 'sell' && order.stop_price) {
                const price = parseFloat(order.stop_price);
                
                if (!isNaN(price) && price > 0) {
                    // Include all stop loss orders: new, accepted, filled, and cancelled
                    stopLossOrders.push({
                        time: time,
                        price: price,
                        status: order.status,
                        order: order
                    });
                } else {
                    console.warn('Skipping invalid stop loss order:', order);
                }
            }
        });
        
        // Add entry points as horizontal lines (positioned below price)
        if (entryOrders.length > 0) {
            console.log('Entry orders:', entryOrders);
            const entryData = [];
            entryOrders.forEach((entry, index) => {
                // Create a short horizontal line for each entry
                const lineStart = entry.time - 86400; // 1 day before
                const lineEnd = entry.time + 86400;   // 1 day after
                                        
                if (!isNaN(lineStart) && !isNaN(lineEnd) && !isNaN(entry.price)) {
                    entryData.push(
                        { time: lineStart, value: entry.price },
                        { time: lineEnd, value: entry.price }
                    );
                } else {
                    console.warn(`Skipping entry ${index} due to invalid values:`, {
                        lineStart,
                        lineEnd,
                        price: entry.price
                    });
                }
            });
            // Validate entry data before setting
            const validEntryData = entryData.filter(point => 
                point && 
                typeof point.time === 'number' && !isNaN(point.time) && point.time > 0 &&
                typeof point.value === 'number' && !isNaN(point.value) && point.value > 0
            );
            try {
                getEntrySeries().setData(validEntryData);
                console.log(`Entry markers: ${validEntryData.length} points`);
            } catch (entryError) {
                console.error('Error setting entry data:', entryError);
                console.log('Entry data that caused error:', validEntryData);
            }
        }
        
        // Add exit points as horizontal lines (positioned above price)
        if (exitOrders.length > 0) {
            console.log('Exit orders:', exitOrders);
            const exitData = [];
            exitOrders.forEach((exit, index) => {
                // Create a short horizontal line for each exit
                const lineStart = exit.time - 86400; // 1 day before
                const lineEnd = exit.time + 86400;   // 1 day after
                
                if (!isNaN(lineStart) && !isNaN(lineEnd) && !isNaN(exit.price)) {
                    exitData.push(
                        { time: lineStart, value: exit.price },
                        { time: lineEnd, value: exit.price }
                    );
                } else {
                    console.warn(`Skipping exit ${index} due to invalid values:`, {
                        lineStart,
                        lineEnd,
                        price: exit.price
                    });
                }
            });
            // Validate exit data before setting
            const validExitData = exitData.filter(point => 
                point && 
                typeof point.time === 'number' && !isNaN(point.time) && point.time > 0 &&
                typeof point.value === 'number' && !isNaN(point.value) && point.value > 0
            );
            try {
                getExitSeries().setData(validExitData);
            } catch (exitError) {
                console.error('Error setting exit data:', exitError);
                console.log('Exit data that caused error:', validExitData);
            }
        }
        
        // Add stop loss lines
        if (stopLossOrders.length > 0) {
            console.log('Stop loss orders found:', stopLossOrders.length);
            console.log('Stop loss orders:', stopLossOrders);
            await addStopLossLines(stopLossOrders);
        } else {
            console.log('No stop loss orders found');
        }
        
    } catch (error) {
        console.error('Error overlaying orders:', error);
    }
}

/**
 * Add stop loss horizontal lines
 */
async function addStopLossLines(stopLossOrders) {
    try {
        // Get the current chart data to determine the time range
        const chartData = getCandlestickSeries().data();
        if (!chartData || chartData.length === 0) {
            console.warn('No chart data available for stop loss lines');
            return;
        }
        
        const chartEndTime = chartData[chartData.length - 1].time;
        const allStopLossData = [];
        
        // Sort stop loss orders by time to handle overlapping periods correctly
        const sortedStopLosses = stopLossOrders.sort((a, b) => a.time - b.time);
        
        // Process each stop loss order
        sortedStopLosses.forEach((stopLoss, index) => {
            let endTime;

            if (stopLoss.status === 'canceled' || stopLoss.status === 'cancelled') {
                // Cancelled stop loss - line from creation to cancellation
                const canceledAt = stopLoss.order.canceled_at || stopLoss.order.updated_at;
                if (!canceledAt) {
                    console.warn('No cancellation timestamp found for order:', stopLoss.order);
                    return;
                }
                const canceledDate = new Date(canceledAt);
                endTime = Math.floor(canceledDate.getTime() / 1000);
                
                // Validate the timestamp
                if (isNaN(endTime) || endTime <= 0) {
                    console.warn('Invalid cancellation timestamp:', canceledAt, 'parsed as:', endTime);
                    return;
                }
            } else if (stopLoss.status === 'filled') {
                // Filled stop loss - line from creation to fill
                const filledAt = stopLoss.order.filled_at || stopLoss.order.updated_at;
                if (!filledAt) {
                    console.warn('No fill timestamp found for order:', stopLoss.order);
                    return;
                }
                const filledDate = new Date(filledAt);
                endTime = Math.floor(filledDate.getTime() / 1000);
                
                // Validate the timestamp
                if (isNaN(endTime) || endTime <= 0) {
                    console.warn('Invalid fill timestamp:', filledAt, 'parsed as:', endTime);
                    return;
                }
            } else if (stopLoss.status === 'new' || stopLoss.status === 'accepted') {
                // Active stop loss - line from creation to current time
                // Use current time if chart end time is earlier than stop loss time
                const currentTime = Math.floor(Date.now() / 1000);
                endTime = Math.max(chartEndTime, currentTime);
            } else {
                // Skip other statuses
                console.log(`Skipping stop loss with status: ${stopLoss.status}`);
                return;
            }
            
            // Create line from start to end (validate values first)
            if (!isNaN(stopLoss.time) && !isNaN(stopLoss.price) && !isNaN(endTime) && endTime >= stopLoss.time) {
                allStopLossData.push({
                    time: stopLoss.time,
                    value: stopLoss.price
                });
                allStopLossData.push({
                    time: endTime,
                    value: stopLoss.price
                });
            } else {
                console.warn('Skipping invalid stop loss data:', {
                    time: stopLoss.time,
                    price: stopLoss.price,
                    endTime: endTime,
                    order: stopLoss.order
                });
            }
        });
        
        // Set all stop loss data at once (with final validation)
        if (allStopLossData.length > 0) {
            // Final validation to ensure no null values
            const validStopLossData = allStopLossData.filter(point => 
                point && 
                typeof point.time === 'number' && !isNaN(point.time) && point.time > 0 &&
                typeof point.value === 'number' && !isNaN(point.value) && point.value > 0
            );
            
            if (validStopLossData.length > 0) {
                try {
                    console.log('About to set stop loss data:', validStopLossData);
                    
                    // Additional validation before setting data
                    const finalValidData = validStopLossData.filter(point => {
                        const isValid = point && 
                            typeof point.time === 'number' && !isNaN(point.time) && point.time > 0 &&
                            typeof point.value === 'number' && !isNaN(point.value) && point.value > 0;
                        
                        if (!isValid) {
                            console.error('Filtering out invalid stop loss point:', point);
                        }
                        return isValid;
                    });
                    
                    // Additional safety check - ensure all values are valid
                    const ultraValidData = finalValidData.map(point => ({
                        time: Math.floor(point.time),
                        value: parseFloat(point.value)
                    })).filter(point => 
                        !isNaN(point.time) && point.time > 0 &&
                        !isNaN(point.value) && point.value > 0
                    );
                    
                    // Deduplicate by timestamp - keep the last value for each timestamp
                    const deduplicatedData = [];
                    const timestampMap = new Map();
                    
                    ultraValidData.forEach(point => {
                        timestampMap.set(point.time, point.value);
                    });
                    
                    // Convert back to array, sorted by time
                    for (const [time, value] of timestampMap.entries()) {
                        deduplicatedData.push({ time, value });
                    }
                    
                    // Sort by time to ensure proper order
                    deduplicatedData.sort((a, b) => a.time - b.time);
                    
                    // Check if stopLossSeries is properly initialized
                    if (getStopLossSeries() && typeof getStopLossSeries().setData === 'function') {
                        getStopLossSeries().setData(deduplicatedData);
                        console.log(`Stop loss lines: ${deduplicatedData.length} points from ${sortedStopLosses.length} orders`);
                    } else {
                        console.error('stopLossSeries is not properly initialized');
                    }
                } catch (stopLossError) {
                    console.error('Error setting stop loss data:', stopLossError);
                    console.log('Stop loss data that caused error:', validStopLossData);
                    // Try to identify the problematic data point
                    validStopLossData.forEach((point, index) => {
                        console.log(`Data point ${index}:`, point);
                        if (point.time === null || point.value === null || isNaN(point.time) || isNaN(point.value)) {
                            console.error(`Problematic data point at index ${index}:`, point);
                        }
                    });
                }
            } else {
                console.log('No valid stop loss data to plot');
            }
        } else {
            console.log('No stop loss orders found');
        }
        
    } catch (error) {
        console.error('Error adding stop loss lines:', error);
    }
}

/**
 * Refresh all data
 */
async function refreshData() {
    updateSelectedSymbol('', 'Refreshing...');
    try {
        await loadPositions();
        await loadCurrentOrders();
        renderPositions();
    } catch (error) {
        showPositionsError();
    }
    
    try {
        await loadHistoricalTrades();
        renderTrades();
    } catch (error) {
        showTradesError();
    }
    
    if (selectedSymbol) {
        try {
            await loadChartData(selectedSymbol);
        } catch (error) {
            console.warn('Chart refresh failed:', error);
        }
        
        try {
            await loadOrdersForSymbol(selectedSymbol);
            await overlayOrdersOnChart(getCurrentOrders());
        } catch (error) {
            console.warn('Orders refresh failed:', error);
        }
    }
}

/**
 * Get selected symbol
 */
function getSelectedSymbol() {
    return selectedSymbol;
}
