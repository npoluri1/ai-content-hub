import json
import math
import os
from datetime import datetime, timedelta
from collections import defaultdict


class PredictiveMonitor:
    def __init__(self, sql_store=None, model_dir="./data/models"):
        self.sql_store = sql_store
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

    def _get_daily_counts(self, source=None, topic=None, days=90):
        if not self.sql_store:
            return {}
        try:
            counts = defaultdict(int)
            sources_to_check = [source] if source else list(self.sql_store.get_stats().get("by_source", {}).keys())
            for src in sources_to_check:
                items = self.sql_store.get_by_source(src, limit=2000)
                for item in items:
                    pub = item.get("published_at")
                    if not pub:
                        continue
                    if isinstance(pub, str):
                        pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00").split("+")[0])
                    else:
                        pub_dt = pub
                    if (datetime.utcnow() - pub_dt).days > days:
                        continue
                    if topic:
                        topics = item.get("topics", "")
                        if isinstance(topics, str):
                            topics_list = topics.split(",")
                        else:
                            topics_list = topics or []
                        if topic not in topics_list:
                            continue
                    date_key = pub_dt.strftime("%Y-%m-%d")
                    counts[date_key] += 1
            return dict(sorted(counts.items()))
        except Exception:
            return {}

    def _get_hourly_counts(self, source=None, days=30):
        if not self.sql_store:
            return {}
        try:
            hourly = defaultdict(int)
            sources_to_check = [source] if source else list(self.sql_store.get_stats().get("by_source", {}).keys())
            for src in sources_to_check:
                items = self.sql_store.get_by_source(src, limit=2000)
                for item in items:
                    pub = item.get("published_at")
                    if not pub:
                        continue
                    if isinstance(pub, str):
                        pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00").split("+")[0])
                    else:
                        pub_dt = pub
                    if (datetime.utcnow() - pub_dt).days > days:
                        continue
                    hourly[pub_dt.hour] += 1
            return dict(sorted(hourly.items()))
        except Exception:
            return {}

    def _moving_average(self, values, window=7):
        if len(values) < window:
            return values[:]
        result = []
        for i in range(len(values)):
            if i < window - 1:
                result.append(sum(values[:i + 1]) / (i + 1))
            else:
                result.append(sum(values[i - window + 1:i + 1]) / window)
        return result

    def _exponential_smoothing(self, values, alpha=0.3):
        if not values:
            return []
        result = [values[0]]
        for i in range(1, len(values)):
            smoothed = alpha * values[i] + (1 - alpha) * result[-1]
            result.append(smoothed)
        return result

    def _linear_regression(self, values):
        n = len(values)
        if n < 2:
            return 0, 0
        x_vals = list(range(n))
        x_mean = sum(x_vals) / n
        y_mean = sum(values) / n
        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, values))
        den = sum((x - x_mean) ** 2 for x in x_vals)
        slope = num / den if den != 0 else 0
        intercept = y_mean - slope * x_mean
        return slope, intercept

    def _std_dev(self, values):
        if len(values) < 2:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)

    def _confidence_from_data(self, values):
        if len(values) < 3:
            return 0.5
        cv = self._std_dev(values) / max(sum(values) / len(values), 0.0001)
        confidence = max(0, min(1, 1 - cv))
        return round(confidence, 3)

    def predict_content_volume(self, source=None, topic=None, days_ahead=7):
        counts = self._get_daily_counts(source=source, topic=topic, days=90)
        if not counts:
            return {"predictions": [], "confidence": 0, "model": "moving_average"}
        values = list(counts.values())
        if len(values) < 2:
            return {"predictions": [], "confidence": 0, "model": "moving_average"}
        smoothed = self._moving_average(values, window=min(7, len(values)))
        slope, intercept = self._linear_regression(smoothed)
        std = self._std_dev(smoothed)
        last_date = datetime.strptime(list(counts.keys())[-1], "%Y-%m-%d")
        predictions = []
        for i in range(1, days_ahead + 1):
            pred_date = (last_date + timedelta(days=i)).strftime("%Y-%m-%d")
            predicted = max(0, intercept + slope * (len(smoothed) + i - 1))
            lower = max(0, predicted - 2 * std)
            upper = predicted + 2 * std
            predictions.append({
                "date": pred_date,
                "predicted": round(predicted, 2),
                "lower_bound": round(lower, 2),
                "upper_bound": round(upper, 2),
            })
        confidence = self._confidence_from_data(smoothed)
        return {
            "predictions": predictions,
            "confidence": confidence,
            "model": "moving_average",
            "source": source,
            "topic": topic,
        }

    def predict_peak_hours(self, source=None, days=30):
        hourly = self._get_hourly_counts(source=source, days=days)
        if not hourly:
            return []
        total = sum(hourly.values())
        if total == 0:
            return []
        result = []
        for hour in range(24):
            count = hourly.get(hour, 0)
            pct = (count / total) * 100
            result.append({
                "hour": hour,
                "count": count,
                "percentage": round(pct, 2),
                "is_peak": pct > (100 / 24) * 1.5,
            })
        result.sort(key=lambda x: x["count"], reverse=True)
        return result

    def predict_topic_growth(self, topic, days_ahead=30):
        counts = self._get_daily_counts(topic=topic, days=90)
        if not counts:
            return {"topic": topic, "trend": "unknown", "growth_rate": 0, "predictions": [], "confidence": 0}
        values = list(counts.values())
        if len(values) < 7:
            return {"topic": topic, "trend": "insufficient_data", "growth_rate": 0, "predictions": [], "confidence": 0}
        half = len(values) // 2
        first_half_avg = sum(values[:half]) / half
        second_half_avg = sum(values[half:]) / (len(values) - half)
        growth_rate = (second_half_avg - first_half_avg) / max(first_half_avg, 0.0001)
        if growth_rate > 0.1:
            trend = "growing"
        elif growth_rate < -0.1:
            trend = "declining"
        else:
            trend = "stable"
        smoothed = self._exponential_smoothing(values, alpha=0.3)
        slope, intercept = self._linear_regression(smoothed)
        std = self._std_dev(smoothed)
        last_date = datetime.strptime(list(counts.keys())[-1], "%Y-%m-%d")
        predictions = []
        for i in range(1, days_ahead + 1):
            pred_date = (last_date + timedelta(days=i)).strftime("%Y-%m-%d")
            predicted = max(0, intercept + slope * (len(smoothed) + i - 1))
            lower = max(0, predicted - 2 * std)
            upper = predicted + 2 * std
            predictions.append({
                "date": pred_date,
                "predicted": round(predicted, 2),
                "lower_bound": round(lower, 2),
                "upper_bound": round(upper, 2),
            })
        confidence = self._confidence_from_data(smoothed)
        return {
            "topic": topic,
            "trend": trend,
            "growth_rate": round(growth_rate, 4),
            "predictions": predictions,
            "confidence": confidence,
        }

    def anomaly_prediction(self, source=None):
        counts = self._get_daily_counts(source=source, days=30)
        if not counts:
            return {"probability": 0, "expected_range": {"lower": 0, "upper": 0}, "risk_level": "low"}
        values = list(counts.values())
        if len(values) < 7:
            return {"probability": 0, "expected_range": {"lower": 0, "upper": 0}, "risk_level": "low"}
        mean = sum(values) / len(values)
        std = self._std_dev(values)
        recent = values[-7:]
        recent_mean = sum(recent) / len(recent)
        deviation = abs(recent_mean - mean) / max(std, 0.0001)
        probability = min(1, deviation / 3)
        if probability > 0.7:
            risk_level = "high"
        elif probability > 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"
        return {
            "probability": round(probability, 3),
            "expected_range": {
                "lower": round(max(0, mean - 2 * std), 2),
                "upper": round(mean + 2 * std, 2),
            },
            "risk_level": risk_level,
            "source": source,
        }

    def get_trend_forecast(self, topic, days_history=90, days_ahead=30):
        counts = self._get_daily_counts(topic=topic, days=days_history)
        if not counts:
            return {"topic": topic, "forecast": [], "confidence": 0}
        values = list(counts.values())
        if len(values) < 7:
            return {"topic": topic, "forecast": [], "confidence": 0}
        smoothed = self._exponential_smoothing(values, alpha=0.2)
        slope, intercept = self._linear_regression(smoothed)
        std = self._std_dev(smoothed)
        dates = list(counts.keys())
        last_date = datetime.strptime(dates[-1], "%Y-%m-%d")
        forecast = []
        for i in range(0, days_ahead + 1):
            pred_date = (last_date + timedelta(days=i)).strftime("%Y-%m-%d")
            predicted = max(0, intercept + slope * (len(smoothed) + i - 1))
            lower = max(0, predicted - 2 * std)
            upper = predicted + 2 * std
            is_historical = i == 0
            forecast.append({
                "date": pred_date,
                "predicted": round(predicted, 2),
                "lower_bound": round(lower, 2),
                "upper_bound": round(upper, 2),
                "is_historical": is_historical,
            })
        confidence = self._confidence_from_data(smoothed)
        return {
            "topic": topic,
            "forecast": forecast,
            "confidence": confidence,
            "model": "exponential_smoothing",
            "growth_rate": round(slope, 4),
        }

    def get_seasonal_patterns(self, source, days=90):
        counts = self._get_daily_counts(source=source, days=days)
        if not counts:
            return []
        day_of_week_data = defaultdict(list)
        for date_str, count in counts.items():
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                dow = dt.strftime("%A")
                day_of_week_data[dow].append(count)
            except (ValueError, IndexError):
                pass
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        patterns = []
        for day in day_order:
            vals = day_of_week_data.get(day, [0])
            avg_count = sum(vals) / len(vals)
            std = self._std_dev(vals) if len(vals) > 1 else 0
            patterns.append({
                "day_of_week": day,
                "avg_count": round(avg_count, 2),
                "std_dev": round(std, 2),
                "min_count": min(vals),
                "max_count": max(vals),
                "sample_size": len(vals),
            })
        return patterns

    def get_correlation_matrix(self, sources=None, days=30):
        if not self.sql_store:
            return {"sources": [], "matrix": []}
        try:
            all_sources = list(self.sql_store.get_stats().get("by_source", {}).keys())
            if sources:
                all_sources = [s for s in all_sources if s in sources]
            if len(all_sources) < 2:
                return {"sources": all_sources, "matrix": []}
            source_series = {}
            for src in all_sources:
                counts = self._get_daily_counts(source=src, days=days)
                source_series[src] = list(counts.values())
            all_dates = set()
            for src in all_sources:
                counts = self._get_daily_counts(source=src, days=days)
                all_dates.update(counts.keys())
            sorted_dates = sorted(all_dates)
            aligned = {}
            for src in all_sources:
                counts = self._get_daily_counts(source=src, days=days)
                aligned[src] = [counts.get(d, 0) for d in sorted_dates]
            matrix = []
            for i, s1 in enumerate(all_sources):
                row = []
                for j, s2 in enumerate(all_sources):
                    v1 = aligned[s1]
                    v2 = aligned[s2]
                    if len(v1) < 3 or len(v2) < 3:
                        corr = 0
                    else:
                        corr = self._pearson_correlation(v1, v2)
                    row.append(round(corr, 3))
                matrix.append(row)
            return {"sources": all_sources, "matrix": matrix}
        except Exception:
            return {"sources": sources or [], "matrix": []}

    def _pearson_correlation(self, x, y):
        n = len(x)
        if n != len(y) or n < 2:
            return 0
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        num = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        den_x = math.sqrt(sum((x[i] - x_mean) ** 2 for i in range(n)))
        den_y = math.sqrt(sum((y[i] - y_mean) ** 2 for i in range(n)))
        if den_x == 0 or den_y == 0:
            return 0
        return num / (den_x * den_y)
