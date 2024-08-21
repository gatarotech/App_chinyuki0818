import streamlit as st
import pandas as pd
import datetime
import os
import googlemaps
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# APIキーの設定
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
gmaps = googlemaps.Client(key=API_KEY) if API_KEY else None

# 日本語の曜日を取得する関数
def get_japanese_weekday(date):
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    return weekdays[date.weekday()]

# 画像とテキストのオプション（リスト内の辞書）
options = {
    "会社の固い宴会": {"description": "正式な会社の宴会", "image": "./img/item01.png"},
    "会社の同僚との気さくな宴会": {"description": "同僚と楽しく過ごす宴会", "image": "./img/image2.png"},
    "合コン": {"description": "新しい出会いの場", "image": "./img/image3.png"},
    "友人との遊び": {"description": "友人と気軽に楽しむ", "image": "./img/image4.png"},
}

# 選択を管理する変数
if "selected_event" not in st.session_state:
    st.session_state.selected_event = None

if "dates" not in st.session_state:
    st.session_state.dates = []


# 選択肢を表示する関数
def custom_select(label, options):
    selected_value = st.session_state.selected_event
    cols = st.columns(len(options))

    for i, (key, value) in enumerate(options.items()):
        with cols[i]:
            if st.button(f"{key}", key=f"{key}_btn"):
                selected_value = key
                st.session_state.selected_event = key
            # 選択されているかどうかを判定してCSSクラスを適用
            selected_class = "selected" if key == selected_value else ""
            st.markdown(f"""
                <div class="select-img {selected_class}">
                    <img src="{value['image']}" alt="{key}">
                    <div>{key}</div>
                    <div style="font-size:small;">{value['description']}</div>
                </div>
                """, unsafe_allow_html=True)

    return selected_value

# サイドバーでナビゲーションメニューを作成
st.sidebar.title("メニュー")
section = st.sidebar.radio("セクションを選択してください", ["幹事の設定", "メンバーの入力", "結果の確認"])

# 幹事の設定セクション
if section == "幹事の設定":
    st.header("幹事の設定")

    # 会の趣旨セクション
    st.header("会の趣旨を選択してください")

    # カスタム選択肢の結果を取得
    event_type = custom_select("宴会の目的", options)

    # 選択された値を表示
    if event_type:
        st.write(f"選択された会の趣旨: {event_type}")

    st.subheader("日程候補の入力")

    # カレンダーから日付を選択して追加
    new_date = st.date_input("日程を選択してください", value=datetime.date.today())
    if st.button("日程を追加"):
        if new_date not in st.session_state.dates:
            st.session_state.dates.append(new_date)

    # 選択された日程候補を表示
    if st.session_state.dates:
        st.markdown("### 選択された日程候補")
        for date in st.session_state.dates:
            day_of_week = get_japanese_weekday(date)
            st.write(f"{date.strftime('%Y/%m/%d')} ({day_of_week}曜日)")

# メンバーの入力セクション
if section == "メンバーの入力":
    st.header("メンバーの入力")

    if "members" not in st.session_state:
        st.session_state.members = []

    def add_member():
        st.session_state.members.append({
            "name": "",
            "availability": {date: "" for date in st.session_state.dates},
            "location": "",
            "hobbies": [],
            "favorite_foods": []
        })

    if st.button("＋ メンバーを追加"):
        add_member()

    # 趣味と好きな食べ物の選択肢
    hobbies_options = ["スポーツ", "ゲーム", "読書", "映画", "音楽", "旅行"]
    food_options = ["和食", "イタリアン", "中華", "フレンチ", "焼肉", "寿司", "カレー", "ラーメン"]

    for i, member in enumerate(st.session_state.members):
        st.subheader(f"メンバー {i + 1} の入力")
        st.session_state.members[i]["name"] = st.text_input("メンバーの名前", key=f"name_{i}")

        for date in st.session_state.dates:
            st.session_state.members[i]["availability"][date] = st.radio(
                f"{date.strftime('%Y-%m-%d')} ({get_japanese_weekday(date)}) の出欠を選んでください ({member['name']})", 
                ["○", "×", "△"], 
                key=f"availability_{i}_{date}"
            )

        st.session_state.members[i]["location"] = st.text_input("自宅からの最寄り駅", key=f"location_{i}")

        st.session_state.members[i]["hobbies"] = st.multiselect(
            "趣味を選んでください", 
            hobbies_options, 
            key=f"hobbies_{i}"
        )

        st.session_state.members[i]["favorite_foods"] = st.multiselect(
            "好きな食べ物を選んでください", 
            food_options, 
            key=f"favorite_foods_{i}"
        )

if section == "結果の確認":
    st.header("入力内容の確認")

    # 出欠の集計
    attendance_summary = {date: {"○": 0, "×": 0, "△": 0} for date in st.session_state.dates}

    for member in st.session_state.members:
        for date, attendance in member["availability"].items():
            if attendance:
                attendance_summary[date][attendance] += 1

    # 集計結果をテーブルで表示し、ユーザーが日程を選択できるようにする
    st.subheader("出欠状況と日程の選択")

    # DataFrameで集計結果を表示
    attendance_df = pd.DataFrame([
        {
            "日程": date.strftime('%Y-%m-%d'),
            "曜日": get_japanese_weekday(date),
            "○": summary["○"],
            "×": summary["×"],
            "△": summary["△"]
        } for date, summary in attendance_summary.items()
    ])

    st.table(attendance_df)

    # ユーザーが日程を選択できるセクション
    selected_date = st.selectbox("最適な日程を選んでください", options=attendance_summary.keys(), format_func=lambda date: f"{date.strftime('%Y-%m-%d')} ({get_japanese_weekday(date)}曜日)")

    if selected_date:
        st.write(f"選択された日程: {selected_date.strftime('%Y-%m-%d')} ({get_japanese_weekday(selected_date)}曜日)")


    # メンバーごとの好みや制約を表示
    st.subheader("メンバーの好みや制約")
    for member in st.session_state.members:
        st.write(f"**{member['name']}**")
        st.write(f"自宅からの最寄り駅: {member['location']}")
        st.write(f"趣味: {', '.join(member['hobbies'])}")
        st.write(f"好きな食べ物: {', '.join(member['favorite_foods'])}")
        st.write("---")

    # 飲食店の検索と表示
    st.header("最適な飲食店を探す")
    if st.button("飲食店を探す"):
        if st.session_state.members and gmaps:
            try:
                locations = [
                    gmaps.geocode(member['location'])[0]['geometry']['location']
                    for member in st.session_state.members if member['location']
                ]
                if locations:
                    avg_lat = sum(location['lat'] for location in locations) / len(locations)
                    avg_lng = sum(location['lng'] for location in locations) / len(locations)

                    places_result = gmaps.places_nearby(
                        location=(avg_lat, avg_lng), radius=1000, type='restaurant', open_now=True
                    )

                    if places_result['results']:
                        sorted_places = sorted(
                            places_result['results'],
                            key=lambda x: x.get('rating', 0),
                            reverse=True
                        )
                        st.write("点数の高い飲食店の候補:")
                        for place in sorted_places[:5]:
                            place_name = place['name']
                            vicinity = place['vicinity']
                            st.write(f"{place_name} - {vicinity}")
                    else:
                        st.write("適切な飲食店が見つかりませんでした。")
                else:
                    st.write("メンバーの最寄り駅の情報が不足しています。")
            except Exception as e:
                st.error(f"飲食店の検索中にエラーが発生しました: {e}")
        else:
            st.write("メンバーの情報が不足しています。")
