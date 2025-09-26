/**
 * Chart management functions for the Alpaca Trading Dashboard
 */

let chart = null;
let candlestickSeries = null;
let stopLossSeries = null;
let entrySeries = null;
let exitSeries = null;

/**
 * Initialize TradingView chart
 */
function initChart() {
    const chartContainer = document.getElementById('chart');
    chart = LightweightCharts.createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: 500,
        layout: {
            backgroundColor: '#ffffff',
            textColor: '#333',
        },
        grid: {
            vertLines: {
                color: '#f0f0f0',
            },
            horzLines: {
                color: '#f0f0f0',
            },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: '#cccccc',
        },
        timeScale: {
            borderColor: '#cccccc',
        },
    });

    candlestickSeries = chart.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
    });

    // Add horizontal line series for stop losses
    stopLossSeries = chart.addLineSeries({
        color: '#ef4444',
        lineWidth: 2,
        lineStyle: 2, // Dashed line
        title: 'Stop Loss'
    });

    // Add series for entry points (below price)
    entrySeries = chart.addLineSeries({
        color: '#10b981',
        lineWidth: 3,
        lineStyle: 0, // Solid line
        title: 'Entry Points'
    });

    // Add series for exit points (above price)
    exitSeries = chart.addLineSeries({
        color: '#f59e0b',
        lineWidth: 3,
        lineStyle: 0, // Solid line
        title: 'Exit Points'
    });
}

/**
 * Load chart data for a symbol
 */
async function loadChartData(symbol) {
    try {
        // Use historical data only (avoid recent data requirements)
        const start = new Date();
        start.setDate(start.getDate() - 120); // 200 days ago to ensure historical data

        // Format date for Alpaca API
        const startStr = start.toISOString().split('T')[0];

        // Use the data API endpoint for historical bars (no end date)
        const dataApiUrl = 'https://data.alpaca.markets';
        const response = await fetch(
            `${dataApiUrl}/v2/stocks/${symbol}/bars?` +
            `start=${startStr}&` +
            `timeframe=1Day&` +
            `limit=200`,
            {
                headers: {
                    'APCA-API-KEY-ID': ALPACA_CONFIG.apiKey,
                    'APCA-API-SECRET-KEY': ALPACA_CONFIG.secretKey
                }
            }
        );

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Chart data API error:', response.status, errorText);
            throw new Error(`Failed to load chart data: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Chart data response:', data);
        const bars = data.bars || [];
        
        // Convert to chart format with comprehensive validation
        const chartData = bars.map(bar => {
            // Validate that all required values are present and not null/undefined
            if (!bar.t || 
                bar.o === null || bar.o === undefined || 
                bar.h === null || bar.h === undefined || 
                bar.l === null || bar.l === undefined || 
                bar.c === null || bar.c === undefined) {
                console.warn('Skipping invalid bar data:', bar);
                return null;
            }
            
            // Parse values and validate they're valid numbers
            const open = parseFloat(bar.o);
            const high = parseFloat(bar.h);
            const low = parseFloat(bar.l);
            const close = parseFloat(bar.c);
            const time = Math.floor(new Date(bar.t).getTime() / 1000);
            
            // Validate parsed values
            if (isNaN(open) || isNaN(high) || isNaN(low) || isNaN(close) || isNaN(time) || 
                open <= 0 || high <= 0 || low <= 0 || close <= 0 || time <= 0) {
                console.warn('Skipping bar with invalid numeric values:', bar);
                return null;
            }
            
            return {
                time: time,
                open: open,
                high: high,
                low: low,
                close: close
            };
        }).filter(bar => bar !== null); // Remove any null entries

        // Final safety check before setting chart data
        if (chartData.length > 0) {
            try {
                // Ensure no null values in the final data structure
                const safeChartData = chartData.map(bar => ({
                    time: bar.time,
                    open: bar.open,
                    high: bar.high,
                    low: bar.low,
                    close: bar.close
                }));
                
                console.log(`Chart loaded: ${safeChartData.length} bars for ${symbol}`);
                
                // Check for any null values in chart data (only log if found)
                const hasNullValues = safeChartData.some(bar => 
                    bar.time === null || bar.open === null || bar.high === null || 
                    bar.low === null || bar.close === null ||
                    isNaN(bar.time) || isNaN(bar.open) || isNaN(bar.high) || 
                    isNaN(bar.low) || isNaN(bar.close)
                );
                
                if (hasNullValues) {
                    console.error('Chart data contains null or NaN values!');
                    safeChartData.forEach((bar, index) => {
                        if (bar.time === null || bar.open === null || bar.high === null || 
                            bar.low === null || bar.close === null ||
                            isNaN(bar.time) || isNaN(bar.open) || isNaN(bar.high) || 
                            isNaN(bar.low) || isNaN(bar.close)) {
                            console.error(`Problematic chart bar at index ${index}:`, bar);
                        }
                    });
                }
                
                candlestickSeries.setData(safeChartData);
                document.getElementById('selected-symbol').textContent = `${symbol} - ${safeChartData.length} bars`;
            } catch (chartError) {
                console.error('Error setting chart data:', chartError);
                document.getElementById('selected-symbol').textContent = `${symbol} - Chart error`;
            }
        } else {
            console.warn('No valid chart data to display');
            document.getElementById('selected-symbol').textContent = `${symbol} - No chart data`;
        }
        
    } catch (error) {
        console.error('Error loading chart data:', error);
        throw error;
    }
}

/**
 * Clear all chart overlays
 */
function clearChartOverlays() {
    if (candlestickSeries) {
        candlestickSeries.setMarkers([]);
    }
    if (stopLossSeries) {
        stopLossSeries.setData([]);
    }
    if (entrySeries) {
        entrySeries.setData([]);
    }
    if (exitSeries) {
        exitSeries.setData([]);
    }
}

/**
 * Get chart instance
 */
function getChart() {
    return chart;
}

/**
 * Get candlestick series
 */
function getCandlestickSeries() {
    return candlestickSeries;
}

/**
 * Get stop loss series
 */
function getStopLossSeries() {
    return stopLossSeries;
}

/**
 * Get entry series
 */
function getEntrySeries() {
    return entrySeries;
}

/**
 * Get exit series
 */
function getExitSeries() {
    return exitSeries;
}
