import streamlit as st
import plotly.express as px
from translations import t, td, tl


MRP = 4_325

TAX_TABLE = [
    (1100,          1),
    (1500,          2),
    (2000,          3),
    (2500,          6),
    (3000,          9),
    (4000,         15),
    (float("inf"), 117),
]


def calc_transport_tax(volume_cc: int, fuel_type_en: str) -> int:
    """Транспортный налог. fuel_type_en — нормализованное значение ('electric'/'электро'/'Электро')."""
    if fuel_type_en.lower() in ("electric", "электро"):
        return 0
    base_mrp = 1
    lower = 0
    for upper, mrp in TAX_TABLE:
        if volume_cc <= upper:
            base_mrp = mrp
            break
        lower = upper
    tax = base_mrp * MRP
    if volume_cc > 1500:
        tax += (volume_cc - lower) * 7
    return int(tax)


UTIL_BASE = 50 * MRP  


def calc_utilsbor(volume_cc: int, fuel_type_en: str) -> int:
    if fuel_type_en.lower() in ("electric", "электро"):
        return int(UTIL_BASE * 0.15)
    table = {
        (0,    1000): 0.15,
        (1001, 2000): 0.35,
        (2001, 3000): 0.50,
        (3001, 4000): 1.00,
        (4001, float("inf")): 2.30,
    }
    for (lo, hi), coeff in table.items():
        if lo <= volume_cc <= hi:
            return int(UTIL_BASE * coeff)
    return int(UTIL_BASE * 2.30)


def calc_reg_fee(age_years: int) -> int:
    if age_years <= 2:
        return int(0.25 * MRP)
    elif age_years <= 3:
        return 25 * MRP
    else:
        return 250 * MRP


BASE_PREMIUM = 1.9 * MRP  # 8 217.5 ₸

CASCO_PROVIDERS = {
    "Halyk Insurance": {"min": 3.5, "max": 5.5, "default": 4.2},
    "Kaspi Insurance": {"min": 3.8, "max": 6.0, "default": 4.8},
    "BCC Insurance":   {"min": 3.2, "max": 5.0, "default": 3.9},
}


def calc_ogpo(region: str, age: int, experience: int, vehicle_age: int, car_type_label: str) -> int:
    """
    car_type_label — первый элемент из tl("tco_car_type_options") означает легковой.
    Определяем коэффициент по позиции в списке.
    """
    regions = td("tco_regions")
    k_region, _ = regions.get(region, (1.0, 5_800))
    k_driver  = 1.0 if (age >= 25 and experience >= 2) else 1.5
    k_vehicle = 1.1 if vehicle_age > 7 else 1.0
    # Первый вариант в radio = легковой/кроссовер
    car_type_options = tl("tco_car_type_options")
    k_type = 2.09 if car_type_label == car_type_options[0] else 2.50
    premium = BASE_PREMIUM * 1.01 * k_region * k_type * k_driver * k_vehicle
    return round(premium)


def is_electric(fuel_label: str) -> bool:
    """Проверяем, является ли выбранное топливо электро (последний элемент списка)."""
    fuel_options = tl("tco_fuel_options")
    return fuel_label == fuel_options[-1]


# ══════════════════════════════════════════════════════════════
def show_tco_calculator():
    st.title(t("tco_title"))
    st.caption(t("tco_caption"))

    car        = st.session_state.get("car_data")
    price_pred = st.session_state.get("predicted_price")

    if car:
        st.success(
            f"{t('tco_from_rec')} "
            f"**{car.get('company','').title()} {car.get('mark','').title()} {car.get('year','')}**"
        )
    if price_pred:
        st.info(f"{t('tco_pred_price')} **{int(price_pred):,} ₸**")

    st.divider()

    # ── Параметры автомобиля 
    st.subheader(t("tco_params"))

    REGIONS           = td("tco_regions")
    INSPECTION_PRICES = td("tco_inspection_prices")

    col_r, col_y, col_v = st.columns(3)
    with col_r:
        region = st.selectbox(t("tco_region"), list(REGIONS.keys()), key="tco_region")
    with col_y:
        year_car = st.number_input(
            t("tco_year"), 1990, 2026,
            value=int(car.get("year", 2020)) if car else 2020,
            key="tco_year"
        )
    with col_v:
        vol_cc = st.number_input(
            t("tco_vol_cc"), 0, 8000,
            value=int((car.get("volume", 2.0) if car else 2.0) * 1000),
            step=100, key="tco_vol_cc",
            help=t("tco_vol_cc_help")
        )

    age_car = 2026 - year_car

    FUEL_OPTIONS = tl("tco_fuel_options")

    _fuel_map = {
        # ru/kk значения
        "бензин": 0, "дизель": 1, "гибрид": 2, "электро": 3,
        # en значения
        "gasoline": 0, "diesel": 1, "hybrid": 2, "electric": 3,
        # capitalize варианты
        "бензин": 0, "Бензин": 0, "Дизель": 1, "Гибрид": 2, "Электро": 3,
        "Gasoline": 0, "Diesel": 1, "Hybrid": 2, "Electric": 3,
    }
    raw_fuel = car.get("fuel_type", "") if car else ""
    default_fuel_idx = _fuel_map.get(raw_fuel.lower() if raw_fuel else "", 0)
    
    default_fuel_idx = min(default_fuel_idx, len(FUEL_OPTIONS) - 1)

    st.divider()

    # ── Таможня 
    include_customs = st.checkbox(t("tco_customs_check"), value=False, key="tco_customs_check")

    total_customs = 0
    car_value_kzt = 0
    total_in_kz   = 0
    fuel_type     = FUEL_OPTIONS[0]  

    if include_customs:
        st.markdown(t("tco_customs_title"))
        st.caption(t("tco_customs_caption"))

        col_u, col_f = st.columns(2)
        with col_u:
            default_price_kzt = int(price_pred) if price_pred else 10_000_000
            car_value_kzt = st.number_input(
                t("tco_car_price"),
                1_000_000, 500_000_000,
                value=default_price_kzt,
                step=100_000,
                key="tco_car_price_kzt"
            )
        with col_f:
            fuel_type = st.selectbox(
                t("tco_fuel"),
                FUEL_OPTIONS,
                index=default_fuel_idx,
                key="tco_fuel_type_customs"
            )
            if is_electric(fuel_type):
                st.info(t("tco_electro_customs"))

        duty         = car_value_kzt * 0.15
        util         = calc_utilsbor(vol_cc, fuel_type)
        reg_fee_cust = calc_reg_fee(age_car)
        customs_fee  = 6 * MRP
        nds_base     = car_value_kzt + duty + util
        nds          = nds_base * 0.16
        total_customs = duty + util + reg_fee_cust + customs_fee + nds
        total_in_kz   = car_value_kzt + total_customs

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric(t("tco_car_price"),  f"{car_value_kzt:,.0f} ₸")
            st.metric(t("tco_duty"),       f"{duty:,.0f} ₸")
            st.metric(t("tco_util"),       f"{util:,.0f} ₸")
        with col_b:
            st.metric(t("tco_nds"),        f"{nds:,.0f} ₸")
            st.metric(t("tco_reg_fee"),    f"{reg_fee_cust:,.0f} ₸")
            st.metric(t("tco_customs_fee"),f"{customs_fee:,.0f} ₸")

        st.success(t("tco_customs_total").format(total_customs))
        st.success(t("tco_total_in_kz").format(total_in_kz))
        st.divider()
    else:
        fuel_type = st.selectbox(
            t("tco_fuel"),
            FUEL_OPTIONS,
            index=default_fuel_idx,
            key="tco_fuel_type_main"
        )
        if is_electric(fuel_type):
            st.info(t("tco_electro_info"))
        st.divider()

    # Кредит
    include_loan = st.checkbox(t("tco_loan_check"), value=False, key="tco_loan_check")

    monthly_loan   = 0.0
    overpayment    = 0.0
    loan_car_price = price_pred if price_pred else (int(total_in_kz) if total_in_kz else 10_000_000)

    if include_loan:
        st.markdown(t("tco_loan_title"))

        c1, c2 = st.columns(2)
        with c1:
            loan_car_price = st.number_input(
                t("tco_car_price"), 1_000_000, 500_000_000,
                value=int(price_pred if price_pred else (total_in_kz if total_in_kz else 10_000_000)),
                step=100_000, key="tco_loan_price"
            )
            down_pct = st.slider(t("tco_down_pct"), 0, 80, 20, key="tco_down")
        with c2:
            loan_rate   = st.slider(t("tco_rate"), 5, 35, 18, key="tco_rate")
            loan_months = st.selectbox(t("tco_months"), [12, 24, 36, 48, 60, 72, 84], index=4, key="tco_months")

        down_amt  = loan_car_price * down_pct / 100
        loan_body = loan_car_price - down_amt
        r         = loan_rate / 100 / 12
        if r > 0:
            monthly_loan = loan_body * (r * (1 + r) ** loan_months) / ((1 + r) ** loan_months - 1)
        else:
            monthly_loan = loan_body / loan_months
        total_loan_pay = monthly_loan * loan_months
        overpayment    = total_loan_pay - loan_body

        col_a, col_b, col_c = st.columns(3)
        col_a.metric(t("tco_monthly"),   f"{monthly_loan:,.0f} ₸")
        col_b.metric(t("tco_overpay"),   f"{overpayment:,.0f} ₸")
        col_c.metric(t("tco_total_pay"), f"{total_loan_pay:,.0f} ₸")
        st.divider()

    # Страхование
    st.subheader(t("tco_insurance"))
    st.markdown(t("tco_ogpo_title"))

    col_o1, col_o2, col_o3 = st.columns(3)
    with col_o1:
        ogpo_driver_age = st.slider(
            t("tco_driver_age"), 18, 80, 35,
            help=t("tco_driver_age_help"),
            key="tco_ogpo_driver_age"
        )
    with col_o2:
        ogpo_experience = st.slider(
            t("tco_experience"), 0, 40, 5,
            key="tco_ogpo_experience"
        )
    with col_o3:
        ogpo_vehicle_age = st.number_input(
            t("tco_vehicle_age"), 0, 50,
            value=max(0, 2026 - year_car),
            key="tco_ogpo_vehicle_age",
            help=t("tco_vehicle_age_help")
        )

    car_type_options = tl("tco_car_type_options")
    ogpo_car_type = st.radio(
        t("tco_car_type_radio"),
        car_type_options,
        horizontal=True,
        key="tco_ogpo_car_type"
    )

    ogpo = calc_ogpo(
        region=region,
        age=ogpo_driver_age,
        experience=ogpo_experience,
        vehicle_age=ogpo_vehicle_age,
        car_type_label=ogpo_car_type
    )

    k_region, _ = REGIONS.get(region, (1.0, 5_800))
    k_driver  = 1.0 if (ogpo_driver_age >= 25 and ogpo_experience >= 2) else 1.5
    k_vehicle = 1.1 if ogpo_vehicle_age > 7 else 1.0

    st.subheader(t("tco_ogpo_result"))
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(t("tco_base_premium"),  f"{BASE_PREMIUM:,.0f} ₸")
    with col2:
        st.metric(t("tco_region_coeff"),  f"{k_region}")
    with col3:
        st.metric(t("tco_ogpo_total"),    f"{ogpo:,} ₸")

    st.success(t("tco_ogpo_success").format(ogpo))
    st.caption(t("tco_ogpo_caption"))

    # КАСКО 
    casco = 0
    include_casco = st.checkbox(t("tco_casco_check"), value=False, key="tco_casco")
    if include_casco:
        maint_price_base_casco = price_pred if price_pred else int(loan_car_price)

        casco_provider = st.radio(
            t("tco_casco_provider"),
            list(CASCO_PROVIDERS.keys()),
            horizontal=True,
            key="tco_casco_provider"
        )
        prov = CASCO_PROVIDERS[casco_provider]

        col_ci, col_cr = st.columns(2)
        with col_ci:
            st.caption(
                f"**{casco_provider}** · {prov['min']}–{prov['max']}% / год · ≈ {prov['default']}%"
            )
        with col_cr:
            casco_rate = st.slider(
                t("tco_casco_rate"),
                prov["min"], prov["max"], prov["default"],
                step=0.1, key="tco_casco_rate"
            )

        casco = int(maint_price_base_casco * casco_rate / 100)
        st.metric(t("tco_casco_year"), f"{casco:,.0f} ₸")

    annual_insurance = ogpo + casco
    st.divider()

    # ТО и ремонт 
    st.subheader(t("tco_maint_title"))

    maint_price_base = price_pred if price_pred else int(loan_car_price)
    MAINT_HINTS = td("maint_hints")

    hint_electro_key = t("maint_hint_electro")
    hint_key = hint_electro_key if is_electric(fuel_type) else list(MAINT_HINTS.keys())[0]

    brand_hint = st.selectbox(
        t("tco_brand_hint"),
        list(MAINT_HINTS.keys()),
        index=list(MAINT_HINTS.keys()).index(hint_key) if hint_key in MAINT_HINTS else 0,
        key="tco_brand_hint"
    )
    lo_h, hi_h, def_h = MAINT_HINTS[brand_hint]
    st.caption(t("tco_maint_caption").format(brand_hint, lo_h, hi_h, def_h))

    maint_rate = st.slider(
        t("tco_maint_rate"),
        1.0, 10.0, float(def_h), step=0.5,
        key="tco_maint_rate"
    )
    maintenance_annual = int(maint_price_base * maint_rate / 100)
    st.metric(t("tco_maint_year"), f"{maintenance_annual:,.0f} ₸")

    st.divider()

    # Транспортный налог и техосмотр
    transport_tax   = calc_transport_tax(vol_cc, fuel_type)
    insp_price_full = INSPECTION_PRICES.get(region, 6_500)

    if age_car < 7:
        inspection_fee       = 0
        inspection_note      = t("insp_not_needed").format(age_car)
        inspection_annual_note = ""
    elif age_car < 15:
        inspection_fee       = insp_price_full // 2
        inspection_note      = t("insp_every2").format(age_car, region, insp_price_full, inspection_fee)
        inspection_annual_note = t("insp_every2_note").format(insp_price_full)
    else:
        inspection_fee       = insp_price_full
        inspection_note      = t("insp_annual").format(age_car, region, insp_price_full)
        inspection_annual_note = t("insp_annual_note")

    col_t, col_i = st.columns(2)
    with col_t:
        if is_electric(fuel_type):
            st.metric(t("tco_tax_electro"), t("tco_tax_electro_val"), help=t("tco_tax_electro_help"))
        else:
            st.metric(t("tco_tax"), f"{transport_tax:,.0f} ₸")
    with col_i:
        st.metric(t("tco_inspection"), f"{inspection_fee:,.0f} ₸", help=inspection_note)

    st.info(inspection_note)

    annual_tax_insp = transport_tax + inspection_fee

    # Итог
    st.divider()

    annual_loan_payment = monthly_loan * 12
    annual_running = (
        annual_tax_insp +
        annual_insurance +
        maintenance_annual +
        annual_loan_payment
    )
    monthly_running = annual_running / 12

    col1, col2 = st.columns(2)
    col1.metric(t("tco_monthly_total"), f"{monthly_running:,.0f} ₸")
    col2.metric(t("tco_annual_total"),  f"{annual_running:,.0f} ₸")

    tco_year = total_customs + int(overpayment) + annual_running

    st.header(t("tco_header").format(annual_running))
    if total_customs > 0 or overpayment > 0:
        st.caption(t("tco_onetime").format(tco_year))

    # Pie Chart
    breakdown_pie = {
        t("tco_pie_tax"):   transport_tax,
        t("tco_pie_insp"):  inspection_fee,
        t("tco_pie_ogpo"):  ogpo,
        t("tco_pie_casco"): casco,
        t("tco_pie_maint"): maintenance_annual,
        t("tco_pie_loan"):  int(annual_loan_payment),
    }
    breakdown_pie = {k: v for k, v in breakdown_pie.items() if v > 0}

    fig = px.pie(
        values=list(breakdown_pie.values()),
        names=list(breakdown_pie.keys()),
        hole=0.42,
        title=t("tco_pie_title").format(annual_running),
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(
        legend=dict(orientation="v", x=1.02, y=0.5),
        margin=dict(t=60, b=20, l=20, r=20),
        height=480,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Детальный breakdown
    with st.expander(t("tco_breakdown")):
        rows = []

        if total_customs > 0:
            rows.append((t("tco_row_customs"), f"{total_customs:,.0f} ₸"))
        if overpayment > 0:
            rows.append((t("tco_row_overpay"), f"{int(overpayment):,.0f} ₸"))

        if transport_tax > 0:
            rows.append((t("tco_row_tax"), f"{transport_tax:,.0f} ₸"))
        else:
            rows.append((t("tco_row_tax"), t("tco_row_tax_electro")))

        insp_label = f"{t('tco_row_insp')} {inspection_annual_note}".strip()
        rows.append((insp_label, f"{inspection_fee:,.0f} ₸"))
        rows.append((t("tco_ogpo_region_row").format(region), f"{ogpo:,.0f} ₸"))
        if casco > 0:
            rows.append((t("tco_casco_year"), f"{casco:,.0f} ₸"))
        rows.append((t("tco_row_maint").format(maint_rate), f"{maintenance_annual:,.0f} ₸"))
        if annual_loan_payment > 0:
            rows.append((t("tco_row_loan"), f"{int(annual_loan_payment):,.0f} ₸"))

        rows.append((t("tco_row_annual"), f"**{annual_running:,.0f} ₸**"))
        if tco_year != annual_running:
            rows.append((t("tco_row_tco"), f"**{tco_year:,.0f} ₸**"))

        st.table({
            t("tco_table_col1"): [r[0] for r in rows],
            t("tco_table_col2"): [r[1] for r in rows],
        })

    # Навигация
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button(t("tco_to_rec")):
            st.session_state["page_key"] = "nav_rec"
            st.rerun()
    with col2:
        if st.button(t("tco_to_price")):
            st.session_state["page_key"] = "nav_price"
            st.rerun()
    with col3:
        if st.button(t("tco_reset")):
            st.session_state.car_data        = None
            st.session_state.predicted_price = None
            st.rerun()
