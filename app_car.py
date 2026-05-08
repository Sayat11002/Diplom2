import streamlit as st
from car1_recommendation import show_car_recommendation
from price2_prediction import show_price_prediction
from tco1_calculator import show_tco_calculator
from translations import t, TEXTS
from datetime import datetime
from supabase import create_client

st.set_page_config(page_title="Car Assistant Pro", layout="wide")


# ====================== SUPABASE ======================
@st.cache_resource
def get_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def load_reviews():
    try:
        db = get_supabase()
        result = db.table("reviews").select("*").order("date", desc=True).execute()
        return result.data  # список словарей [{"date":..., "rating":..., "review":...}]
    except Exception as e:
        st.error(f"Ошибка загрузки отзывов: {e}")
        return []


def save_review(date: str, rating: int, review: str) -> bool:
    try:
        db = get_supabase()
        db.table("reviews").insert({
            "date": date,
            "rating": rating,
            "review": review
        }).execute()
        return True
    except Exception as e:
        st.error(f"Ошибка сохранения: {e}")
        return False


# ====================== СТИЛИ ======================
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


# ====================== ОТЗЫВЫ ======================
def show_home_reviews():
    st.divider()

    st.markdown("""
    <style>
    .reviews-header { font-size:1.5rem; font-weight:700; color:#1a2b3c; margin-bottom:4px; }
    .reviews-subline { color:#627d98; font-size:0.92rem; margin-bottom:20px; }
    .review-card {
        background:#ffffff; border:1px solid #e2eaf2; border-radius:14px;
        padding:18px 22px; margin-bottom:14px;
        box-shadow:0 2px 8px rgba(36,59,83,0.06);
    }
    .review-card:hover { box-shadow:0 4px 18px rgba(36,59,83,0.13); }
    .review-top { display:flex; justify-content:space-between; margin-bottom:8px; }
    .review-stars { font-size:1.1rem; letter-spacing:2px; }
    .review-date { font-size:0.78rem; color:#9fb3c8; font-family:monospace; }
    .review-text { font-size:0.97rem; color:#334e68; line-height:1.6; }
    .avg-badge {
        display:inline-block;
        background:linear-gradient(135deg,#243B53,#334E68);
        color:white; border-radius:30px; padding:6px 20px;
        font-size:1.05rem; font-weight:600; margin-bottom:18px;
    }
    .no-reviews { color:#9fb3c8; font-style:italic; text-align:center; padding:20px 0; }
    .form-section {
        background:#f0f4f8; border-radius:14px;
        padding:20px 24px; margin-bottom:24px; border:1px solid #d9e2ec;
    }
    .star-label { font-size:0.9rem; color:#627d98; margin-bottom:8px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="reviews-header">{t("reviews_title")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="reviews-subline">Ваше мнение помогает нам становиться лучше</div>',
                unsafe_allow_html=True)

    # ── Инициализация рейтинга ──
    if "star_rating" not in st.session_state:
        st.session_state["star_rating"] = 5

    # ── Форма ──
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    st.markdown('<div class="star-label">Ваша оценка:</div>', unsafe_allow_html=True)

    # 5 звёздочек-кнопок
    star_cols = st.columns(10)
    current = st.session_state["star_rating"]
    for i in range(1, 6):
        with star_cols[i - 1]:
            star_char = "⭐" if i <= current else "☆"
            if st.button(star_char, key=f"star_{i}",
                         help=f"{i} звезд{'а' if i == 1 else 'ы' if i < 5 else ''}"):
                st.session_state["star_rating"] = i
                st.rerun()

    rating = st.session_state["star_rating"]
    st.caption(f"Выбрано: {'⭐' * rating} ({rating} из 5)")

    review_text = st.text_area(
        t("reviews_text"),
        placeholder=t("reviews_placeholder"),
        height=100,
        key="home_review"
    )

    if st.button(t("reviews_send"), type="primary", key="send_review"):
        if review_text.strip():
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            ok = save_review(date_str, rating, review_text.strip())
            if ok:
                st.success(t("reviews_success"))
                st.session_state["star_rating"] = 5
                st.rerun()
        else:
            st.warning(t("reviews_warning"))

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Список отзывов из Supabase ──
    records = load_reviews()

    if records:
        ratings = [r["rating"] for r in records]
        avg = sum(ratings) / len(ratings)
        full_stars = int(round(avg))
        st.markdown(
            f'<div class="avg-badge">{"⭐" * full_stars} {avg:.1f} / 5 &nbsp;·&nbsp; {len(records)} отзывов</div>',
            unsafe_allow_html=True
        )
        for row in records:  # уже отсортированы desc по date
            stars = "⭐" * int(row.get("rating", 5))
            date_str = str(row.get("date", ""))
            text = str(row.get("review", ""))
            st.markdown(f"""
            <div class="review-card">
                <div class="review-top">
                    <span class="review-stars">{stars}</span>
                    <span class="review-date">{date_str}</span>
                </div>
                <div class="review-text">{text}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-reviews">Пока отзывов нет. Будьте первым!</div>',
                    unsafe_allow_html=True)


# ====================== SESSION STATE ======================
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
    "ru": "Cars_Dataset3.csv",
    "kk": "cars_dataset_kk.csv",
    "en": "Cars_dataset_en.csv",
}

PAGE_KEYS = ["nav_rec", "nav_price", "nav_tco"]
WELCOME_KEY = "welcome"


def set_page(page_key: str):
    st.session_state["page_key"] = page_key
    st.rerun()


if "page_key" not in st.session_state:
    st.session_state["page_key"] = WELCOME_KEY


# ====================== ЯЗЫК ======================
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


# ====================== РОУТИНГ ======================
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
    show_home_reviews()

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
