"""
Predictor Agent for linear regression-based predictions, very basic, work in progress
"""

from typing import Dict, List, Optional
import pandas as pd
from sklearn.linear_model import LinearRegression


class PredictorAgent:
    def __init__(self):
        pass

    def make_prediction(self, data: Optional[List[Dict]] = None, target: str = "y") -> Dict:
        """Perform regression analysis and predictions"""
        try:
            # Use sample data if none provided
            if not data or len(data) == 0:
                data = [
                    {"x": 1, "y": 2.1}, {"x": 2, "y": 3.9}, {"x": 3, "y": 6.1},
                    {"x": 4, "y": 7.8}, {"x": 5, "y": 10.2}
                ]
                print("Using sample data for demonstration")

            df = pd.DataFrame(data)

            if target not in df.columns:
                available_cols = list(df.columns)
                return {
                    "success": False,
                    "error": f"Target column '{target}' not found.",
                    "available_columns": available_cols,
                    "suggestion": f"Try using one of: {available_cols}"
                }

            # Prepare features (all columns except target)
            X = df.drop(columns=[target])
            y = df[target]

            if X.empty or len(X.columns) == 0:
                return {
                    "success": False,
                    "error": "No feature columns available for prediction"
                }

            # Train a linear regression model
            model = LinearRegression()
            model.fit(X, y)

            predictions = model.predict(X)
            residuals = y - predictions

            return {
                "success": True,
                "message": f"Trained regression model to predict '{target}'",
                "model_info": {
                    "features": list(X.columns),
                    "target": target,
                    "training_samples": len(df)
                },
                "performance": {
                    "r_squared": round(model.score(X, y), 4),
                    "mean_absolute_error": round(abs(residuals).mean(), 4)
                },
                "coefficients": {
                    "intercept": round(model.intercept_, 4),
                    "feature_coefficients": dict(zip(X.columns, [round(c, 4) for c in model.coef_]))
                },
                "sample_predictions": [
                    {"actual": round(float(y.iloc[i]), 2), "predicted": round(float(predictions[i]), 2)}
                    for i in range(min(5, len(predictions)))
                ],
                "data_used": data
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Prediction failed: {str(e)}"
            }