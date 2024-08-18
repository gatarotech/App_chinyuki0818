import streamlit as st
import googlemaps
import pandas as pd
from collections import Counter
from datetime import date
import os
import openai

# Google Maps APIキーを環境変数から取得
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
gmaps = googlemaps.Client(key=API_KEY)

# OpenAI APIキーを設定（環境変数から取得）
openai.api_key = os.getenv('OPENAI_API_KEY')

def suggest_game(purpose):
    # ChatGPTにリクエストして、宴会の目的に応じたゲームを提案
    prompt = f"提案してほしい宴会の目的は「{purpose}」です。適切なゲームを提案してください。"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()

def main():
    st.title("最適な飲食店を探すアプリ")

    # 宴会の目的の選択
    st.header("宴会の目的を選択してください")
    purposes = (
        "会社の固い宴会",
        "会社の同僚との気さくな宴会",
        "合コン",
        "友人との遊び",
    )
    selected_purpose = st.selectbox("宴会の目的", purposes)

    # 参加者情報の入力
    st.header("参加者情報の入力")
    num_participants = st.number_input("参加者数を入力してください", min_value=1, step=1)
    participants = []

    for i in range(num_participants):
        st.subheader(f"参加者 {i+1}")
        name = st.text_input(f"名前 {i+1}", key=f"name_{i}")
        dates = st.multiselect(
            f"参加可能日程を選択してください {i+1}",
            options=pd.date_range(start=date.today(), periods=30).tolist(),
            format_func=lambda x: x.strftime('%Y-%m-%d')
        )
        station = st.text_input(f"最寄り駅 {i+1}", key=f"station_{i}")
        if name and dates and station:
            participants.append({
                'name': name,
                'dates': dates,
                'station': station
            })

    # 飲食店の検索と表示
    st.header("最適な飲食店を探す")
    if st.button("飲食店を探す"):
        if participants:
            all_dates = [date for participant in participants for date in participant['dates']]
            date_counts = Counter(all_dates)
            optimal_date = max(date_counts, key=date_counts.get)
            st.session_state.optimal_date = optimal_date

            try:
                locations = [
                    gmaps.geocode(participant['station'])[0]['geometry']['location']
                    for participant in participants
                ]
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
            except Exception as e:
                st.write("エラーが発生しました。詳細:", e)
        else:
            st.write("参加者情報を入力してください。")

    # 飲食店の決定とLINEメッセージの表示
    if 'place_names' in st.session_state:
        selected_place_name = st.selectbox("どの飲食店にしますか？", [p['name'] for p in st.session_state.place_names])
        if selected_place_name:
            selected_place = next(p for p in st.session_state.place_names if p['name'] == selected_place_name)
            place_details = gmaps.place(place_id=selected_place['place_id'])
            phone_number = place_details.get('result', {}).get('formatted_phone_number', '電話番号なし')
            address = place_details.get('result', {}).get('formatted_address', '住所なし')
            st.session_state.selected_place = selected_place
            st.session_state.phone_number = phone_number
            st.session_state.address = address

            st.write(f"選択した飲食店: {selected_place_name}")
            line_message = (
                f"次回の宴会は、{st.session_state.optimal_date}の19:00から「{selected_place_name}」のお店で行います。\n"
                f"住所: {st.session_state.address}\n"
                f"電話番号: {st.session_state.phone_number}\n"
                f"公式サイト: {selected_place['url']}\n"
                "当日楽しみにしております！"
            )
            st.write("LINEで送信するメッセージ:")
            st.code(line_message)

    # ゲーム提案のボタンをLINEメッセージの後に配置
    if st.button("ゲームを提案してもらう"):
        game_suggestion = suggest_game(selected_purpose)
        st.write(f"提案されたゲーム: {game_suggestion}")

if __name__ == "__main__":
    main()
