/**
 * Chart management functions for the Alpaca Trading Dashboard
 */

let chart = null;
let volumeChart = null;
let candlestickSeries = null;
let stopLossSeries = null;
let entrySeries = null;
let exitSeries = null;
let volumeSeries = null;
let sma10Series = null;
let sma50Series = null;
let chartsSynchronized = false;

/**
 * Initialize TradingView chart
 */
function initChart() {
    const chartContainer = document.getElementById('chart');
    const volumeContainer = document.getElementById('volume-chart');
    
    // Create main price chart
    chart = LightweightCharts.createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: 400,
        layout: {
            backgroundColor: '#ffffff',
            textColor: '#333',
            attributionLogo: false,
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
        leftPriceScale: {
            borderColor: '#cccccc',
            visible: true,
            scaleMargins: {
                top: 0.1,
                bottom: 0.1,
            },
        },
        rightPriceScale: {
            borderColor: '#cccccc',
            visible: true,
            scaleMargins: {
                top: 0.1,
                bottom: 0.1,
            },
        },
        timeScale: {
            borderColor: '#cccccc',
        },
    });

    candlestickSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
        priceScaleId: 'left',
    });

    // Add horizontal line series for stop losses
    stopLossSeries = chart.addSeries(LightweightCharts.LineSeries, {
        color: '#ef4444',
        lineWidth: 2,
        lineStyle: 2, // Dashed line
        title: 'Stop Loss',
        priceScaleId: 'left'
    });

    // Add series for entry points (below price)
    entrySeries = chart.addSeries(LightweightCharts.LineSeries, {
        color: '#10b981',
        lineWidth: 3,
        lineStyle: 0, // Solid line
        title: 'Entry Points',
        priceScaleId: 'left'
    });

    // Add series for exit points (above price)
    exitSeries = chart.addSeries(LightweightCharts.LineSeries, {
        color: '#f59e0b',
        lineWidth: 3,
        lineStyle: 0, // Solid line
        title: 'Exit Points',
        priceScaleId: 'left'
    });

    // Create separate volume chart
    volumeChart = LightweightCharts.createChart(volumeContainer, {
        width: volumeContainer.clientWidth,
        height: 120,
        layout: {
            backgroundColor: '#f8fafc',
            textColor: '#333',
            attributionLogo: false,
        },
        grid: {
            vertLines: {
                color: '#e2e8f0',
            },
            horzLines: {
                color: '#e2e8f0',
            },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        leftPriceScale: {
            borderColor: '#e2e8f0',
            visible: true,
            scaleMargins: {
                top: 0.1,
                bottom: 0.1,
            },
        },
        rightPriceScale: {
            visible: false,
        },
        timeScale: {
            borderColor: '#e2e8f0',
            timeVisible: true,
            secondsVisible: false,
        },
    });

    // Add volume series to separate chart
    volumeSeries = volumeChart.addSeries(LightweightCharts.HistogramSeries, {
        color: '#26a69a',
        priceFormat: {
            type: 'volume',
        },
        title: 'Volume',
        priceScaleId: 'left'
    });

    // Synchronization will be set up after data is loaded

    // Add 10-day Simple Moving Average
    sma10Series = chart.addSeries(LightweightCharts.LineSeries, {
        color: '#ff6b6b',
        lineWidth: 2,
        lineStyle: 0, // Solid line
        priceScaleId: 'left',
        title: '' // Hide from legend
    });

    // Add 50-day Simple Moving Average
    sma50Series = chart.addSeries(LightweightCharts.LineSeries, {
        color: '#4ecdc4',
        lineWidth: 2,
        lineStyle: 0, // Solid line
        priceScaleId: 'left',
        title: '' // Hide from legend
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
                close: close,
                volume: parseFloat(bar.v) || 0
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
                
                // Prepare volume data
                const volumeData = chartData.map(bar => ({
                    time: bar.time,
                    value: bar.volume,
                    color: bar.close >= bar.open ? '#26a69a' : '#ef5350' // Green for up, red for down
                }));
                
                // Calculate moving averages
                const sma10Data = calculateSMA(chartData, 10);
                const sma50Data = calculateSMA(chartData, 50);
                
                // Set volume data on separate chart
                volumeSeries.setData(volumeData);
                
                // Set moving average data
                sma10Series.setData(sma10Data);
                sma50Series.setData(sma50Data);
                
                // Set up synchronization after data is loaded (only once)
                if (!chartsSynchronized) {
                    setTimeout(() => {
                        synchronizeCharts();
                        chartsSynchronized = true;
                    }, 200);
                }
                
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
    // Note: In v5.0, markers are handled through plugins, not directly on series
    if (stopLossSeries) {
        stopLossSeries.setData([]);
    }
    if (entrySeries) {
        entrySeries.setData([]);
    }
    if (exitSeries) {
        exitSeries.setData([]);
    }
    if (volumeSeries && volumeChart) {
        volumeSeries.setData([]);
    }
    if (sma10Series) {
        sma10Series.setData([]);
    }
    if (sma50Series) {
        sma50Series.setData([]);
    }
}

/**
 * Get chart instance
 */
function getChart() {
    return chart;
}

/**
 * Get volume chart instance
 */
function getVolumeChart() {
    return volumeChart;
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

/**
 * Calculate Simple Moving Average
 */
function calculateSMA(data, period) {
    const smaData = [];
    
    for (let i = period - 1; i < data.length; i++) {
        let sum = 0;
        for (let j = 0; j < period; j++) {
            sum += data[i - j].close;
        }
        const average = sum / period;
        smaData.push({
            time: data[i].time,
            value: average
        });
    }
    
    return smaData;
}

/**
 * Get volume series
 */
function getVolumeSeries() {
    return volumeSeries;
}

/**
 * Get SMA 10 series
 */
function getSMA10Series() {
    return sma10Series;
}

/**
 * Get SMA 50 series
 */
function getSMA50Series() {
    return sma50Series;
}

/**
 * Synchronize charts for scrolling, zooming, and crosshair movement
 */
function synchronizeCharts() {
    if (!chart || !volumeChart) return;
    
    // Check if volume chart has data before setting up synchronization
    if (!volumeSeries || !volumeChart.timeScale()) {
        console.warn('Volume chart not ready for synchronization');
        return;
    }

    let isPriceChartScrolling = false;
    let isVolumeChartScrolling = false;

    // Synchronize time scale changes (scrolling/zooming)
    chart.timeScale().subscribeVisibleTimeRangeChange((timeRange) => {
        if (isPriceChartScrolling || !timeRange || !timeRange.from || !timeRange.to) return;
        
        isVolumeChartScrolling = true;
        try {
            volumeChart.timeScale().setVisibleRange(timeRange);
        } catch (error) {
            console.warn('Volume chart time range sync failed:', error);
        }
        setTimeout(() => {
            isVolumeChartScrolling = false;
        }, 10);
    });

    volumeChart.timeScale().subscribeVisibleTimeRangeChange((timeRange) => {
        if (isVolumeChartScrolling || !timeRange || !timeRange.from || !timeRange.to) return;
        
        isPriceChartScrolling = true;
        try {
            chart.timeScale().setVisibleRange(timeRange);
        } catch (error) {
            console.warn('Price chart time range sync failed:', error);
        }
        setTimeout(() => {
            isPriceChartScrolling = false;
        }, 10);
    });

    // Synchronize crosshair movement
    chart.subscribeCrosshairMove((param) => {
        try {
            if (param.point) {
                volumeChart.setCrosshairPosition(param.point.x, param.point.y, param.seriesData);
            } else {
                volumeChart.clearCrosshairPosition();
            }
        } catch (error) {
            console.warn('Volume chart crosshair sync failed:', error);
        }
    });

    volumeChart.subscribeCrosshairMove((param) => {
        try {
            if (param.point) {
                chart.setCrosshairPosition(param.point.x, param.point.y, param.seriesData);
            } else {
                chart.clearCrosshairPosition();
            }
        } catch (error) {
            console.warn('Price chart crosshair sync failed:', error);
        }
    });

    // Synchronize clicks
    chart.subscribeClick((param) => {
        try {
            if (param.point) {
                volumeChart.setCrosshairPosition(param.point.x, param.point.y, param.seriesData);
            }
        } catch (error) {
            console.warn('Volume chart click sync failed:', error);
        }
    });

    volumeChart.subscribeClick((param) => {
        try {
            if (param.point) {
                chart.setCrosshairPosition(param.point.x, param.point.y, param.seriesData);
            }
        } catch (error) {
            console.warn('Price chart click sync failed:', error);
        }
    });
}
