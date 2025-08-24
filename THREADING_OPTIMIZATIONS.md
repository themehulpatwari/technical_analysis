# Threading Optimizations

## Overview
This technical analysis application has been optimized with threading to improve performance when processing multiple stocks concurrently. The optimizations are designed to be cloud-server friendly with conservative thread counts.

## Threading Configuration

The application uses different thread pools for different types of operations:

### 1. Stock Filtering Threads (`MAX_FILTER_THREADS: 6`)
- Used for concurrent stock info fetching during filtering phase
- Handles I/O intensive operations (API calls to get market cap, volume data)
- Conservative count to avoid overwhelming external APIs

### 2. Data Fetching Threads (`MAX_FETCH_THREADS: 5`)
- Used for concurrent stock data fetching from Yahoo Finance
- Handles downloading historical price data
- Limited to avoid rate limiting issues

### 3. Analysis Threads (`MAX_ANALYSIS_THREADS: 4`)
- Used for concurrent technical analysis (RSI, MACD calculations)
- CPU-intensive operations using TA-Lib
- Lower count as these are compute-heavy operations

## Key Optimizations

### 1. Concurrent Stock Filtering
- **Before**: Sequential processing of each stock's market cap and volume data
- **After**: Parallel processing using ThreadPoolExecutor
- **Benefit**: Significant speedup when filtering large lists of stocks

### 2. Concurrent Data Fetching  
- **Before**: Sequential download of stock data
- **After**: Parallel download using ThreadPoolExecutor
- **Benefit**: Major reduction in I/O wait time

### 3. Concurrent Stock Analysis
- **Before**: Sequential RSI and MACD calculation for each stock
- **After**: Parallel analysis of multiple stocks
- **Benefit**: Better CPU utilization for technical indicator calculations

### 4. Concurrent Email Preparation
- **Before**: Sequential CSV creation and email body generation
- **After**: Parallel preparation using ThreadPoolExecutor
- **Benefit**: Faster email report generation

## Cloud Server Considerations

The thread counts are deliberately conservative to ensure:

1. **Memory Usage**: Limited threads prevent excessive memory consumption
2. **API Rate Limits**: Controlled concurrent requests to avoid being blocked
3. **CPU Load**: Balanced threading to prevent overwhelming cloud servers
4. **Network Bandwidth**: Controlled concurrent downloads

## Performance Monitoring

The application includes performance monitoring:

- **Function-level timing**: Using `@performance_monitor` decorator
- **Memory usage tracking**: Optional psutil integration
- **Throughput metrics**: Stocks processed per second
- **Success rates**: Analysis and signal detection rates

## Configuration

You can adjust thread counts in `src/config.py`:

```python
# Threading configuration
MAX_ANALYSIS_THREADS: int = 4    # CPU intensive operations
MAX_FETCH_THREADS: int = 5       # I/O intensive data fetching  
MAX_FILTER_THREADS: int = 6      # I/O intensive filtering
```

## Testing

Run the threading test to verify optimizations:

```bash
python test_threading.py
```

## Best Practices

1. **Monitor resource usage**: Keep an eye on CPU and memory consumption
2. **Respect rate limits**: Don't increase thread counts too much for external APIs
3. **Error handling**: Individual thread failures don't crash the entire process
4. **Graceful degradation**: Application continues even if some threads fail

## Expected Performance Improvements

- **Stock filtering**: 3-5x faster with concurrent API calls
- **Data fetching**: 4-6x faster with parallel downloads
- **Analysis**: 2-3x faster with concurrent calculations
- **Overall runtime**: 50-70% reduction in total execution time

The actual improvements depend on:
- Network latency
- Available CPU cores
- Cloud server specifications
- Number of stocks being processed
