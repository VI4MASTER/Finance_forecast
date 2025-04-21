import pandas as pd
import numpy as np
from prophet import Prophet
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import logging

logger = logging.getLogger(__name__)


def prepare_data(df, selected_years, test_mode=False, fund_typ=None):
    """Підготовка даних для прогнозування."""
    if df.empty:
        logger.error("Вхідний DataFrame порожній")
        return pd.DataFrame(), pd.DataFrame()

    df['date'] = pd.to_datetime(df['rep_period'].str.replace('.', '-'), format='%m-%Y')
    df = df[df['date'].dt.year.isin(selected_years)]

    if fund_typ:
        df = df[df['fund_typ'] == fund_typ]

    if df.empty:
        logger.error(f"Після фільтрації за роками {selected_years} і fund_typ={fund_typ} даних немає")
        return pd.DataFrame(), pd.DataFrame()

    df = df.sort_values('date')

    if test_mode:
        train_df = df[df['date'].dt.year < 2024]
        test_df = df[df['date'].dt.year == 2024]
    else:
        train_df = df
        test_df = pd.DataFrame()

    logger.debug(f"train_df: {len(train_df)} записів, test_df: {len(test_df)} записів")
    return train_df, test_df


def calculate_mape(y_true, y_pred):
    """Обчислення MAPE (Mean Absolute Percentage Error)."""
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    # Уникаємо ділення на нуль
    non_zero = y_true != 0
    if not np.any(non_zero):
        return np.inf
    return np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero])) * 100


def prophet_forecast(train_df, test_df, forecast_periods):
    """Прогнозування за допомогою Prophet."""
    try:
        if train_df.empty:
            logger.error("train_df порожній для Prophet")
            return None, None

        prophet_df = train_df[['date', 'fakt_amt']].rename(columns={'date': 'ds', 'fakt_amt': 'y'})
        model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        model.fit(prophet_df)

        future = model.make_future_dataframe(periods=forecast_periods, freq='MS')
        forecast = model.predict(future)

        forecast_result = forecast[['ds', 'yhat']].tail(forecast_periods)
        forecast_result = forecast_result.rename(columns={'ds': 'date', 'yhat': 'forecast'})

        metrics = None
        if not test_df.empty:
            test_dates = test_df['date']
            test_values = test_df['fakt_amt']
            test_forecast = forecast[forecast['ds'].isin(test_dates)]['yhat']
            if len(test_values) == len(test_forecast):
                mae = mean_absolute_error(test_values, test_forecast)
                rmse = np.sqrt(mean_squared_error(test_values, test_forecast))
                mape = calculate_mape(test_values, test_forecast)
                metrics = {'MAE': mae, 'RMSE': rmse, 'MAPE': mape}

        return forecast_result, metrics
    except Exception as e:
        logger.error(f"Помилка Prophet: {str(e)}")
        return None, None


def sarima_forecast(train_df, test_df, forecast_periods):
    """Прогнозування за допомогою SARIMA."""
    try:
        if train_df.empty:
            logger.error("train_df порожній для SARIMA")
            return None, None

        train_series = train_df.set_index('date')['fakt_amt']
        model = SARIMAX(train_series, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        results = model.fit(disp=False)

        forecast = results.forecast(steps=forecast_periods)
        forecast_dates = pd.date_range(start=train_series.index[-1] + pd.offsets.MonthBegin(1),
                                       periods=forecast_periods, freq='MS')
        forecast_result = pd.DataFrame({'date': forecast_dates, 'forecast': forecast})

        metrics = None
        if not test_df.empty:
            test_series = test_df.set_index('date')['fakt_amt']
            test_forecast = results.forecast(steps=len(test_series))
            if len(test_series) == len(test_forecast):
                mae = mean_absolute_error(test_series, test_forecast)
                rmse = np.sqrt(mean_squared_error(test_series, test_forecast))
                mape = calculate_mape(test_series, test_forecast)
                metrics = {'MAE': mae, 'RMSE': rmse, 'MAPE': mape}

        return forecast_result, metrics
    except Exception as e:
        logger.error(f"Помилка SARIMA: {str(e)}")
        return None, None


def gradient_boosting_forecast(train_df, test_df, forecast_periods):
    """Прогнозування за допомогою Gradient Boosting."""
    try:
        if train_df.empty:
            logger.error("train_df порожній для Gradient Boosting")
            return None, None

        train_df = train_df.copy()
        train_df['month'] = train_df['date'].dt.month
        train_df['year'] = train_df['date'].dt.year
        X_train = train_df[['month', 'year']]
        y_train = train_df['fakt_amt']

        model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        last_date = train_df['date'].max()
        future_dates = pd.date_range(start=last_date + pd.offsets.MonthBegin(1),
                                     periods=forecast_periods, freq='MS')
        future_df = pd.DataFrame({
            'date': future_dates,
            'month': [d.month for d in future_dates],
            'year': [d.year for d in future_dates]
        })

        X_future = future_df[['month', 'year']]
        forecast = model.predict(X_future)
        forecast_result = pd.DataFrame({'date': future_dates, 'forecast': forecast})

        metrics = None
        if not test_df.empty:
            test_df = test_df.copy()
            test_df['month'] = test_df['date'].dt.month
            test_df['year'] = test_df['date'].dt.year
            X_test = test_df[['month', 'year']]
            y_test = test_df['fakt_amt']
            test_forecast = model.predict(X_test)
            if len(y_test) == len(test_forecast):
                mae = mean_absolute_error(y_test, test_forecast)
                rmse = np.sqrt(mean_squared_error(y_test, test_forecast))
                mape = calculate_mape(y_test, test_forecast)
                metrics = {'MAE': mae, 'RMSE': rmse, 'MAPE': mape}

        return forecast_result, metrics
    except Exception as e:
        logger.error(f"Помилка Gradient Boosting: {str(e)}")
        return None, None