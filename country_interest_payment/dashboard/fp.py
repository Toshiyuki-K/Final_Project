import seaborn as sns
from faicons import icon_svg
import pandas as pd
import os
import geopandas as gpd 
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from shared import app_dir, df
from shiny import App, ui, reactive, render

# CSVファイルのパス
csv_path = r"C:\Users\sumos\OneDrive\デスクトップ\Harris\2024秋\Python2\PS\final_project\data\final_gdf.csv"

# UIの定義
app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select(
            id="continent_country_select",
            label="Select a Continent and Country:",
            choices=[]  # 初期状態では空（後でサーバー側で更新）
        ),
        title="Continent and Country Selection"
    ),
    ui.output_plot("country_plot", width="800px", height="600px")  # プロットを表示するエリア
)

# サーバーロジック
def server(input, output, session):
    # データの読み込みと初期処理
    @reactive.Calc
    def load_data():
        # データを読み込む
        data = pd.read_csv(csv_path)

        # Year列を数値に変換し、エラーをNaNに置き換える
        data['Year'] = pd.to_numeric(data['Year'], errors='coerce')

        # Interest payments列を数値に変換
        data['Interest payments on external debt (% of GNI)'] = pd.to_numeric(
            data['Interest payments on external debt (% of GNI)'], errors='coerce'
        )

        # CONTINENT列とCountry Name列を文字列型に変換
        data['CONTINENT'] = data['CONTINENT'].astype(str)
        data['Country Name'] = data['Country Name'].astype(str)

        # Year列を整数型に変換
        data['Year'] = data['Year'].fillna(0).astype(int)

        return data

    # ドロップダウンメニューを更新
    @reactive.Effect
    def update_continent_country_choices():
        data = load_data()

        # CONTINENT - Country Nameのリストを作成
        continent_country_list = (
            data[['CONTINENT', 'Country Name']]
            .drop_duplicates()
            .apply(lambda row: f"{row['CONTINENT']} - {row['Country Name']}", axis=1)
            .tolist()
        )
        continent_country_list.sort()  # アルファベット順にソート
        ui.update_select("continent_country_select", choices=continent_country_list)

    # プロットを作成
    @output
    @render.plot
    def country_plot():
        data = load_data()
        selected_continent_country = input.continent_country_select()  # ユーザーが選択したCONTINENT - Country

        # CONTINENTとCountry Nameを分割
        selected_continent, selected_country = selected_continent_country.split(" - ")

        # 選択された国のデータをフィルタリング
        country_data = data[
            (data["CONTINENT"] == selected_continent) &
            (data["Country Name"] == selected_country) &
            (data["Year"].between(2012, 2022))
        ]

        # Interest payments列がNaNでない行のみを抽出
        country_data = country_data.dropna(subset=["Interest payments on external debt (% of GNI)"])

        # データが存在しない場合の処理
        if country_data.empty:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No data available for the selected country.", 
                    ha="center", va="center", fontsize=16)
            ax.axis("off")
            return fig

        # プロットデータ
        x = country_data["Year"]
        y = country_data["Interest payments on external debt (% of GNI)"]

        # 棒グラフを作成
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(x, y, color="skyblue", edgecolor="black")
        ax.set_title(f"Interest Payments on External Debt (% of GNI)\n{selected_country} ({selected_continent}) (2012-2022)", fontsize=14)
        ax.set_xlabel("Year", fontsize=12)
        ax.set_ylabel("Interest Payments (% of GNI)", fontsize=12)
        ax.tick_params(axis="x", rotation=45)  # X軸のラベルを回転
        ax.grid(axis="y", linestyle="--", alpha=0.7)
        plt.tight_layout()

        return fig

# アプリの作成と実行
app = App(app_ui, server)


