# main.py
import pandas as pd
from prophet import Prophet
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

# CORS setup
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ya ["http://localhost:3000"] agar specific chahiye
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model classes
class PricePoint(BaseModel):
    date: str
    price: int  # force int

class History(BaseModel):
    history: List[PricePoint]

# Festival dates
FESTIVALS = [
     "2025-10-21",  # Diwali 2025
    "2026-11-08",  # Diwali 2026
    "2025-03-14",  # Holi 2025
    "2026-03-04",  # Holi 2026
    "2025-08-09",  # Raksha Bandhan 2025
    "2026-08-28",  # Raksha Bandhan 2026
    "2025-08-15",  # Independence Day (recurring)
    "2026-08-15",
    "2025-01-26",  # Republic Day
    "2026-01-26",
    "2025-10-02",  # Gandhi Jayanti
    "2026-10-02",
]

@app.post("/predict")
def predict_price(history: History):
    if not history.history:
        return [{"ds": pd.Timestamp.today().date().isoformat(), "yhat": 100}]  # constant fallback

    df = pd.DataFrame([{"ds": h.date, "y": h.price} for h in history.history])
    df["ds"] = pd.to_datetime(df["ds"])


    # Edge case: Only 1 data point
    if len(df) < 2:
        only_point = df.iloc[0]
        future_dates = pd.date_range(start=only_point["ds"], periods=30)
        print("bhai chl rh ahia kya kmuje btao")
        result = [{"ds": date.date().isoformat(), "yhat": int(only_point["y"])} for date in future_dates]
        return result



    try:


        unique_prices = sorted(df["y"].unique().tolist())
        lowest_price = int(df["y"].min())

        print(df)
    # Add holiday window (-2 to +1 days from each festival)
        holidays = []
        for fest in FESTIVALS:
            fest_date = pd.to_datetime(fest)
            for offset in [-2, -1, 0, 1, 2]:  # window
                holidays.append({"ds": fest_date + pd.Timedelta(days=offset), "holiday": "festival"})
        holidays_df = pd.DataFrame(holidays)

        model = Prophet(daily_seasonality=True, holidays=holidays_df)
        model.fit(df)
        print(df)
    # Forecast next 30 days
        future = model.make_future_dataframe(periods=30)
        forecast = model.predict(future)

    # Round prediction to closest real price from history
        def round_to_known_prices(yhat):
            print(yhat)
            print(unique_prices)
            print(min(unique_prices, key=lambda x: abs(x - yhat)))
            return min(unique_prices, key=lambda x: abs(x - yhat))

        result = []
        for _, row in forecast.tail(30).iterrows():
            date_str = row["ds"].date().isoformat()
            if row["ds"].date() in holidays_df["ds"].dt.date.values:
                price = lowest_price
            else:
                price = round_to_known_prices(row["yhat"])
            result.append({"ds": date_str, "yhat": price})

        print(result)    
        return result

    except Exception as e:
        # Fallback in case of unexpected error
        return [{"ds": pd.Timestamp.today().date().isoformat(), "yhat": 100, "error": str(e)}]