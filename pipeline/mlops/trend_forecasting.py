"""Time series trend forecasting using Holt-Winters, ARIMA, and fallback methods."""

from ..core.models import ContentItem
from collections import defaultdict
from datetime import datetime, timedelta
import json
import math
import os
import pickle


class TrendForecaster:
    def __init__(self, model_dir: str = "./data/models/forecast"):
        self.model_dir = model_dir
        self._statsmodels_available = self._check_statsmodels()
        self._model_cache = {}

    def _check_statsmodels(self) -> bool:
        try:
            import statsmodels
            return True
        except ImportError:
            return False

    def _get_series(self, topic: str, days: int) -> list[dict]:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.get_by_topic(topic, limit=5000) if topic else store.search("", limit=5000)
        since = (datetime.now() - timedelta(days=days)).isoformat()
        daily = defaultdict(int)
        for r in results:
            published = r.get("published_at", "")
            if published and published >= since[:10]:
                daily[published[:10]] += 1
        series = []
        for i in range(days):
            date_key = (datetime.now() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            series.append({"date": date_key, "count": daily.get(date_key, 0)})
        return series

    def forecast_topic(self, topic: str, days_history: int = 90, days_ahead: int = 30) -> dict:
        series = self._get_series(topic, days_history)
        forecast = self._forecast_series(series, days_ahead)
        metrics = self.get_forecast_accuracy_metrics(series, forecast)
        seasonality = self.detect_seasonality(series)
        trend_direction = self._get_trend_direction(series)
        return {
            "historical": series,
            "forecast": forecast,
            "metrics": metrics,
            "seasonality": seasonality,
            "trend_direction": trend_direction,
        }

    def forecast_source(self, source: str, days_history: int = 90, days_ahead: int = 30) -> dict:
        series = self._get_source_series(source, days_history)
        forecast = self._forecast_series(series, days_ahead)
        metrics = self.get_forecast_accuracy_metrics(series, forecast)
        seasonality = self.detect_seasonality(series)
        trend_direction = self._get_trend_direction(series)
        return {
            "historical": series,
            "forecast": forecast,
            "metrics": metrics,
            "seasonality": seasonality,
            "trend_direction": trend_direction,
        }

    def _get_source_series(self, source: str, days: int) -> list[dict]:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.get_by_source(source, limit=5000)
        since = (datetime.now() - timedelta(days=days)).isoformat()
        daily = defaultdict(int)
        for r in results:
            published = r.get("published_at", "")
            if published and published >= since[:10]:
                daily[published[:10]] += 1
        series = []
        for i in range(days):
            date_key = (datetime.now() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            series.append({"date": date_key, "count": daily.get(date_key, 0)})
        return series

    def forecast_engagement(self, topic: str = None, days_ahead: int = 30) -> dict:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        if topic:
            results = store.get_by_topic(topic, limit=5000)
        else:
            results = store.search("", limit=5000)
        since = (datetime.now() - timedelta(days=90)).isoformat()
        daily = defaultdict(int)
        for r in results:
            published = r.get("published_at", "")
            if published and published >= since[:10]:
                daily[published[:10]] += int(r.get("engagement", 0) or 0)

        series = []
        for i in range(90):
            date_key = (datetime.now() - timedelta(days=89 - i)).strftime("%Y-%m-%d")
            series.append({"date": date_key, "count": daily.get(date_key, 0)})

        forecast = self._forecast_series(series, days_ahead)
        metrics = self.get_forecast_accuracy_metrics(series, forecast)
        trend_direction = self._get_trend_direction(series)
        return {
            "historical": series,
            "forecast": forecast,
            "metrics": metrics,
            "trend_direction": trend_direction,
        }

    def _forecast_series(self, series: list[dict], days_ahead: int) -> list[dict]:
        if not series:
            return [{"date": (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d"), "predicted": 0, "lower_bound": 0, "upper_bound": 0} for i in range(days_ahead)]

        values = [s["count"] for s in series]

        if self._statsmodels_available:
            try:
                return self._holt_winters_forecast(values, series, days_ahead)
            except Exception:
                try:
                    return self._arima_forecast(values, series, days_ahead)
                except Exception:
                    pass

        return self._moving_average_forecast(values, series, days_ahead)

    def _holt_winters_forecast(self, values: list[float], series: list[dict], days_ahead: int) -> list[dict]:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        series_len = len(values)
        if series_len < 4:
            return self._moving_average_forecast(values, series, days_ahead)

        seasonal_periods = min(7, max(2, series_len // 2))
        try:
            model = ExponentialSmoothing(
                values, trend='add', seasonal='add' if series_len >= 2 * seasonal_periods else None,
                seasonal_periods=seasonal_periods
            ).fit()
            forecast_vals = model.forecast(days_ahead).tolist()
        except Exception:
            return self._moving_average_forecast(values, series, days_ahead)

        last_date = datetime.strptime(series[-1]["date"], "%Y-%m-%d")
        resid = [values[i] - model.fittedvalues[i] if i < len(model.fittedvalues) else 0 for i in range(series_len)]
        std_resid = math.sqrt(sum(r * r for r in resid) / max(len(resid), 1)) if resid else 0

        results = []
        for i in range(days_ahead):
            date = (last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d")
            pred = max(0, forecast_vals[i])
            results.append({
                "date": date,
                "predicted": round(pred, 2),
                "lower_bound_80": round(max(0, pred - 1.282 * std_resid), 2),
                "upper_bound_80": round(pred + 1.282 * std_resid, 2),
                "lower_bound_95": round(max(0, pred - 1.96 * std_resid), 2),
                "upper_bound_95": round(pred + 1.96 * std_resid, 2),
            })
        return results

    def _arima_forecast(self, values: list[float], series: list[dict], days_ahead: int) -> list[dict]:
        from statsmodels.tsa.arima.model import ARIMA
        try:
            model = ARIMA(values, order=(1, 1, 1)).fit()
            forecast_result = model.get_forecast(steps=days_ahead)
            forecast_vals = forecast_result.predicted_mean.tolist()
            conf_int = forecast_result.conf_int(alpha=0.05)
        except Exception:
            return self._moving_average_forecast(values, series, days_ahead)

        last_date = datetime.strptime(series[-1]["date"], "%Y-%m-%d")
        results = []
        for i in range(days_ahead):
            date = (last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d")
            pred = max(0, forecast_vals[i])
            lb = max(0, conf_int.iloc[i, 0]) if i < len(conf_int) else max(0, pred * 0.5)
            ub = max(pred, conf_int.iloc[i, 1]) if i < len(conf_int) else pred * 1.5
            results.append({
                "date": date,
                "predicted": round(pred, 2),
                "lower_bound_80": round(pred - 0.5 * (ub - lb), 2),
                "upper_bound_80": round(pred + 0.5 * (ub - lb), 2),
                "lower_bound_95": round(lb, 2),
                "upper_bound_95": round(ub, 2),
            })
        return results

    def _moving_average_forecast(self, values: list[float], series: list[dict], days_ahead: int) -> list[dict]:
        series_len = len(values)
        last_date = datetime.strptime(series[-1]["date"], "%Y-%m-%d") if series else datetime.now()

        window = min(14, max(3, series_len // 4))
        if series_len >= window:
            recent = values[-window:]
            level = sum(recent) / len(recent)
            if series_len >= 2 * window:
                older = values[-2 * window:-window]
                older_level = sum(older) / len(older)
                trend = (level - older_level) / window
            else:
                trend = 0
        else:
            level = sum(values) / max(len(values), 1) if values else 0
            trend = 0

        resid = [values[i] - level for i in range(series_len)] if values else [0]
        std_resid = math.sqrt(sum(r * r for r in resid) / max(len(resid), 1)) if resid else 0

        results = []
        for i in range(days_ahead):
            date = (last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d")
            pred = max(0, level + trend * (i + 1))
            results.append({
                "date": date,
                "predicted": round(pred, 2),
                "lower_bound_80": round(max(0, pred - 1.282 * std_resid), 2),
                "upper_bound_80": round(pred + 1.282 * std_resid, 2),
                "lower_bound_95": round(max(0, pred - 1.96 * std_resid), 2),
                "upper_bound_95": round(pred + 1.96 * std_resid, 2),
            })
        return results

    def detect_seasonality(self, series: list[dict]) -> dict:
        values = [s["count"] for s in series]
        n = len(values)
        if n < 14:
            return {"weekly": False, "monthly": False, "weekly_strength": 0, "monthly_strength": 0}

        weekly_ac = self._autocorrelation(values, 7)
        monthly_ac = self._autocorrelation(values, 30)
        random_ac = self._autocorrelation(values, 3)

        weekly_strength = max(0, weekly_ac - random_ac) if random_ac >= 0 else weekly_ac
        monthly_strength = max(0, monthly_ac - random_ac) if random_ac >= 0 else monthly_ac

        return {
            "weekly": weekly_strength > 0.15,
            "monthly": monthly_strength > 0.15,
            "weekly_strength": round(weekly_strength, 4),
            "monthly_strength": round(monthly_strength, 4),
            "weekly_ac": round(weekly_ac, 4),
            "monthly_ac": round(monthly_ac, 4),
        }

    def _autocorrelation(self, values: list[float], lag: int) -> float:
        n = len(values)
        if n <= lag:
            return 0
        mean = sum(values) / n
        var = sum((v - mean) ** 2 for v in values)
        if var == 0:
            return 0
        cov = sum((values[i] - mean) * (values[i + lag] - mean) for i in range(n - lag))
        return cov / var

    def detect_trend_changes(self, series: list[dict], window: int = 7) -> list[dict]:
        values = [s["count"] for s in series]
        n = len(values)
        if n < 2 * window:
            return [{"index": 0, "date": series[0]["date"], "type": "start"}]

        changes = []
        for i in range(window, n - window):
            before = values[i - window:i]
            after = values[i:i + window]
            mean_before = sum(before) / len(before)
            mean_after = sum(after) / len(after)
            t_stat = (mean_after - mean_before) / max(math.sqrt((sum((v - mean_before) ** 2 for v in before) + sum((v - mean_after) ** 2 for v in after)) / (2 * window - 2) * (2 / window) if 2 * window > 2 else 1), 0.001)
            if abs(t_stat) > 2.0:
                changes.append({
                    "index": int(i),
                    "date": series[i]["date"],
                    "type": "up" if t_stat > 0 else "down",
                    "magnitude": round(abs(mean_after - mean_before), 2),
                    "t_statistic": round(t_stat, 4),
                })
        return changes

    def get_growth_rate(self, topic: str, days: int = 30) -> float:
        series = self._get_series(topic, days)
        values = [s["count"] for s in series]
        n = len(values)
        if n < 2:
            return 0.0
        first_half = values[:n // 2]
        second_half = values[n // 2:]
        first_avg = sum(first_half) / max(len(first_half), 1)
        second_avg = sum(second_half) / max(len(second_half), 1)
        if first_avg == 0:
            return 1.0 if second_avg > 0 else 0.0
        periods = n // 2
        cagr = (second_avg / first_avg) ** (1.0 / max(periods, 1)) - 1
        return round(cagr, 6)

    def get_topic_lifecycle_stage(self, topic: str) -> str:
        series = self._get_series(topic, 90)
        values = [s["count"] for s in series]
        n = len(values)
        if n < 10:
            return "emerging"

        recent = sum(values[-10:]) / 10
        mid = sum(values[max(0, n // 2 - 5):n // 2 + 5]) / 10
        early = sum(values[:10]) / 10

        growth_rate = self.get_growth_rate(topic, 30)
        total_vol = sum(values)

        if total_vol < 5:
            return "emerging"
        if growth_rate > 0.03 and recent > early * 2:
            return "growing"
        if growth_rate > 0.003 and recent > mid * 0.7:
            return "mature"
        if growth_rate < -0.01 and recent < early * 0.5:
            return "declining"
        if growth_rate > 0.01 and recent > mid * 1.3 and early < mid * 0.5:
            return "resurging"
        if recent > mid * 0.7:
            return "mature"
        if recent < early * 0.3:
            return "declining"
        return "growing" if growth_rate > 0 else "mature"

    def compare_topics_growth(self, topics: list[str], days: int = 30) -> list[dict]:
        results = []
        for topic in topics:
            rate = self.get_growth_rate(topic, days)
            series = self._get_series(topic, days)
            total = sum(s["count"] for s in series)
            stage = self.get_topic_lifecycle_stage(topic)
            results.append({
                "topic": topic,
                "growth_rate": rate,
                "total_mentions": total,
                "stage": stage,
            })
        results.sort(key=lambda x: x["growth_rate"], reverse=True)
        return results

    def _get_trend_direction(self, series: list[dict]) -> str:
        values = [s["count"] for s in series]
        n = len(values)
        if n < 7:
            return "stable"
        recent = sum(values[-7:]) / 7
        older = sum(values[:7]) / 7
        diff = recent - older
        if diff > max(0.5, older * 0.1):
            return "up"
        if diff < -max(0.5, older * 0.1):
            return "down"
        return "stable"

    def get_forecast_accuracy_metrics(self, historical: list[dict], forecast: list[dict]) -> dict:
        if not historical or len(historical) < 2:
            return {"mae": 0, "rmse": 0, "mape": 0, "mase": 0}

        actuals = [s["count"] for s in historical]
        n = len(actuals)

        predictions = [s.get("predicted", 0) for s in forecast]
        if not predictions:
            return {"mae": 0, "rmse": 0, "mape": 0, "mase": 0}

        if self._statsmodels_available:
            try:
                from statsmodels.tsa.holtwinters import ExponentialSmoothing
                train = actuals[:-min(7, len(actuals) // 3)]
                test = actuals[len(train):]
                if len(train) < 4 or len(test) < 1:
                    test_pred = self._moving_average_forecast(
                        [{"date": "", "count": v} for v in train], 0
                    )
                    test_pred_vals = []
                else:
                    seasonal = min(7, max(2, len(train) // 3))
                    model = ExponentialSmoothing(train, trend='add', seasonal=None).fit()
                    test_pred_vals = model.forecast(len(test)).tolist()
                if test_pred_vals:
                    actuals_trim = test
                    preds_trim = test_pred_vals
                else:
                    actuals_trim = actuals
                    preds_trim = predictions[:len(actuals)]
            except Exception:
                actuals_trim = actuals
                preds_trim = predictions[:len(actuals)]
        else:
            preds_trim = predictions[:min(len(predictions), n)]
            actuals_trim = actuals[:len(preds_trim)]

        if not actuals_trim or not preds_trim:
            return {"mae": 0, "rmse": 0, "mape": 0, "mase": 0}

        min_len = min(len(actuals_trim), len(preds_trim))
        actuals_trim = actuals_trim[:min_len]
        preds_trim = preds_trim[:min_len]

        errors = [actuals_trim[i] - preds_trim[i] for i in range(min_len)]
        mae = sum(abs(e) for e in errors) / min_len
        rmse = math.sqrt(sum(e * e for e in errors) / min_len)

        nonzero = [a for a in actuals_trim if a != 0]
        if nonzero:
            mape = sum(abs(errors[i]) / max(abs(actuals_trim[i]), 0.001) for i in range(min_len)) / min_len
        else:
            mape = 0

        if min_len > 1:
            naive_errors = [abs(actuals_trim[i] - actuals_trim[i - 1]) for i in range(1, min_len)]
            naive_mae = sum(naive_errors) / max(len(naive_errors), 1)
            mase = mae / max(naive_mae, 0.001)
        else:
            mase = 0

        return {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "mape": round(mape, 4),
            "mase": round(mase, 4),
        }
