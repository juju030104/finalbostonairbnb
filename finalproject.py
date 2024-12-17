import streamlit as st
import pandas as pd
import pydeck as pdk
import matplotlib.pyplot as plt
import seaborn as sns
# data
@st.cache_data
def get_airbnb_data():
    return pd.read_csv("listings.csv")

airbnb_data = get_airbnb_data()

# Filter function
def apply_filters(df, min_price, max_price, neighborhoods=None, room_type=None, min_avail=0, max_avail=365, min_reviews=0, search_text=None):
    filtered = df[(df["price"] >= min_price) & (df["price"] <= max_price) &
                  (df["availability_365"] >= min_avail) & (df["availability_365"] <= max_avail) &
                  (df["number_of_reviews"] >= min_reviews)]
    if neighborhoods:
        filtered = filtered[filtered["neighbourhood"].isin(neighborhoods)]
    if room_type:
        filtered = filtered[filtered["room_type"] == room_type]
    if search_text:
        filtered = filtered[filtered["name"].str.contains(search_text, case=False, na=False)]
    avg_price = filtered["price"].mean() if not filtered.empty else 0
    total_count = len(filtered)
    return filtered, avg_price, total_count

# charts
def create_bar_chart(data, x_col, y_col, title, x_label, y_label):
    fig, ax = plt.subplots()
    bars = data.plot(kind="bar", x=x_col, y=y_col, ax=ax, color="lightblue")
    for bar in ax.patches:
        ax.annotate(f"{bar.get_height():.2f}",
                    (bar.get_x() + bar.get_width() / 2., bar.get_height()),
                    ha='center', va='center', xytext=(0, 8), textcoords='offset points')
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    return fig

def create_histogram(data, col, bins, title, x_label, y_label):
    fig, ax = plt.subplots()
    data[col].plot(kind="hist", bins=bins, ax=ax, color="orange", edgecolor="black")
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    return fig

# header
st.title("Boston Airbnbs")
st.markdown("""
Explore Boston Airbnbs! This app will answer the following questions:

1. What's the average listing price in different neighborhoods?
2. What's the average price for each room type?
3. Which Airbnbs are available under a specific price?
4. Where are these Airbnbs located on a map?
""")

# Dashboard
st.markdown("### Quick Stats")
with st.container():
    total_listings = len(airbnb_data)
    avg_price = airbnb_data["price"].mean()
    priciest_neighborhood = airbnb_data.groupby("neighbourhood")["price"].mean().idxmax()
    cheapest_neighborhood = airbnb_data.groupby("neighbourhood")["price"].mean().idxmin()

    st.metric("Total Listings", total_listings)
    st.metric("Overall Average Price", f"${avg_price:.2f}")
    st.metric("Most Expensive Neighborhood", priciest_neighborhood)
    st.metric("Most Affordable Neighborhood", cheapest_neighborhood)

# Sidebar filters
st.sidebar.header("Filters")
chosen_neighborhoods = st.sidebar.multiselect("Neighborhoods", airbnb_data["neighbourhood"].unique(), default=airbnb_data["neighbourhood"].unique())
chosen_room_type = st.sidebar.selectbox("Room Type", ["All"] + list(airbnb_data["room_type"].unique()))
price_range = st.sidebar.slider("Price Range ($)", int(airbnb_data["price"].min()), int(airbnb_data["price"].max()), (50, 300))
availability_range = st.sidebar.slider("Availability (days/year)", 0, 365, (0, 365))
min_reviews = st.sidebar.slider("Minimum Reviews", 0, int(airbnb_data["number_of_reviews"].max()), 0)
search_name = st.sidebar.text_input("Search by Name/Description")

# Tabs for results
tabs = st.tabs(["Neighborhood Prices", "Room Type Prices", "Price Filter", "Map View"])

# Average price by neighborhood
with tabs[0]:
    st.header("Neighborhood Price Averages")
    if chosen_neighborhoods:
        neighborhood_data = airbnb_data[airbnb_data["neighbourhood"].isin(chosen_neighborhoods)].groupby("neighbourhood")["price"].mean().reset_index()
        if neighborhood_data.empty:
            st.warning("No data matches your criteria.")
        else:
            fig = create_bar_chart(neighborhood_data, "neighbourhood", "price", "Average Price by Neighborhood", "Neighborhood", "Price ($)")
            st.pyplot(fig)
    else:
        st.warning("Please select at least one neighborhood.")

# Average price by room type
with tabs[1]:
    st.header("Room Type Price Averages")
    try:
        room_data = airbnb_data if chosen_room_type == "All" else airbnb_data[airbnb_data["room_type"] == chosen_room_type]
        room_avg = room_data.groupby("room_type")["price"].mean().reset_index()
        st.subheader("Prices by Room Type")
        fig = create_bar_chart(room_avg, "room_type", "price", "Room Type Prices", "Room Type", "Price ($)")
        st.pyplot(fig)
    except Exception as err:
        st.error(f"Error generating room type data: {err}")

# Listings under a price
with tabs[2]:
    st.header("Find Listings Below Price")
    try:
        filtered_listings, avg_listing_price, listing_count = apply_filters(
            airbnb_data, price_range[0], price_range[1], chosen_neighborhoods,
            None if chosen_room_type == "All" else chosen_room_type,
            availability_range[0], availability_range[1], min_reviews, search_name)
        if filtered_listings.empty:
            st.warning("No results match your filters.")
        else:
            st.write("Filtered Listings:")
            st.dataframe(filtered_listings[["name", "neighbourhood", "price", "room_type", "availability_365", "number_of_reviews"]])

            st.write(f"Total: {listing_count}")
            st.write(f"Median Price: ${filtered_listings['price'].median():.2f}")
            st.write(f"Price Std Dev: ${filtered_listings['price'].std():.2f}")

            quartiles = filtered_listings["price"].quantile([0.25, 0.75])
            st.write(f"25th Percentile: ${quartiles[0.25]:.2f}")
            st.write(f"75th Percentile: ${quartiles[0.75]:.2f}")

            fig = create_histogram(filtered_listings, "price", 20, "Price Distribution", "Price ($)", "Count")
            st.pyplot(fig)
    except Exception as err:
        st.error(f"Error filtering data: {err}")

# Map
with tabs[3]:
    st.header("Airbnb Map View")
    try:
        map_data, _, _ = apply_filters(airbnb_data, price_range[0], price_range[1], chosen_neighborhoods,
                                       None if chosen_room_type == "All" else chosen_room_type,
                                       availability_range[0], availability_range[1], min_reviews, search_name)
        if map_data.empty:
            st.warning("No data available for map view.")
        else:
            st.subheader("Filtered Airbnb Locations")
            st.pydeck_chart(pdk.Deck(
                map_style="mapbox://styles/mapbox/light-v9",
                initial_view_state=pdk.ViewState(
                    latitude=map_data["latitude"].mean(),
                    longitude=map_data["longitude"].mean(),
                    zoom=11,
                ),
                layers=[
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=map_data,
                        get_position="[longitude, latitude]",
                        get_color="[200, 30, 0, 160]",
                        get_radius=200,
                        pickable=True,
                    ),
                ],
            ))
    except Exception as err:
        st.error(f"Error generating map: {err}")
