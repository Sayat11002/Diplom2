import streamlit as st
import pandas as pd
import json
from openai import OpenAI
from translations import t

def show_car_recommendation():
    st.title(t("rec_title"))
    client = OpenAI(api_key=st.secrets["API_KEY"])


    def _set_car(rec: dict):
        fuel_raw = rec.get("fuel_type", "бензин")
        st.session_state.car_data = {
            "company":   rec.get("company", ""),
            "mark":      rec.get("mark", ""),
            "year":      int(rec.get("year", 2020)),
            "volume":    float(rec.get("volume", 2.0)),
            "fuel_type": fuel_raw.capitalize(),
            "car_type":  rec.get("car_type", ""),
            "source":    "AI Recommendation",
        }
        st.session_state.predicted_price = None
        st.session_state["price_input_data"] = st.session_state.car_data.copy()

    @st.cache_data
    def load_data(path: str):
        df = pd.read_csv(path)
        df = df[["Company", "Mark", "Price", "Volume", "Year", "Fuel Type",
                 "Transmission", "Mileage", "Car_Type", "Region", "Link"]].copy()
        df["Fuel Type"] = df["Fuel Type"].replace(["nan", "None", ""], "бензин")
        return df.reset_index(drop=True)

    dataset_path = st.session_state.get("dataset_path", r"C:\Users\Саят\Downloads\Cars_Dataset3.csv")
    load_data(dataset_path)

    if st.session_state.get("car_data"):
        car = st.session_state.car_data
        st.success(
            f"{t('rec_selected')} **{car.get('company','')} {car.get('mark','')} {car.get('year','')}** "
            f"· {car.get('volume', '?')} л · {car.get('fuel_type', '—')}"
        )
    user_query = st.text_area(
        t("rec_query_label"),
        placeholder=t("rec_query_placeholder"),
        height=120,
        key="rec_query",
    )

    if st.button(t("rec_button"), type="primary", use_container_width=True):
        if not user_query.strip():
            st.error(t("rec_error_empty"))
            return

        with st.spinner(t("rec_spinner")):
            lang = st.session_state.get("lang", "ru")

            if lang == "en":
                system_prompt = "You are a car expert in Kazakhstan."
                prompt = f"""User is looking for: "{user_query}"
Suggest up to 5 most suitable options.
Return ONLY JSON:
{{"recommendations": [
  {{"rank": 1, "company": "Toyota", "mark": "Camry", "year": 2021,
   "volume": 2.5, "fuel_type": "gasoline", "car_type": "sedan",
   "reason": "Reliable family sedan"}}
]}}
fuel_type: gasoline | diesel | hybrid | gas | electric
car_type: suv | sedan | hatchback | minivan | wagon | sports | pickup | commercial
Write company and mark in lowercase english."""
            elif lang == "kk":
                system_prompt = "Сіз Қазақстандағы автомобиль сарапшысысыз."
                prompt = f"""Пайдаланушы іздейді: "{user_query}"
Ең қолайлы 5 нұсқаны ұсыныңыз.
ТІКЕЛЕЙ JSON қайтарыңыз:
{{"recommendations": [
  {{"rank": 1, "company": "toyota", "mark": "camry", "year": 2021,
   "volume": 2.5, "fuel_type": "бензин", "car_type": "седан",
   "reason": "Сенімді отбасылық седан"}}
]}}
fuel_type: бензин | дизель | гибрид | газ | электро
car_type: внедорожник | седан | хэтчбек | минивэн | универсал | спорт | пикап | коммерческий
Компания мен марканы кіші әріппен орыс немесе ағылшын тілінде жазыңыз."""
            else:
                system_prompt = "Ты эксперт по автомобилям в Казахстане."
                prompt = f"""Пользователь ищет: "{user_query}"
Предложи максимум 5 самых подходящих вариантов.
Верни ТОЛЬКО JSON:
{{"recommendations": [
  {{"rank": 1, "company": "Toyota", "mark": "Camry", "year": 2021,
   "volume": 2.5, "fuel_type": "бензин", "car_type": "седан",
   "reason": "Надёжный семейный седан"}}
]}}
fuel_type: бензин | дизель | гибрид | газ | электро
car_type: внедорожник | седан | хэтчбек | минивэн | универсал | спорт | пикап | коммерческий
Пример: если хочешь порекомендовать mercedes-benz e-класс — напиши так, а не e-class."""

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": prompt},
                    ]
                )

                result = response.choices[0].message.content.strip()
                if "```" in result:
                    result = result.split("```")[1]
                    if result.startswith("json"):
                        result = result[4:]

                data = json.loads(result)
                st.session_state["ai_recommendations"] = data.get("recommendations", [])
                st.success(t("rec_success"))

            except Exception as e:
                st.error(t("rec_error_gpt"))
                st.code(str(e))

    recs = st.session_state.get("ai_recommendations", [])
    if recs:
        st.subheader(t("rec_subheader"))
        for rec in recs:
            with st.container(border=True):
                col_a, col_b = st.columns([4, 2])
                with col_a:
                    st.markdown(f"**#{rec.get('rank')} {rec.get('company','').title()} {rec.get('mark','').title()}**")
                    st.write(f"📅 {rec.get('year')} · {rec.get('car_type')}")
                    st.write(f"⛽ {rec.get('fuel_type')} · {rec.get('volume')} л")
                    st.write(f"**{t('rec_why')}** {rec.get('reason')}")
                with col_b:
                    if st.button(
                        t("rec_select_btn"),
                        key=f"rec_select_{rec.get('rank')}",
                        use_container_width=True
                    ):
                        _set_car(rec)
                        st.rerun()


    if st.session_state.get("car_data"):
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button(t("rec_to_price"), use_container_width=True, type="primary"):
                st.session_state["page_key"] = "nav_price"
                st.rerun()
        with col2:
            if st.button(t("rec_to_tco"), use_container_width=True):
                st.session_state["page_key"] = "nav_tco"
                st.rerun()
