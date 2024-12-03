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


# Path to the CSV file
csv_path = r"C:\Users\sumos\OneDrive\デスクトップ\Harris\2024秋\Python2\PS\final_project\data\final_gdf.csv"

# Hill scale definition (used for converting numerical credit ratings to letter ratings)
hill_scale = {
    21: 'AAA', 20: 'AA+', 19: 'AA', 18: 'AA-', 17: 'A+', 16: 'A', 15: 'A-',
    14: 'BBB+', 13: 'BBB', 12: 'BBB-', 11: 'BB+', 10: 'BB', 9: 'BB-',
    8: 'B+', 7: 'B', 6: 'B-', 5: 'CCC+', 4: 'CCC', 3: 'CCC-', 2: 'CC', 1: 'C', 0: 'D'
}
# Reverse mapping of Hill scale for sorting
hill_scale_order = {v: k for k, v in hill_scale.items()}

# Define the UI
app_ui = ui.page_sidebar(
    ui.sidebar(
        # Switch button to toggle between continent-level and country-level data views
        ui.input_switch(
            id="switch_button",
            label="Area data to Country data",
            value=False  # Default state is off (continent-level view)
        ),
        # Panel for continent selection when switch is off
        ui.panel_conditional(
            "input.switch_button == false",
            ui.input_checkbox_group(
                id="continent_select",
                label="Select Areas:",
                choices=["Africa", "Asia", "Non-Africa"],  # Limited choices for areas
                selected=["Africa"]  # Default selection
            )
        ),
        # Panel for country selection when switch is on
        ui.panel_conditional(
            "input.switch_button == true",
            ui.input_select(
                id="continent_country_select",
                label="Select a Continent and Country:",
                choices=[]  # Empty initially, to be updated dynamically
            )
        ),
        title="Switch Between Views"  # Sidebar title
    ),
    # Conditional plot outputs
    ui.panel_conditional(
        "input.switch_button == false",  # Show continent-level plot when switch is off
        ui.output_plot("continent_plot", width='800px', height='600px')
    ),
    ui.panel_conditional(
        "input.switch_button == true",  # Show country-level plot when switch is on
        ui.output_plot("country_plot", width='800px', height='600px')
    )
)

# Server logic
def server(input, output, session):
    # Load and preprocess data
    @reactive.Calc
    def load_data():
        data = pd.read_csv(csv_path)
        # Convert columns to numeric where applicable
        data['Year'] = pd.to_numeric(data['Year'], errors='coerce')
        data['Interest payments on external debt (% of GNI)'] = pd.to_numeric(
            data['Interest payments on external debt (% of GNI)'], errors='coerce'
        )
        data['Average Credit Rating'] = pd.to_numeric(data['Average Credit Rating'], errors='coerce')
        # Convert categorical columns to strings
        data['CONTINENT'] = data['CONTINENT'].astype(str)
        data['SUBREGION'] = data['SUBREGION'].astype(str)
        data['Country Name'] = data['Country Name'].astype(str)
        # Ensure column is integer
        data['Year'] = data['Year'].fillna(0).astype(int)
        return data

    # Update dropdown menu for country selection
    @reactive.Effect
    def update_region_country_choices():
        data = load_data()
        # Generate list of unique "Continent - Country" combinations
        continent_country_list = (
            data[['CONTINENT', 'Country Name']]
            .drop_duplicates()
            .apply(lambda row: f"{row['CONTINENT']} - {row['Country Name']}", axis=1)
            .tolist()
        )
        continent_country_list.sort()  # Sort alphabetically
        ui.update_select("continent_country_select", choices=continent_country_list)

    # Continent-level plot
    @output
    @render.plot
    def continent_plot():
        data = load_data()
        selected_continents = input.continent_select()
        if not selected_continents:  # If no areas are selected
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No continents selected.", 
                    ha="center", va="center", fontsize=16)
            ax.axis("off")
            return fig

        fig, ax = plt.subplots(figsize=(10, 6))
        colors = {"Africa": "red", "Asia": "blue", "Non-Africa": "green"}
        all_ratings = pd.Index(hill_scale.values())  # Common credit rating index

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

            # Remove missing values for interest payments and credit ratings
            continent_data = continent_data.dropna(subset=["Interest payments on external debt (% of GNI)", "Average Credit Rating"])
        
            # Convert credit ratings to letter ratings
            continent_data["Rounded_Credit_Rating"] = continent_data["Average Credit Rating"].round()
            continent_data["Letter_Rating"] = continent_data["Rounded_Credit_Rating"].map(hill_scale)

            # Calculate weighted average and align with common credit ratings
            weighted_by_rating = (
                continent_data.groupby("Letter_Rating")["Interest payments on external debt (% of GNI)"]
                .mean()
                .reindex(all_ratings)
            )

            # Plot
            if not weighted_by_rating.empty:
                weighted_by_rating.plot(kind="bar", ax=ax, color=colors[continent], alpha=0.5, label=continent)

                # Add average payment line
                avg_payment = weighted_by_rating.mean()
                ax.axhline(avg_payment, linestyle="--", color=colors[continent], 
                           label=f"{continent} Weighted Avg ({avg_payment:.2f})")

        # Plot decorations
        ax.set_title("Weighted Average Interest Payments by Credit Rating (2022)", fontsize=14)
        ax.set_xlabel("Credit Rating", fontsize=12)
        ax.set_ylabel("Interest Payments on External Debt(% of GNI)", fontsize=12)
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", linestyle="--", alpha=0.7)
        ax.legend()  # Add legend
        plt.tight_layout()

        return fig
    
    # Country-level plot
    @output
    @render.plot
    def country_plot():
        data = load_data()
        selected_continent_country = input.continent_country_select()
        if selected_continent_country is None:
            return
        # Split continent and country
        selected_continent, selected_country = selected_continent_country.split(" - ")
        # Filter data for the selected country
        country_data = data[
            (data["CONTINENT"] == selected_continent) &
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
        ax.set_title(f"Interest Payments on External Debt (% of GNI)\n{selected_country} ({selected_continent}) (2012-2022)", fontsize=14)
        ax.set_xlabel("Year", fontsize=12)
        ax.set_ylabel("Interest Payments (% of GNI)", fontsize=12)
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", linestyle="--", alpha=0.7)
        plt.tight_layout()
        return fig

# Create and run the app
app = App(app_ui, server)
