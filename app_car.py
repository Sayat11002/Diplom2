import streamlit as st
from car1_recommendation import show_car_recommendation
from price1_prediction import show_price_prediction
from tco1_calculator import show_tco_calculator
from translations import t, TEXTS

st.set_page_config(page_title="Car Assistant Pro", layout="wide")


def apply_global_styles():
    st.markdown("""
    <style>
    .stApp {
        background-color: #F0F4F8;
    }
    div.stButton > button {
        background-color: #243B53;
        color: #FFFFFF;
        border-radius: 6px;
        border: none;
        padding: 0.6rem 1.2rem;
        font-weight: 400;
    }
    div.stButton > button:hover {
        background-color: #334E68;
        color: #FFFFFF;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    section[data-testid="stSidebar"] {
        background-color: #D9E2EC;
    }
    </style>
    """, unsafe_allow_html=True)


apply_global_styles()

if "lang" not in st.session_state:
    st.session_state["lang"] = "ru"

if "page" not in st.session_state:
    st.session_state.page = t("welcome")

if "car_data" not in st.session_state:
    st.session_state.car_data = None

if "predicted_price" not in st.session_state:
    st.session_state.predicted_price = None

if st.session_state.car_data is not None:
    st.session_state.car_data.setdefault("fuel_type", "Бензин")
    st.session_state.car_data.setdefault("volume", 2.0)

DATASET_PATH = {
    "ru": r"C:\Users\Саят\Downloads\Cars_Dataset3.csv",
    "kk": r"C:\Users\Саят\Downloads\cars_dataset_kk.csv",
    "en": r"C:\Users\Саят\Downloads\Cars_dataset_en.csv",
}

PAGE_KEYS = ["nav_rec", "nav_price", "nav_tco"]
WELCOME_KEY = "welcome"


def set_page(page_key: str):
    st.session_state["page_key"] = page_key
    st.rerun()


if "page_key" not in st.session_state:
    st.session_state["page_key"] = WELCOME_KEY


selected_lang = st.sidebar.selectbox(
    "🌐 Язык / Тіл / Language",
    ["ru", "kk", "en"],
    format_func=lambda x: {"ru": "Русский", "kk": "Қазақша", "en": "English"}[x],
    index=["ru", "kk", "en"].index(st.session_state["lang"]),
    key="lang_selector"
)


if selected_lang != st.session_state["lang"]:
    st.session_state["lang"] = selected_lang
    
    st.session_state.car_data = None
    st.session_state.predicted_price = None
    st.session_state.pop("pp_results", None)
    st.session_state.pop("ai_recommendations", None)
    st.rerun()


st.session_state["dataset_path"] = DATASET_PATH[st.session_state["lang"]]


if st.session_state["page_key"] == WELCOME_KEY:
    st.title(t("app_title"))
    st.markdown(f"### {t('all_modules')}")

    col1, col2, col3 = st.columns(3, gap="large")
    with col1:
        st.info(f"### 1. {t('nav_rec')}")
        if st.button(t("open_rec"), use_container_width=True):
            set_page("nav_rec")
    with col2:
        st.success(f"### 2. {t('nav_price')}")
        if st.button(t("open_price"), use_container_width=True):
            set_page("nav_price")
    with col3:
        st.warning(f"### 3. {t('nav_tco')}")
        if st.button(t("open_tco"), use_container_width=True):
            set_page("nav_tco")


else:
    if st.sidebar.button(t("back_home")):
        set_page(WELCOME_KEY)

    st.sidebar.title(t("nav_title"))

    
    page_labels = [t(k) for k in PAGE_KEYS]
    current_label = t(st.session_state["page_key"]) if st.session_state["page_key"] in PAGE_KEYS else page_labels[0]

    if current_label not in page_labels:
        current_label = page_labels[0]

    selection_label = st.sidebar.radio(
        t("nav_select"),
        page_labels,
        index=page_labels.index(current_label),
    )

    
    selected_key = PAGE_KEYS[page_labels.index(selection_label)]
    st.session_state["page_key"] = selected_key

    
    if selected_key == "nav_rec":
        show_car_recommendation()
    elif selected_key == "nav_price":
        show_price_prediction()
    elif selected_key == "nav_tco":
        show_tco_calculator()
