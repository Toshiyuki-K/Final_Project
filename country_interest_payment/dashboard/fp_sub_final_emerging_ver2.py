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

# Hill scale の定義
hill_scale = {
    21: 'AAA', 20: 'AA+', 19: 'AA', 18: 'AA-', 17: 'A+', 16: 'A', 15: 'A-',
    14: 'BBB+', 13: 'BBB', 12: 'BBB-', 11: 'BB+', 10: 'BB', 9: 'BB-',
    8: 'B+', 7: 'B', 6: 'B-', 5: 'CCC+', 4: 'CCC', 3: 'CCC-', 2: 'CC', 1: 'C', 0: 'D'
}
hill_scale_order = {v: k for k, v in hill_scale.items()}  # ソート用の逆マッピング

# UIの定義
app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_switch(
            id="switch_button",
            label="Area data to Country data",
            value=False  # 初期状態はオフ
        ),
        ui.panel_conditional(
            "input.switch_button == false",  # オフのとき大陸選択メニューを表示
            ui.input_checkbox_group(
                id="continent_select",
                label="Select Areas:",
                choices=["Africa", "Asia", "Non-Africa"],  # 選択肢を限定
                selected=["Africa"]  # デフォルト選択
            )
        ),
        ui.panel_conditional(
            "input.switch_button == true",  # オンのとき通常プロット
            ui.input_select(
                id="region_country_select",
                label="Select a Region and Country:",
                choices=[]  # 初期状態では空（後でサーバー側で更新）
            )
        ),
        title="Switch Between Views"
    ),
    # プロットを条件付きで表示
    ui.panel_conditional(
        "input.switch_button == false",  # スイッチがオフのとき表示
        ui.output_plot("continent_plot", width='800px', height='600px')  # 大陸別プロット
    ),
    ui.panel_conditional(
        "input.switch_button == true",  # スイッチがオンのとき表示
        ui.output_plot("country_plot", width='800px', height='600px')  # 通常プロット
    )
)

# サーバーロジック
def server(input, output, session):
    # データ読み込み
    @reactive.Calc
    def load_data():
        data = pd.read_csv(csv_path)
        data['Year'] = pd.to_numeric(data['Year'], errors='coerce')
        data['Interest payments on external debt (% of GNI)'] = pd.to_numeric(
            data['Interest payments on external debt (% of GNI)'], errors='coerce'
        )
        data['Average Credit Rating'] = pd.to_numeric(data['Average Credit Rating'], errors='coerce')
        data['CONTINENT'] = data['CONTINENT'].astype(str)
        data['SUBREGION'] = data['SUBREGION'].astype(str)
        data['Country Name'] = data['Country Name'].astype(str)
        data['Year'] = data['Year'].fillna(0).astype(int)
        return data

    # ドロップダウンメニューを更新
    @reactive.Effect
    def update_region_country_choices():
        data = load_data()
        region_country_list = (
            data[['SUBREGION', 'Country Name']]
            .drop_duplicates()
            .apply(lambda row: f"{row['SUBREGION']} - {row['Country Name']}", axis=1)
            .tolist()
        )
        region_country_list.sort()  # アルファベット順にソート
        ui.update_select("region_country_select", choices=region_country_list)

    # 大陸別プロット（重ね合わせ）
    @output
    @render.plot
    def continent_plot():
        data = load_data()
        selected_continents = input.continent_select()
        if not selected_continents:  # 何も選択されていない場合
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No continents selected.", 
                    ha="center", va="center", fontsize=16)
            ax.axis("off")
            return fig

        fig, ax = plt.subplots(figsize=(10, 6))
        colors = {"Africa": "red", "Asia": "blue", "Non-Africa": "green"}
        all_ratings = pd.Index(hill_scale.values())  # 共通のレーティングインデックス

        for continent in selected_continents:
            if continent == "Non-Africa":
                continent_data = data[
                    (data["CONTINENT"] != "Africa") & 
                    (data["Year"] == 2022)
                ]
            else:
                continent_data = data[
                    (data["CONTINENT"] == continent) & 
                    (data["Year"] == 2022)
                ]

            # 欠損値を削除
            continent_data = continent_data.dropna(subset=["Interest payments on external debt (% of GNI)", "Average Credit Rating"])
        
            # クレジットレーティングを丸めて変換
            continent_data["Rounded_Credit_Rating"] = continent_data["Average Credit Rating"].round()
            continent_data["Letter_Rating"] = continent_data["Rounded_Credit_Rating"].map(hill_scale)

            # 重み付け平均を計算し、共通インデックスで再インデックス
            weighted_by_rating = (
                continent_data.groupby("Letter_Rating")["Interest payments on external debt (% of GNI)"]
                .mean()
                .reindex(all_ratings)  # 共通のインデックスで再インデックス
            )

            # プロット
            if not weighted_by_rating.empty:
                weighted_by_rating.plot(kind="bar", ax=ax, color=colors[continent], alpha=0.5, label=continent)

                # 平均線を追加
                avg_payment = weighted_by_rating.mean()
                ax.axhline(avg_payment, linestyle="--", color=colors[continent], 
                           label=f"{continent} Weighted Avg ({avg_payment:.2f})")

        # グラフ装飾
        ax.set_title("Weighted Average Interest Payments by Credit Rating (2022)", fontsize=14)
        ax.set_xlabel("Credit Rating", fontsize=12)
        ax.set_ylabel("Interest Payments on External Debt(% of GNI)", fontsize=12)
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", linestyle="--", alpha=0.7)
        ax.legend()  # 凡例
        plt.tight_layout()

        return fig
    
    # 通常プロットの更新
    @output
    @render.plot
    def country_plot():
        data = load_data()
        selected_region_country = input.region_country_select()
        if selected_region_country is None:
            return
        selected_region, selected_country = selected_region_country.split(" - ")
        country_data = data[
            (data["SUBREGION"] == selected_region) &
            (data["Country Name"] == selected_country) &
            (data["Year"].between(2012, 2022))
        ]
        country_data = country_data.dropna(subset=["Interest payments on external debt (% of GNI)"])
        if country_data.empty:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No data available for the selected country.", 
                    ha="center", va="center", fontsize=16)
            ax.axis("off")
            return fig
        x = country_data["Year"]
        y = country_data["Interest payments on external debt (% of GNI)"]
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(x, y, color="skyblue", edgecolor="black")
        ax.set_title(f"Interest Payments on External Debt (% of GNI)\n{selected_country} ({selected_region}) (2012-2022)", fontsize=14)
        ax.set_xlabel("Year", fontsize=12)
        ax.set_ylabel("Interest Payments (% of GNI)", fontsize=12)
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", linestyle="--", alpha=0.7)
        plt.tight_layout()
        return fig

# アプリの作成と実行
app = App(app_ui, server)
