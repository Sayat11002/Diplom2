import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor
from translations import t


@st.cache_data
def load_data(path: str):
    df = pd.read_csv(path)
    df = df[["Company", "Mark", "Price", "Volume", "Year", "Fuel Type",
             "Transmission", "Mileage", "Car_Type", "Region", "Link"]].copy()
    df["Fuel Type"] = df["Fuel Type"].replace(["nan", "None", ""], "бензин")
    for col in ["Company", "Mark", "Fuel Type", "Transmission", "Car_Type"]:
        df[col] = df[col].astype(str).str.lower()
    return df.reset_index(drop=True)

CATEGORICAL_COLS = ["Company", "Mark", "Fuel Type", "Transmission", "Car_Type"]

@st.cache_data
def preprocess_model_data(data: pd.DataFrame):
    df = data[["Company", "Mark", "Price", "Volume", "Year", "Fuel Type",
               "Transmission", "Mileage", "Car_Type"]].copy()
    encoders = {}
    for col in CATEGORICAL_COLS:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        encoders[col] = le
    df["Age"] = 2026 - df["Year"]
    df["Mileage_per_year"] = df["Mileage"] / (df["Age"] + 1)
    return df, encoders

@st.cache_resource
def train_model(_df_model: pd.DataFrame):
    X = _df_model.drop("Price", axis=1)
    y = _df_model["Price"]
    model = RandomForestRegressor(
        n_estimators=300, max_depth=12,
        random_state=42, n_jobs=-1
    )
    model.fit(X, y)
    return model


def show_price_prediction():
    st.title(t("price_title"))

    dataset_path = st.session_state.get("dataset_path", "Cars_Dataset3.csv")
    raw_data = load_data(dataset_path)
    df_model, encoders = preprocess_model_data(raw_data)
    model = train_model(df_model)

    car = st.session_state.get("price_input_data", {})

    if car and st.session_state.get("_last_car_applied") != id(car):
        try:
            company_val = str(car.get("company", "")).lower()
            mark_val    = str(car.get("mark", "")).lower()

            if raw_data[(raw_data["Company"] == company_val) &
                        (raw_data["Mark"] == mark_val)].empty:
                raise ValueError("Car not found in dataset")

            all_companies = sorted(raw_data["Company"].unique())
            if company_val not in all_companies:
                raise ValueError(f"Company {company_val} not in dataset")

            marks_for_company = sorted(
                raw_data[raw_data["Company"] == company_val]["Mark"].unique()
            )
            if mark_val not in marks_for_company:
                raise ValueError(f"Mark {mark_val} not in dataset")

            st.session_state["_pp_company_val"] = company_val
            st.session_state["_pp_mark_val"]    = mark_val
            st.session_state["_pp_year_val"]    = int(car.get("year", 2020))
            st.session_state["_pp_cartype_val"] = str(car.get("car_type", "")).lower()
            st.session_state["_pp_fuel_val"]    = str(car.get("fuel_type", "бензин")).lower()
            st.session_state["_pp_volume_val"]  = str(float(car.get("volume", 2.0)))
            st.session_state["_last_car_applied"] = id(car)

            st.success(
                f"{t('price_from_rec')} "
                f"**{car.get('company','').title()} {car.get('mark','').title()} {car.get('year','')}**"
            )

        except Exception as e:
            st.warning(f"{t('price_not_found')} {e}.")
            st.session_state["_last_car_applied"] = id(car)

    all_companies = sorted(raw_data["Company"].unique())

    default_company = st.session_state.get("_pp_company_val", all_companies[0])
    if default_company not in all_companies:
        default_company = all_companies[0]

    col1, col2 = st.columns(2)

    with col1:
        company = st.selectbox(
            t("price_company"),
            all_companies,
            index=all_companies.index(default_company),
            key="pp_company_widget"
        )

        if st.session_state.get("_pp_company_val") != company:
            st.session_state["_pp_company_val"] = company
            st.session_state["_pp_mark_val"]    = None

        marks = sorted(raw_data[raw_data["Company"] == company]["Mark"].unique())
        default_mark = st.session_state.get("_pp_mark_val")
        if default_mark not in marks:
            default_mark = marks[0]

        mark = st.selectbox(
            t("price_mark"),
            marks,
            index=marks.index(default_mark),
            key="pp_mark_widget"
        )
        st.session_state["_pp_mark_val"] = mark

        default_year = st.session_state.get("_pp_year_val", 2020)
        year = st.number_input(
            t("price_year"), 1990, 2026,
            value=int(default_year),
            key="pp_year_widget"
        )
        st.session_state["_pp_year_val"] = year

    with col2:
        car_types = sorted(
            raw_data[(raw_data["Company"] == company) &
                     (raw_data["Mark"] == mark)]["Car_Type"].unique()
        )
        default_cartype = st.session_state.get("_pp_cartype_val", "")
        if default_cartype not in car_types:
            default_cartype = car_types[0] if car_types else "седан"

        car_type = st.selectbox(
            t("price_cartype"),
            car_types if car_types else ["седан"],
            index=(car_types.index(default_cartype)
                   if car_types and default_cartype in car_types else 0),
            key="pp_cartype_widget"
        )

        possible_volumes = sorted(
            raw_data[
                (raw_data["Company"] == company) &
                (raw_data["Mark"] == mark) &
                (raw_data["Car_Type"] == car_type) &
                (raw_data["Year"].between(year - 2, year + 2))
            ]["Volume"].dropna().unique()
        )
        volume_options = ([str(round(v, 1)) for v in possible_volumes]
                          if len(possible_volumes) > 0 else ["2.0"])

        default_volume = st.session_state.get("_pp_volume_val", "2.0")
        if default_volume not in volume_options:
            default_volume = volume_options[0]

        volume_str = st.selectbox(
            t("price_volume"),
            volume_options,
            index=volume_options.index(default_volume),
            key="pp_volume_widget"
        )
        volume = float(volume_str)

        possible_fuels = sorted(
            raw_data[
                (raw_data["Company"] == company) &
                (raw_data["Mark"] == mark) &
                (raw_data["Car_Type"] == car_type)
            ]["Fuel Type"].unique()
        )
        fuel_options = possible_fuels if possible_fuels else ["бензин"]

        default_fuel = st.session_state.get("_pp_fuel_val", "бензин")
        if default_fuel not in fuel_options:
            default_fuel = fuel_options[0]

        fuel = st.selectbox(
            t("price_fuel"),
            fuel_options,
            index=fuel_options.index(default_fuel),
            key="pp_fuel_widget"
        )

        transmission = st.selectbox(
            t("price_transmission"),
            sorted(raw_data["Transmission"].unique()),
            key="pp_trans_widget"
        )

    mileage = st.number_input(t("price_mileage"), 0, 1_000_000, 85_000, step=5000)

    
    if st.button(t("price_calc_btn"), type="primary", use_container_width=True):

        input_df = pd.DataFrame({
            "Company":      [company],
            "Mark":         [mark],
            "Volume":       [volume],
            "Year":         [year],
            "Fuel Type":    [fuel],
            "Transmission": [transmission],
            "Mileage":      [mileage],
            "Car_Type":     [car_type],
        })

        for col in CATEGORICAL_COLS:
            val = input_df[col].iloc[0]
            if val not in encoders[col].classes_:
                input_df[col] = encoders[col].classes_[0]
            input_df[col] = encoders[col].transform(input_df[col])

        input_df["Age"]              = 2026 - input_df["Year"]
        input_df["Mileage_per_year"] = input_df["Mileage"] / (input_df["Age"] + 1)

        pred_price = max(int(model.predict(input_df)[0]),500_000)
        pred_price=(pred_price//1000)*1000
    
        similar = raw_data[
            (raw_data["Company"] == company) &
            (raw_data["Mark"] == mark)
        ].copy()
        similar["price_diff"] = abs(similar["Price"] - pred_price)
        similar = similar.sort_values("price_diff").head(10)

        
        region_stats = (
            raw_data[
                (raw_data["Company"] == company) &
                (raw_data["Mark"] == mark)
            ]
            .groupby("Region")
            .agg(
                Avg=(     "Price", "mean"),
                Median=(  "Price", "median"),
                Count=(   "Price", "count")
            )
            .round(0)
            .reset_index()
            .sort_values("Avg", ascending=False)
        )
        region_stats["Avg"]    = region_stats["Avg"].astype(int).map("{:,}".format)
        region_stats["Median"] = region_stats["Median"].astype(int).map("{:,}".format)
        region_stats.columns   = [
            t("price_col_region"),
            t("price_col_avg"),
            t("price_col_med"),
            t("price_col_cnt"),
        ]

        st.session_state["pp_results"] = {
            "predicted_price": pred_price,
            "company":         company,
            "mark":            mark,
            "year":            year,
            "similar":         similar,
            "region_stats":    region_stats,
        }
        st.session_state["predicted_price"] = pred_price
        st.session_state["car_data"] = {
            "company":   company,
            "mark":      mark,
            "year":      year,
            "volume":    volume,
            "fuel_type": fuel.capitalize(),
        }

   
    results = st.session_state.get("pp_results")
    if results:
        pred_price   = results["predicted_price"]
        similar      = results["similar"]
        region_stats = results["region_stats"]
        mark_res     = results["mark"]
        year_res     = results["year"]

        st.success(t("price_result").format(pred_price))

        st.subheader(t("price_similar"))
        for _, row in similar.iterrows():
            st.markdown(
                f"**{row['Company'].title()} {row['Mark'].title()} {int(row['Year'])}**  \n"
                f" {int(row['Price']):,} ₸  \n"
                f"[{t('price_link')}]({row['Link']})"
            )

        st.divider()
        st.subheader(f"{t('price_analytics')} {mark_res.title()} ({year_res})")
        model_data = raw_data[
            (raw_data["Company"] == results["company"]) &
            (raw_data["Mark"] == mark_res) &
            (raw_data["Year"].between(year_res - 3, year_res + 3))
        ]
        if not model_data.empty:
            colA, colB = st.columns(2)
            with colA:
                avg_price = model_data.groupby("Year")["Price"].mean().round(0).reset_index()
                fig1 = px.bar(avg_price, x="Year", y="Price", title=t("price_avg_year"))
                st.plotly_chart(fig1, use_container_width=True)
            with colB:
                avg_mileage = model_data.groupby("Year")["Mileage"].mean().round(0).reset_index()
                fig2 = px.bar(avg_mileage, x="Year", y="Mileage", title=t("price_avg_mileage"))
                st.plotly_chart(fig2, use_container_width=True)

        st.subheader(f"{t('price_regions')} {mark_res.title()}")
        st.dataframe(region_stats, use_container_width=True, hide_index=True)

    
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button(t("price_to_rec")):
            st.session_state["page_key"] = "nav_rec"
            st.rerun()
    with col2:
        if st.button(t("price_to_tco"), type="primary"):
            st.session_state["page_key"] = "nav_tco"
            st.rerun()
    with col3:
        if st.button(t("price_reset")):
            for key in [
                "price_input_data", "pp_results",
                "_pp_company_val", "_pp_mark_val", "_pp_year_val",
                "_pp_cartype_val", "_pp_fuel_val", "_pp_volume_val",
                "_last_car_applied", "predicted_price"
            ]:
                st.session_state.pop(key, None)
            st.rerun()
