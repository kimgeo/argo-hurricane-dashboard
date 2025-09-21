import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from argopy import DataFetcher
from datetime import timedelta
import os

download_url = f"https://drive.google.com/uc?id=1dRFqAVP7Ck3r5wpAs5NdZM2f0s6U6vMS&export=download"
output_dir = "argo_profile_logs"
os.makedirs(output_dir, exist_ok=True)

st.set_page_config(page_title="Hurricane & Argo Dashboard", layout="wide")
st.title("Hurricane & Argo Profile Dashboard")

season = st.number_input("Select Hurricane Season", min_value=1980, max_value=2025, value=2023)
target_hurr_input = st.text_input("Enter Hurricane Names (comma-separated)", value="ADRIAN,HILARY,IDALIA,LIDIA")
target_hurr = [h.strip().upper() for h in target_hurr_input.split(',') if h.strip()]
bnd = st.slider("Boundary Box (degrees)", 1, 5, 2)
bef_bnd = st.slider("Days Before Hurricane", 1, 30, 14)
dur_bnd = st.slider("Days During Hurricane", 1, 5, 1)
aft_bnd = st.slider("Days After Hurricane", 1, 30, 14)

ibt_file_path = "ibtracs.ALL.list.v04r01.csv" 
output_dir = "argo_profile_logs"
os.makedirs(output_dir, exist_ok=True)

if st.button("Run Analysis"):
    st.info("Loading IBTrACS data...")
    ibtracs = pd.read_csv(download_url, header=0, low_memory=False)
    ibtracs.columns = ibtracs.columns.str.strip().str.upper()
    ibtracs['SEASON'] = pd.to_numeric(ibtracs['SEASON'], errors='coerce')
    ibtracs['LAT'] = pd.to_numeric(ibtracs['LAT'], errors='coerce')
    ibtracs['LON'] = pd.to_numeric(ibtracs['LON'], errors='coerce')
    ibtracs['ISO_TIME'] = pd.to_datetime(ibtracs['ISO_TIME'], format='%Y-%m-%d %H:%M:%S', errors='coerce')

    ibtracs_seas = ibtracs[ibtracs['SEASON'] == season].dropna(subset=['LAT', 'LON', 'ISO_TIME'])
    storm_count = ibtracs_seas['NAME'].nunique()
    storms = ibtracs_seas.groupby('NAME')

    for idx, (name, group) in enumerate(storms, start=1):
        if target_hurr and name.upper() not in target_hurr:
            continue

        st.subheader(f"{name} ({season})")
        group = group.sort_values('ISO_TIME')
        lats = group['LAT'].values
        lons = group['LON'].values
        times = pd.to_datetime(group['ISO_TIME'].values)

        lat_min, lat_max = lats.min() - bnd, lats.max() + bnd
        lon_min, lon_max = lons.min() - bnd, lons.max() + bnd
        time_start = pd.Timestamp(times.min()) - timedelta(days=bef_bnd)
        time_end = pd.Timestamp(times.max()) + timedelta(days=aft_bnd)

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

                if not all(k in ds for k in ['LATITUDE', 'LONGITUDE', 'TIME', 'PLATFORM_NUMBER', 'CYCLE_NUMBER']):
                    continue

                argo_times = pd.to_datetime(ds['TIME'].values)
                lon_argo = ds['LONGITUDE'].values
                lat_argo = ds['LATITUDE'].values
                platform_ids = ds['PLATFORM_NUMBER'].values
                cycle_numbers = ds['CYCLE_NUMBER'].values

                for lon, lat, time, pid, cycle in zip(lon_argo, lat_argo, argo_times, platform_ids, cycle_numbers):
                    pid_str = pid.decode() if isinstance(pid, (bytes, bytearray)) else str(pid)
                    label = f"{pid_str}-{cycle}"
                    entry = f"{label}, {time.date()}, {lat:.2f}, {lon:.2f}"
                    if before_start <= time < before_end:
                        argo_before.append(entry)
                    elif during_start <= time <= during_end:
                        argo_during.append(entry)
                    elif after_start < time <= after_end:
                        argo_after.append(entry)

            except Exception as e:
                st.warning(f"Skipping point due to error: {e}")
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
                coords = [entry.split(',')[-2:] for entry in profiles]
                lon_p = [float(lon.strip()) for _, lon in coords]
                lat_p = [float(lat.strip()) for lat, _ in coords]
                ax.scatter(lon_p, lat_p, color=color, s=10, label=label_text)

        plot_profiles(argo_before, 'magenta', 'Argo: Before')
        plot_profiles(argo_during, 'lime', 'Argo: During')
        plot_profiles(argo_after, 'blue', 'Argo: After')

        plt.title(f"{name} {season} – Hurricane Path & Argo Profiles")
        plt.legend()
        st.pyplot(fig)
