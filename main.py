import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# -----------------------------------------------
# 1. 페이지 설정 및 따뜻한 색상 테마
# -----------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏡",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFF9F2;
    }

    h1, h2, h3 {
        color: #70452F;
    }

    div[data-testid="stSelectbox"] label {
        color: #70452F;
        font-weight: 600;
    }

    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #EEDCCB;
        border-radius: 14px;
        padding: 18px;
    }

    div[data-testid="stMetricLabel"] {
        color: #70452F;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏡 동네별 인구 피라미드")
st.write(
    "우리 동네에는 어떤 연령대가 많이 살고 있을까요? "
    "지역을 선택해 남녀별 인구 구성과 주요 인구 지표를 살펴보세요."
)

# -----------------------------------------------
# 2. 데이터 불러오기
# -----------------------------------------------
DATA_URL = (
    "https://raw.githubusercontent.com/"
    "snow2hite-ui/population-dashboard/main/"
    "population_ts_yearly_gender.zip"
)


@st.cache_data(show_spinner="인구 데이터를 불러오는 중입니다...")
def load_data():
    # ZIP 파일을 pandas로 직접 읽습니다.
    df = pd.read_csv(DATA_URL, compression="zip")

    # 열 이름의 불필요한 공백을 제거합니다.
    df.columns = df.columns.astype(str).str.strip()

    # 연도를 숫자로 변환합니다.
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df = df.dropna(subset=["연도"])
    df["연도"] = df["연도"].astype(int)

    # 0세부터 100세 이상까지 나이 라벨을 생성합니다.
    ages = [f"{age}세" for age in range(100)] + ["100세 이상"]

    # 남녀 인구 열 이름을 생성합니다.
    male_cols = [f"남_{age}" for age in ages]
    female_cols = [f"여_{age}" for age in ages]

    # 필요한 열이 모두 있는지 확인합니다.
    required_cols = [
        "연도",
        "시도",
        "시군구",
        "동",
        *male_cols,
        *female_cols,
    ]

    missing_cols = [
        col for col in required_cols if col not in df.columns
    ]

    if missing_cols:
        raise ValueError(
            "CSV에 필요한 열이 없습니다: "
            + ", ".join(missing_cols[:10])
        )

    # 인구 데이터를 숫자로 변환합니다.
    for col in male_cols + female_cols:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        ).fillna(0)

    # 지역 이름을 문자열로 통일합니다.
    for col in ["시도", "시군구", "동"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df, ages, male_cols, female_cols


try:
    df, ages, male_cols, female_cols = load_data()
except Exception as e:
    st.error("인구 데이터를 불러오지 못했습니다.")
    st.exception(e)
    st.stop()

# -----------------------------------------------
# 3. 최신 연도 데이터만 선택
# -----------------------------------------------
latest_year = int(df["연도"].max())

latest_df = df[df["연도"] == latest_year].copy()

st.caption(f"📅 분석 기준 연도: {latest_year}년")

# -----------------------------------------------
# 4. 시도 → 시군구 → 동 선택
# -----------------------------------------------
st.subheader("📍 우리 동네 선택")

col1, col2, col3 = st.columns(3)

# 첫 번째: 시도
with col1:
    sido_list = sorted(
        latest_df.loc[
            latest_df["시도"] != "", "시도"
        ].unique()
    )

    if not sido_list:
        st.error("선택할 수 있는 시도 데이터가 없습니다.")
        st.stop()

    selected_sido = st.selectbox("① 시도", sido_list)

# 선택한 시도에 해당하는 데이터만 남깁니다.
sido_df = latest_df[
    latest_df["시도"] == selected_sido
]

# 두 번째: 시군구
with col2:
    sigungu_list = sorted(
        sido_df.loc[
            sido_df["시군구"] != "", "시군구"
        ].unique()
    )

    if not sigungu_list:
        st.error("해당 시도에 시군구 데이터가 없습니다.")
        st.stop()

    selected_sigungu = st.selectbox(
        "② 시군구",
        sigungu_list,
    )

# 선택한 시군구에 해당하는 데이터만 남깁니다.
sigungu_df = sido_df[
    sido_df["시군구"] == selected_sigungu
]

# 세 번째: 동
with col3:
    dong_list = sorted(
        sigungu_df.loc[
            sigungu_df["동"] != "", "동"
        ].unique()
    )

    if not dong_list:
        st.error("해당 시군구에 동 데이터가 없습니다.")
        st.stop()

    selected_dong = st.selectbox("③ 동", dong_list)

# -----------------------------------------------
# 5. 선택한 동네의 연령별 인구 계산
# -----------------------------------------------
selected_df = sigungu_df[
    sigungu_df["동"] == selected_dong
]

# 같은 지역에 행이 여러 개 있으면 연령별로 합산합니다.
male_original = (
    selected_df[male_cols]
    .sum()
    .to_numpy(dtype=float)
)

female_population = (
    selected_df[female_cols]
    .sum()
    .to_numpy(dtype=float)
)

# 남녀를 합친 연령별 인구입니다.
age_population = male_original + female_population

# 전체 인구와 남녀 인구를 계산합니다.
total_population = int(age_population.sum())
male_total = int(male_original.sum())
female_total = int(female_population.sum())

# -----------------------------------------------
# 6. 총인구, 평균연령, 고령화율 계산
# -----------------------------------------------

# 연령별 대표 나이를 숫자로 만듭니다.
# 100세 이상은 계산 편의를 위해 100세로 간주합니다.
age_numbers = list(range(100)) + [100]

# 평균연령 = 각 나이 × 해당 나이 인구의 합 / 전체 인구
if total_population > 0:
    average_age = (
        sum(
            age * population
            for age, population in zip(
                age_numbers,
                age_population,
            )
        )
        / total_population
    )
else:
    average_age = 0.0

# 65세 이상 인구를 계산합니다.
# 인덱스 65부터 100세 이상까지가 65세 이상입니다.
elderly_population = int(age_population[65:].sum())

# 고령화율 = 65세 이상 인구 / 전체 인구 × 100
if total_population > 0:
    aging_rate = (
        elderly_population / total_population * 100
    )
else:
    aging_rate = 0.0

# 0~14세 인구를 계산합니다.
children_population = int(age_population[:15].sum())

# 0~14세와 65세 이상 인구의 비율도 계산합니다.
if total_population > 0:
    children_rate = (
        children_population / total_population * 100
    )
    elderly_rate = (
        elderly_population / total_population * 100
    )
else:
    children_rate = 0.0
    elderly_rate = 0.0

# -----------------------------------------------
# 7. 지표 카드 3개
# -----------------------------------------------
st.divider()

st.subheader(
    f"📊 {selected_sido} {selected_sigungu} {selected_dong}"
)

card1, card2, card3 = st.columns(3)

# 카드 1: 총인구
with card1:
    st.metric(
        label="👥 총인구",
        value=f"{total_population:,}명",
        help="선택한 동네의 남녀 전체 인구입니다.",
    )

# 카드 2: 평균연령
with card2:
    st.metric(
        label="🎂 평균연령",
        value=f"{average_age:.1f}세",
        help=(
            "연령별 인구를 가중 평균한 값입니다. "
            "100세 이상은 계산상 100세로 처리합니다."
        ),
    )

# 카드 3: 고령화율
with card3:
    # 고령화율이 20%를 초과하면 카드에 주의 표시를 붙입니다.
    if aging_rate > 20:
        aging_label = "👵 고령화율 ⚠️ 주의"
    else:
        aging_label = "👵 고령화율"

    st.metric(
        label=aging_label,
        value=f"{aging_rate:.1f}%",
        help=(
            "전체 인구 중 65세 이상 인구의 비율입니다. "
            "20%를 초과하면 주의 표시가 나타납니다."
        ),
    )

# 카드 바로 아래에 추가 안내를 표시합니다.
if aging_rate > 20:
    st.warning(
        f"⚠️ 고령화율이 {aging_rate:.1f}%로 "
        "20%를 초과합니다. 65세 이상 인구 비중이 높은 동네입니다."
    )

# -----------------------------------------------
# 8. 인구 피라미드 그리기
# -----------------------------------------------
st.subheader("📈 연령별 남녀 인구 피라미드")

# 남성은 음수로 바꿔 왼쪽에 표시합니다.
male_population = -male_original

fig = go.Figure()

# 남성 막대
fig.add_trace(
    go.Bar(
        x=male_population,
        y=ages,
        name="남성",
        orientation="h",
        marker_color="#7299C6",
        customdata=-male_population,
        hovertemplate=(
            "나이: %{y}<br>"
            "남성 인구: %{customdata:,.0f}명"
            "<extra></extra>"
        ),
    )
)

# 여성 막대
fig.add_trace(
    go.Bar(
        x=female_population,
        y=ages,
        name="여성",
        orientation="h",
        marker_color="#E99A91",
        hovertemplate=(
            "나이: %{y}<br>"
            "여성 인구: %{x:,.0f}명"
            "<extra></extra>"
        ),
    )
)

# 좌우 축을 대칭으로 설정합니다.
max_population = max(
    float(abs(male_population).max()),
    float(female_population.max()),
    1.0,
)

axis_limit = max_population * 1.12

fig.update_layout(
    title=dict(
        text=f"{selected_dong} 연령별 남녀 인구",
        x=0.5,
        xanchor="center",
        font=dict(size=22, color="#70452F"),
    ),
    barmode="overlay",
    bargap=0.12,
    height=850,
    paper_bgcolor="#FFF9F2",
    plot_bgcolor="#FFF9F2",
    font=dict(
        family="sans-serif",
        color="#59483D",
        size=12,
    ),
    margin=dict(l=80, r=40, t=90, b=65),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.01,
        xanchor="center",
        x=0.5,
    ),
    xaxis=dict(
        title="인구수 (명)",
        range=[-axis_limit, axis_limit],
        zeroline=True,
        zerolinewidth=2,
        zerolinecolor="#B9A99B",
        showgrid=True,
        gridcolor="#EDE1D5",
        tickformat=",.0f",

        # 왼쪽 남성 인구의 음수 눈금도 양수로 표시합니다.
        tickvals=[
            -axis_limit,
            -axis_limit * 0.5,
            0,
            axis_limit * 0.5,
            axis_limit,
        ],
        ticktext=[
            f"{axis_limit:,.0f}",
            f"{axis_limit * 0.5:,.0f}",
            "0",
            f"{axis_limit * 0.5:,.0f}",
            f"{axis_limit:,.0f}",
        ],
    ),
    yaxis=dict(
        title="나이",
        type="category",

        # 나이 라벨을 지정된 순서 그대로 사용합니다.
        categoryorder="array",
        categoryarray=ages,
        tickmode="array",
        tickvals=ages,
        ticktext=ages,

        # 축 반전 옵션을 사용하지 않습니다.
        # categoryarray의 순서대로 0세가 아래,
        # 100세 이상이 위에 오도록 고정합니다.
        showgrid=False,
        automargin=True,
    ),
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------
# 9. 동네 특성 한 줄 자동 설명
# -----------------------------------------------
st.subheader("💬 우리 동네 한눈에 보기")

if total_population == 0:
    st.info(
        "인구 데이터가 없어 동네의 연령별 특성을 "
        "판단할 수 없습니다."
    )
elif children_rate > elderly_rate:
    st.success(
        f"🧒 이 동네는 아이가 많은 편이에요! "
        f"0~14세 인구는 {children_population:,}명"
        f"({children_rate:.1f}%), "
        f"65세 이상 인구는 {elderly_population:,}명"
        f"({elderly_rate:.1f}%)입니다."
    )
elif elderly_rate > children_rate:
    st.info(
        f"👵 이 동네는 어르신이 많은 편이에요. "
        f"65세 이상 인구는 {elderly_population:,}명"
        f"({elderly_rate:.1f}%), "
        f"0~14세 인구는 {children_population:,}명"
        f"({children_rate:.1f}%)입니다."
    )
else:
    st.info(
        f"⚖️ 이 동네는 아이와 어르신의 비율이 같아요. "
        f"두 연령대 모두 {children_rate:.1f}%입니다."
    )

# -----------------------------------------------
# 10. 그래프 읽는 방법
# -----------------------------------------------
with st.expander("💡 인구 피라미드 읽는 방법"):
    st.markdown(
        """
        - **왼쪽 파란색:** 남성 인구
        - **오른쪽 분홍색:** 여성 인구
        - **막대 길이:** 해당 연령대의 인구 규모
        - **세로축 아래:** 0세
        - **세로축 위:** 100세 이상
        - **고령화율:** 전체 인구 중 65세 이상 인구의 비율
        - **주의 표시:** 고령화율이 20%를 초과하면 표시
        """
    )

st.caption(
    "데이터 출처: snow2hite-ui/population-dashboard · "
    f"{latest_year}년 최신 수록 자료 기준"
)
