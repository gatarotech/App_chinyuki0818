import streamlit as st
import pandas as pd
import datetime
import calendar
import os
import openai
import googlemaps
import requests
from collections import Counter
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# APIキーの設定
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
gmaps = googlemaps.Client(key=API_KEY)
openai.api_key = os.getenv("OPEN_API_KEY")

# 日本語の曜日を取得する関数
def get_japanese_weekday(date):
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    return weekdays[date.weekday()]

# ChatGPTにゲームを提案させる関数
def suggest_game(event_type):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # または最新のモデルを指定
            messages=[
                {"role": "system", "content": "飲み会の幹事として、参加者を楽しませて"},
                {"role": "user", "content": f"会の趣旨は「{event_type}」です。ゲームを提案してください。"}
            ]
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return f"エラーが発生しました: {e}"

# 天気予報を取得する関数
def get_weather_forecast(date, location):
    city_code_list = {
        "東京都": "130010",  # 必要に応じて都市コードを追加
        "大阪": "270000",
    }
    
    # locationに基づいて都市コードを取得
    city_code = city_code_list.get(location, "130010")
    
    url = f"https://weather.tsukumijima.net/api/forecast/city/{city_code}"
    response = requests.get(url)
    
    if response.status_code != 200:
        return "天気情報を取得できませんでした"

    weather_json = response.json()
    
    # 日付がAPIのサポート範囲内かをチェック
    today = datetime.date.today()
    days_diff = (date - today).days
    
    if days_diff < 0 or days_diff >= len(weather_json['forecasts']):
        return "指定された日付の天気情報は取得できません"
    
    forecast = weather_json['forecasts'][days_diff]
    
    return forecast['telop']

# 天気による面白いひと言を生成する関数
def get_weather_message(weather):
    if "晴" in weather:
        return "太陽も祝福しているよ！ビールが一層美味しくなりそうだね。"
    elif "雨" in weather:
        return "雨が降っても気にしない！素敵な傘でおしゃれに決めちゃおう。"
    elif "曇" in weather:
        return "曇り空でも気分は晴れやかに！楽しい時間が待っているよ。"
    else:
        return "どんな天気でも楽しい時間が約束されているよ！"

# メインのアプリケーション
def main():

    # サイドバーでナビゲーションメニューを作成
    st.sidebar.title("メニュー")
    section = st.sidebar.radio("セクションを選択してください", ["幹事の設定", "メンバーの入力", "結果の確認"])

    # 幹事の設定セクション
    if section == "幹事の設定":
        st.header("幹事の設定")
        st.subheader("日程候補の入力")

        if "dates" not in st.session_state:
            st.session_state.dates = []

        # カレンダーから日付を選択して追加
        new_date = st.date_input("日程を選択してください", value=datetime.date.today())
        if st.button("日程を追加"):
            if new_date not in st.session_state.dates:
                st.session_state.dates.append(new_date)
        
        st.write("選択された日程候補:", st.session_state.dates)

        # 会の趣旨セクション
        st.header("会の趣旨を選択してください")
        purposes = ("会社の固い宴会", "会社の同僚との気さくな宴会", "合コン", "友人との遊び")
        event_type = st.selectbox("宴会の目的", purposes)
        st.session_state.event_type = event_type

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

    # 結果の確認セクション
    if section == "結果の確認":
        st.header("入力内容の確認")

        # 出欠の集計
        attendance_summary = {date: {"○": 0, "×": 0, "△": 0} for date in st.session_state.dates}

        for member in st.session_state.members:
            for date, attendance in member["availability"].items():
                if attendance:
                    attendance_summary[date][attendance] += 1

        # 集計結果をテーブルで表示
        attendance_df = pd.DataFrame([
            {
                "日程": date.strftime('%Y-%m-%d'),
                "曜日": get_japanese_weekday(date),
                "○": summary["○"],
                "×": summary["×"],
                "△": summary["△"]
            } for date, summary in attendance_summary.items()
        ])

        st.write(attendance_df)

        # 日時を幹事が選択するための入力フィールドを追加
        selected_date = st.date_input("最適な日程を選択してください", value=datetime.date.today() + datetime.timedelta(days=7))
        st.session_state.selected_date = selected_date

        # メンバーごとの好みや制約を表示
        st.subheader("メンバーの好みや制約")
        members_data = {}
        for member in st.session_state.members:
            members_data[member['name']] = {
                "availability": member["availability"].items(),
                "location": member["location"],
                "hobbies": member["hobbies"],
                "favorite_foods": member["favorite_foods"]
            }
            st.write(f"**{member['name']}**")
            st.write(f"自宅からの最寄り駅: {member['location']}")
            st.write(f"趣味: {', '.join(member['hobbies'])}")
            st.write(f"好きな食べ物: {', '.join(member['favorite_foods'])}")
            st.write("---")

        # 会の趣旨を表示
        if "event_type" in st.session_state:
            st.write("**会の趣旨:**", st.session_state.event_type)

        st.write("**集約されたメンバーのデータ:**", members_data)

        # 飲食店の検索と表示
        st.header("最適な飲食店を探す")
        if st.button("飲食店を探す"):
            if st.session_state.members:
                all_dates = [date for member in st.session_state.members for date in member['availability'] if member['availability'][date] == "○"]
                if all_dates:
                    date_counts = Counter(all_dates)
                    optimal_date = max(date_counts, key=date_counts.get)
                    st.session_state.optimal_date = optimal_date

                    try:
                        locations = [
                            gmaps.geocode(member['location'])[0]['geometry']['location']
                            for member in st.session_state.members if member['location']
                        ]
                        if locations:
                            avg_lat = sum(location['lat'] for location in locations) / len(locations)
                            avg_lng = sum(location['lng'] for location in locations) / len(locations)
                            st.session_state.avg_location = (avg_lat, avg_lng)

                            places_result = gmaps.places_nearby(
                                location=(avg_lat, avg_lng), radius=1000, type='restaurant', open_now=True
                            )

                            if places_result['results']:
                                sorted_places = sorted(
                                    places_result['results'],
                                    key=lambda x: x.get('rating', 0),
                                    reverse=True
                                )
                                st.session_state.place_names = []
                                for place in sorted_places[:5]:
                                    details = gmaps.place(place_id=place['place_id'])
                                    website = details.get('result', {}).get('website')
                                    st.session_state.place_names.append({
                                        'name': place['name'],
                                        'vicinity': place['vicinity'],
                                        'place_id': place['place_id'],
                                        'url': website if website else "公式サイトなし"
                                    })
                                st.write("点数の高い飲食店の候補:")
                                for place in st.session_state.place_names:
                                    url_text = f"[公式サイトで見る]({place['url']})" if place['url'] != "公式サイトなし" else "公式サイトなし"
                                    st.write(f"{place['name']} - {place['vicinity']} - {url_text}")
                            else:
                                st.write("適切な飲食店が見つかりませんでした。")
                        else:
                            st.write("メンバーの最寄り駅の情報が不足しています。")
                    except Exception as e:
                        st.write("エラーが発生しました。詳細:", e)
                else:
                    st.write("参加可能日程が選択されていません。")
            else:
                st.write("メンバーが追加されていません。")

        # 会の趣旨に基づいたゲーム提案
        st.subheader("提案されたゲーム")
        if "event_type" in st.session_state:
            suggested_game = suggest_game(st.session_state.event_type)
            st.write(suggested_game)

        # 決定した日程の天気予報を表示
        st.subheader("選択した日程の天気")
        if "selected_date" in st.session_state:
            weather = get_weather_forecast(st.session_state.selected_date, "東京都")  # ここでは仮に「東京都」としています
            weather_message = get_weather_message(weather)
            st.write(f"**{st.session_state.selected_date.strftime('%Y-%m-%d')} の天気:** {weather}")
            st.write(weather_message)
        else:
            st.write("日程がまだ決定していません。")

if __name__ == "__main__":
    main()

# がたろーがブランチ作って編集 08/20 17:30