import streamlit as st
from datetime import datetime
import pandas as pd
from utils.predictions_utils import *
from utils.interpolation_vis_app import *
from utils.hotspot_analysis import *
import streamlit.components.v1 as components


pred_df = pd.read_csv("./demo_predictions.csv")
core_data = pd.read_csv("./PM25_sensor_data")

st.title("PM2.5 Dashboard Demo - March 15 2024")

with st.form(key='location_form'):
    location_input = st.text_input("Enter ZIP Code")
    submit_button = st.form_submit_button(label="Submit")

###############################################
#
# Convert location input to coordinates
#
###############################################

if submit_button:
    try:
        lat, lon = get_coordinates(location_input)
        st.success(f"Using coordinates: ({lat:.4f}, {lon:.4f})")
    except Exception as e:
        st.error(f"Location error: {e}")
        st.stop()

    in_grid = check_within_grid(lat, lon)

    if not in_grid:
        st.error("Your location is outside the interpolation grid. Please select a different point.")
        st.stop()
    else:
        found, prediction = get_pred(lat, lon, pred_df)
        if found:
            st.success(f"Prediction: {prediction}")
        else:
            st.error("Prediction not found.")


    your_prediction = round(prediction['predictions'], 5)

    if your_prediction < 5.0:
        color = 'green'
    elif 5.0 <= your_prediction < 15.0:
        color = 'yellow'
    elif 15.0 <= your_prediction < 35.0:
        color = 'orange'
    else:
        color = 'red'

    st.header('PM2.5 at your location')
    st.markdown(
        f"<h3>Predicted PM2.5 (µg/m³):<br><br><span style='color:{color}'>{your_prediction}</span></h3>",
        unsafe_allow_html=True
    )

    st.subheader('What does this mean?')

    st.write('PM2.5 refers to particulate matter under 2.5 micrometers in diameter (PM2.5). As a pollutant, these particles are so small ' \
    'that they can be inhaled into the bloodstream through the lungs, presenting potential health consequences such as asthma, cardiovascular disease, ' \
    'and even lung cancer.')

    if your_prediction < 5.0:
        st.markdown('<span style="color:green"><strong>This concentration is considered to be generally safe for both long-term and short-term exposure.</span>', unsafe_allow_html=True)

    elif 5.0 <= your_prediction < 9.0:
        st.markdown('<span style="color:yellow"><strong>The World Health organization notes that this concentration (>5.0 µg/m³) may be hazardous '
                'if present annually. However, it is not considered hazardous by the Texas Commission on Environmental Quality, who, according to EPA standards, recently '
                'changed their safety thresholds to 9.0 µg/m³.</span>', unsafe_allow_html=True)
        
    elif 9.0 <= your_prediction < 15.0:
        st.markdown('<span style="color:yellow"><strong>The Texas Commission on Environmental Quality, according to EPA standards, considers this concentration '
                '(>9.0 µg/m³) to be hazardous at annual concentrations.</span>', unsafe_allow_html=True)

    elif 15.0 <= your_prediction < 35.0:
        st.markdown('<span style="color:orange"><strong>This concentration (>15.0 µg/m³) is considered to be concerning at a 24-hour concentration according to the World Health Organization. '
                'However, it is not considered so by the Texas Commission on Environmental Quality, who recently changed their standards to >35 µg/m³.</span>', unsafe_allow_html=True)
        
    elif 35.0 <= your_prediction < 50.0:
        st.markdown('<span style="color:orange"><strong>This concentration (>35.0 µg/m³) is considered to be hazardous by the Texas Commission on Environmental Quality.</span>', unsafe_allow_html=True)

    elif 50.0 <= your_prediction:
        st.markdown('<span style="color:red"><strong>This concentration (>50.0 µg/m³) is considered to be hazardous, and prolonged exposure '
                'may lead to serious health issues and premature mortality</span>', unsafe_allow_html=True)



    ###############################################
    #
    # Visualize grid
    #
    ###############################################

    map_obj = plot_interpolation(pred_df, datetime(2024,3,15), core_data, lon, lat)

    with open("houston_kriging_map.html", 'r', encoding='utf-8') as HtmlFile:
            source_code = HtmlFile.read()
            components.html(source_code, height=600, width=1000)

    use_alternate_viz = st.checkbox("Visualize relative PM2.5 levels")

    if use_alternate_viz:
        map_obj = plot_interpolation_relative(pred_df, datetime(2024,3,15), core_data, lon, lat)
        with open("houston_kriging_map.html", 'r', encoding='utf-8') as HtmlFile:
            source_code = HtmlFile.read()
            components.html(source_code, height=600, width=1000)

    
    ###############################################
    #
    # Find hotspots
    #
    ###############################################

    hotspots_info = st.checkbox("Want to know more about potential hotspots?")

    if hotspots_info:

        core_data['datetime'] = pd.to_datetime(core_data['datetime'], errors='coerce')
        core_data_sub = core_data[core_data['datetime'].dt.date == date]

        localG, p_vals = get_localG(core_data_sub, threshold=0.01)

        core_data_sub.loc[:, 'local_G'] = localG
        core_data_sub.loc[:, 'p_val'] = p_vals

        spots = core_data_sub[core_data_sub['p_val'] < 0.05]

        hotspots = spots[spots['local_G'] > 0]

        if hotspots.empty:

            st.write("There are no detectable hotspots on this map.")

        else:

            st.write(f"There are {hotspots.shape[0]} potential hotspots on this map.")
            map_obj_HC = add_hotspots(map_obj, hotspots)
            with open("houston_kriging_map.html", 'r', encoding='utf-8') as HtmlFile:
                source_code = HtmlFile.read()
                components.html(source_code, height=600, width=1000)

            closest, distance = find_closest_hotspot(hotspots, lat, lon)

            if closest is not None:
                closest_name = closest['sensor_name']
                st.write(f"You are {distance:.2f} miles away from this hotspot: **{closest_name}**")

                hotspot_groups = load_hotspot_info()

                group_name = None
                site_name = closest['sensor_name']
                for group, data in hotspot_groups.items():
                    if site_name in data["sensor_name"]:
                        group_name = group
                        break

                if group_name:
                    group_data = hotspot_groups[group_name]
                    st.markdown(f"### About this area: {group_name}")
                    st.markdown(group_data["description"])
                else:
                    st.info("No additional information available for this hotspot.")