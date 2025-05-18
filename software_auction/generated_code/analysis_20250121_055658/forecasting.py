# Analyze time series data for forecasting future values
import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import warnings
warnings.filterwarnings('ignore')

# Load data
# df = pd.read_csv('data.csv')

# Define the model
# model = ARIMA(df, order=(5,1,0))

# Fit the model
# model_fit = model.fit(disp=0)

# Plot the original series and the forecasted series
# plt.plot(df)
# plt.plot(model_fit.fittedvalues, color='red')

def forecast_time_series(data, time_col, value_col, forecast_periods=5):
    """
    Generate time series forecasts using ARIMA and Exponential Smoothing
    
    Args:
        data: DataFrame with time series data
        time_col: Name of the column containing timestamps
        value_col: Name of the column containing values to forecast
        forecast_periods: Number of periods to forecast
        
    Returns:
        Dictionary with forecast results
    """
    # Ensure time column is datetime
    data[time_col] = pd.to_datetime(data[time_col])
    data = data.sort_values(by=time_col)
    
    # Create time series
    ts = data.set_index(time_col)[value_col]
    
    results = {
        'original_data': {
            'times': ts.index.tolist(),
            'values': ts.values.tolist()
        },
        'forecast_periods': forecast_periods
    }
    
    # ARIMA forecast
    try:
        arima_model = ARIMA(ts, order=(1, 1, 1))
        arima_fit = arima_model.fit()
        arima_forecast = arima_fit.forecast(steps=forecast_periods)
        
        # Calculate forecast dates
        last_date = ts.index[-1]
        freq = pd.infer_freq(ts.index)
        if freq is None:
            # If frequency can't be inferred, assume daily
            forecast_dates = [last_date + pd.Timedelta(days=i+1) for i in range(forecast_periods)]
        else:
            forecast_dates = pd.date_range(start=last_date, periods=forecast_periods+1, freq=freq)[1:]
        
        results['arima'] = {
            'forecast': arima_forecast.tolist(),
            'forecast_dates': [str(date) for date in forecast_dates],
            'model_summary': str(arima_fit.summary())
        }
    except Exception as e:
        results['arima'] = {'error': str(e)}
    
    # Exponential Smoothing forecast
    try:
        es_model = ExponentialSmoothing(ts, trend='add', seasonal='add', seasonal_periods=min(len(ts)//2, 12))
        es_fit = es_model.fit()
        es_forecast = es_fit.forecast(forecast_periods)
        
        results['exp_smoothing'] = {
            'forecast': es_forecast.tolist(),
            'forecast_dates': [str(date) for date in forecast_dates],
            'model_summary': str(es_fit.summary())
        }
    except Exception as e:
        results['exp_smoothing'] = {'error': str(e)}
    
    return results

def detect_anomalies(ts, window=5, threshold=2.0):
    """
    Detect anomalies in time series using rolling statistics
    
    Args:
        ts: Time series data (pandas Series with DatetimeIndex)
        window: Window size for rolling statistics
        threshold: Z-score threshold for anomaly detection
        
    Returns:
        List of anomalies with dates and values
    """
    # Calculate rolling mean and standard deviation
    rolling_mean = ts.rolling(window=window).mean()
    rolling_std = ts.rolling(window=window).std()
    
    # Calculate z-scores
    z_scores = (ts - rolling_mean) / rolling_std
    
    # Identify anomalies
    anomalies = ts[abs(z_scores) > threshold]
    
    return {
        'anomaly_dates': [str(date) for date in anomalies.index],
        'anomaly_values': anomalies.values.tolist(),
        'anomaly_z_scores': z_scores[anomalies.index].tolist()
    }

def analyze_seasonality(ts):
    """
    Analyze seasonality in time series data
    
    Args:
        ts: Time series data (pandas Series with DatetimeIndex)
        
    Returns:
        Dictionary with seasonality analysis
    """
    results = {}
    
    # Check if we have enough data
    if len(ts) < 10:
        return {'error': 'Not enough data for seasonality analysis'}
    
    # Decompose time series
    try:
        from statsmodels.tsa.seasonal import seasonal_decompose
        
        # Try to infer frequency
        freq = pd.infer_freq(ts.index)
        if freq is None:
            # If frequency can't be inferred, use a reasonable period
            period = min(len(ts) // 2, 12)
        else:
            # Map frequency to period
            freq_map = {
                'D': 7,      # Daily -> Weekly
                'W': 52,     # Weekly -> Yearly
                'M': 12,     # Monthly -> Yearly
                'Q': 4,      # Quarterly -> Yearly
                'Y': 5       # Yearly -> 5-year cycle
            }
            period = freq_map.get(freq[0], min(len(ts) // 2, 12))
        
        decomposition = seasonal_decompose(ts, model='additive', period=period)
        
        results['trend'] = decomposition.trend.dropna().values.tolist()
        results['seasonal'] = decomposition.seasonal.dropna().values.tolist()
        results['residual'] = decomposition.resid.dropna().values.tolist()
        results['period'] = period
        
        # Calculate strength of seasonality
        var_seasonal = np.var(decomposition.seasonal.dropna())
        var_residual = np.var(decomposition.resid.dropna())
        var_total = var_seasonal + var_residual
        
        if var_total > 0:
            seasonality_strength = max(0, var_seasonal / var_total)
            results['seasonality_strength'] = seasonality_strength
            
            if seasonality_strength > 0.6:
                results['interpretation'] = 'Strong seasonality'
            elif seasonality_strength > 0.3:
                results['interpretation'] = 'Moderate seasonality'
            else:
                results['interpretation'] = 'Weak seasonality'
        else:
            results['seasonality_strength'] = 0
            results['interpretation'] = 'No seasonality'
            
    except Exception as e:
        results['error'] = str(e)
    
    return results
