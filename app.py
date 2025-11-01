import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from argopy import DataFetcher
from datetime import timedelta
import os
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)

# Streamlit 설정
st.set_page_config(page_title="Hurricane & Argo Dashboard", layout="wide")
st.title("🌪️ Hurricane & Argo Profile Dashboard")

with st.expander("📘 Dashboard Guide (Click to expand)"):
    st.markdown("""  
    ## **User Guide for First-Time Visitors**

    ### 🧠 What is this dashboard for?

    This dashboard helps you explore the relationship between hurricanes and ocean conditions using **Argo float profiles**. Argo floats are autonomous instruments that collect ocean data like temperature, salinity, and biogeochemical properties. By analyzing Argo data before, during, and after hurricanes, you can study how storms impact the ocean.

    ### 🚀 How to use the dashboard

    **1. Select a Hurricane Season**  
    Use the number input to choose a year (e.g., 2023). The dashboard will load hurricane data from that season.

    **2. Enter Hurricane Names**  
    Type one or more hurricane names from the list separated by commas (e.g., `ADRIAN,HILARY`). These names must match official records from the IBTrACS dataset.

    **3. Set Analysis Parameters**  
    - **Boundary Box (degrees)**: Defines the spatial range around each hurricane point to search for Argo profiles.  
    - **Days Before / During / After**: Defines the time window for analysis relative to each hurricane point.  
      - *Before*: Days leading up to the hurricane  
      - *During*: ± days around the hurricane (centered)  
      - *After*: Days following the hurricane

    **4. Run the Analysis**  
    Click the **Run Analysis** button to start. The dashboard will:  
    - Load hurricane track data  
    - Search for Argo profiles within the defined time and space  
    - Categorize profiles into Before, During, and After groups  
    - Extract sensor information from each profile

    **5. View and Download Results**  
    - A downloadable log file will be generated for each hurricane, listing all matching Argo profiles and their sensor types.  
    - A map will display the hurricane path and Argo profile locations, color-coded by time group:  
      - 🔴 Before  
      - 🟢 During  
      - 🔵 After

    ### 📦 What kind of data will I see?

    Each Argo profile entry includes:  
    - Float ID and cycle number  
    - Date and location (latitude, longitude)  
    - Sensor types (e.g., TEMP, PSAL, DOXY, CHLA, PH)

    ### 🧭 Tips for better results

    - Use accurate hurricane names from the selected season.  
    - Increase the boundary box or time window if no profiles are found.  
    - Profiles may be sparse in certain regions or timeframes.
    """)

# 상태 초기화
if "show_list" not in st.session_state:
    st.session_state.show_list = False

# 입력값 설정
season = st.number_input("Select Hurricane Season", min_value=1980, max_value=2025, value=2023)

if st.button("📋 Show Hurricane List"):
    st.session_state.show_list = True

ibt_file_path = "ibtracs.ALL.list.v04r01.csv.gz"
output_dir = "argo_profile_logs"
os.makedirs(output_dir, exist_ok=True)

if st.session_state.show_list:
    st.info("📥 Loading hurricane names for selected season...")
    usecols = ['SEASON', 'NAME', 'ISO_TIME']
    chunksize = 100000
    filtered_chunks = []

    try:
        for chunk in pd.read_csv(ibt_file_path, compression="gzip", usecols=usecols,
                                 chunksize=chunksize, low_memory=False):
            chunk.columns = chunk.columns.str.strip().str.upper()
            chunk['SEASON'] = pd.to_numeric(chunk['SEASON'], errors='coerce')
            chunk['ISO_TIME'] = pd.to_datetime(chunk['ISO_TIME'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
            filtered = chunk[(chunk['SEASON'] == season) & (chunk['ISO_TIME'].dt.year == season)]
            filtered_chunks.append(filtered)

        ibtracs_seas = pd.concat(filtered_chunks, ignore_index=True)
    except Exception as e:
        st.error(f"❌ Failed to load IBTrACS data: {e}")
        st.stop()

    storm_names = (
        ibtracs_seas[['NAME', 'ISO_TIME']]
        .dropna()
        .sort_values('ISO_TIME')
        .drop_duplicates(subset='NAME')
    )

    st.markdown("### 🌀 Hurricanes in Selected Season")
    st.dataframe(storm_names.reset_index(drop=True), use_container_width=True)

    # 허리케인 이름 입력
    target_hurr_input = st.text_input("Enter Hurricane Names (comma-separated)", value="")
    target_hurr = [h.strip().upper() for h in target_hurr_input.split(',') if h.strip()]

    # 타임라인 시각화 및 슬라이더
    st.markdown("### 🕒 Hurricane Time Window")
    st.markdown("Adjust the time window around each hurricane point:")
    st.markdown("```\n← Before (A) ←─── During (B*2) ───→ After (C) →\n```")

    col1, col2, col3 = st.columns(3)
    with col1:
        bef_bnd = st.slider("A: Days Before", 1, 30, 14)
    with col2:
        dur_bnd = st.slider("B: Days Around Hurricane", 1, 5, 1)
    with col3:
        aft_bnd = st.slider("C: Days After", 1, 30, 14)
        
    st.markdown(f"⏱️ Time Window Summary:\n- Before: A days\n- During: ±B days (Total B*2 days)\n- After: C days")

    st.markdown("### 🌍 Spatial Range")
    bnd = st.slider("Boundary Box (degrees)", min_value=1, max_value=5, value=2)

    if st.button("🚀 Run Analysis"):
        st.info("📥 Reloading full hurricane data...")
        bef_bnd = bef_bnd + dur_bnd
        aft_bnd = aft_bnd + dur_bnd

        usecols = ['SEASON', 'NAME', 'LAT', 'LON', 'ISO_TIME']
        filtered_chunks = []

        try:
            for chunk in pd.read_csv(ibt_file_path, compression="gzip", usecols=usecols,
                                     chunksize=chunksize, low_memory=False):
                chunk.columns = chunk.columns.str.strip().str.upper()
                chunk['SEASON'] = pd.to_numeric(chunk['SEASON'], errors='coerce')
                chunk['LAT'] = pd.to_numeric(chunk['LAT'], errors='coerce')
                chunk['LON'] = pd.to_numeric(chunk['LON'], errors='coerce')
                chunk['ISO_TIME'] = pd.to_datetime(chunk['ISO_TIME'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
                filtered = chunk[(chunk['SEASON'] == season) & (chunk['ISO_TIME'].dt.year == season)]
                filtered_chunks.append(filtered)

            ibtracs_seas = pd.concat(filtered_chunks, ignore_index=True)
        except Exception as e:
            st.error(f"❌ Failed to load IBTrACS data: {e}")
            st.stop()

        storms = ibtracs_seas.groupby('NAME')

        for name, group in storms:
            if target_hurr and name.upper() not in target_hurr:
                continue

            with st.status(f"🔄 Processing {name} ({season})...", expanded=True):
                group = group.sort_values('ISO_TIME')
                lats = group['LAT'].values
                lons = group['LON'].values
                times = pd.to_datetime(group['ISO_TIME'].values)

                lat_min, lat_max = lats.min() - bnd, lats.max() + bnd
                lon_min, lon_max = lons.min() - bnd, lons.max() + bnd

                argo_before, argo_during, argo_after = [], [], []

                for point_time, point_lat, point_lon in zip(times, lats, lons):
                    before_start = point_time - timedelta(days=bef_bnd)
                    before_end = point_time - timedelta(days=dur_bnd)
                    during_start = point_time - timedelta(days=dur_bnd)
                    during_end = point_time + timedelta(days=dur_bnd)
                    after_start = point_time + timedelta(days=dur_bnd)
                    after_end = point_time + timedelta(days=aft_bnd)

                    lat_box_min, lat_box_max = point_lat - bnd, point_lat + bnd
                    lon_box_min, lon_box_max = point_lon - bnd, point_lon + bnd

                    try:
                        ds = DataFetcher().region([
                            lon_box_min, lon_box_max, lat_box_min, lat_box_max, 0, 2000,
                            str(before_start.date()), str(after_end.date())
                        ]).to_xarray()

                        if ds is None or ds['LATITUDE'].size == 0:
                            continue

                        argo_times = pd.to_datetime(ds['TIME'].values, errors='coerce')
                        valid_mask = ~pd.isna(argo_times) & ~pd.isna(ds['LATITUDE']) & ~pd.isna(ds['LONGITUDE'])
                        argo_times = argo_times[valid_mask]

                        lon_argo = ds['LONGITUDE'].values
                        lat_argo = ds['LATITUDE'].values
                        platform_ids = ds['PLATFORM_NUMBER'].values
                        cycle_numbers = ds['CYCLE_NUMBER'].values

                        known_sensors = ['TEMP', 'PSAL', 'PRES', 'DOXY', 'CHLA', 'BBP', 'PH', 'NITRATE', 'CDOM', 'DOWN_IRRADIANCE', 'UP_IRRADIANCE', 'BISULFIDE', 'TOTAL_ALKALINITY', 'DIC', 'PCO2', 'NH4', 'PHOSPHATE', 'SILICATE']

                        sensor_vars = [v for v in ds.data_vars if v in known_sensors]
                        sensors = ','.join(sorted(set(sensor_vars))) if sensor_vars else 'Unknown'

                        for lon, lat, time, pid, cycle in zip(lon_argo, lat_argo, argo_times, platform_ids, cycle_numbers):
                            if pd.isna(time) or pd.isna(lat) or pd.isna(lon):
                                continue
                            pid_str = pid.decode() if isinstance(pid, (bytes, bytearray)) else str(pid)
                            label = f"{pid_str}-{cycle}"
                            entry = f"{label}, {time.date()}, {lat:.2f}, {lon:.2f}, Sensors: {sensors}"

                            if before_start <= time < before_end:
                                argo_before.append(entry)
                            elif during_start <= time <= during_end:
                                argo_during.append(entry)
                            elif after_start < time <= after_end:
                                argo_after.append(entry)

                    except Exception as e:
                        logging.info(f"Skipped due to error at {point_time.date()} ({point_lat:.2f}, {point_lon:.2f}): {type(e).__name__}")
                        continue

                txt_filename = os.path.join(output_dir, f"argo_profiles_{name.lower().replace(' ', '_')}.txt")
                with open(txt_filename, 'w') as f:
                    f.write(f"Argo Profiles for Hurricane: {name} {season}\n\n")

                    f.write("[Before]\n")
                    f.write("\n".join(sorted(set(argo_before))) if argo_before else "None\n")

                    f.write("\n\n[During]\n")
                    f.write("\n".join(sorted(set(argo_during))) if argo_during else "None\n")

                    f.write("\n\n[After]\n")
                    f.write("\n".join(sorted(set(argo_after))) if argo_after else "None\n")


                st.download_button("Download Profile Log", data=open(txt_filename).read(), file_name=os.path.basename(txt_filename))

                st.markdown("### Profile List")
                with open(txt_filename, 'r') as f:
                    profile_text = f.read()
                st.code(profile_text, language='text')

                fig = plt.figure(figsize=(10, 6))
                ax = plt.axes(projection=ccrs.PlateCarree())
                ax.set_extent([lon_min - 5, lon_max + 5, lat_min - 5, lat_max + 5])
                ax.add_feature(cfeature.COASTLINE)
                ax.add_feature(cfeature.BORDERS)
                ax.gridlines(draw_labels=True)
                ax.plot(lons, lats, 'r-', label=f"{name} path")
                ax.scatter(lons, lats, color='red', s=10)

                def plot_profiles(profiles, color, label_text):
                    if profiles:
                        lat_p = [float(entry.split(',')[2].strip()) for entry in profiles]
                        lon_p = [float(entry.split(',')[3].strip()) for entry in profiles]
                        ax.scatter(lon_p, lat_p, color=color, s=10, label=label_text)

                plot_profiles(argo_before, 'magenta', 'Argo: Before')
                plot_profiles(argo_during, 'lime', 'Argo: During')
                plot_profiles(argo_after, 'blue', 'Argo: After')

                plt.title(f"{name} {season} – Hurricane Path & Argo Profiles")
                plt.legend()
                st.pyplot(fig)
