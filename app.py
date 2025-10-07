import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from argopy import DataFetcher
from datetime import timedelta
import os

# Streamlit 설정
st.set_page_config(page_title="Hurricane & Argo Dashboard", layout="wide")
st.title("🌪️ Hurricane & Argo Profile Dashboard")

# 입력값 설정
season = st.number_input("Select Hurricane Season", min_value=1980, max_value=2025, value=2023)
target_hurr_input = st.text_input("Enter Hurricane Names (comma-separated)", value="ADRIAN,HILARY,IDALIA,LIDIA")
target_hurr = [h.strip().upper() for h in target_hurr_input.split(',') if h.strip()]
bnd = st.slider("Boundary Box (degrees)", 1, 5, 2)
bef_bnd = st.slider("Days Before Hurricane", 1, 30, 14)
dur_bnd = st.slider("Days During Hurricane", 1, 5, 1)
aft_bnd = st.slider("Days After Hurricane", 1, 30, 14)

ibt_file_path = "ibtracs.ALL.list.v04r01.csv.gz"
output_dir = "argo_profile_logs"
os.makedirs(output_dir, exist_ok=True)

@st.cache_data
def load_ibtracs(path):
    usecols = ['SEASON', 'NAME', 'LAT', 'LON', 'ISO_TIME']
    df = pd.read_csv(path, compression="gzip", usecols=usecols)
    df.columns = df.columns.str.strip().str.upper()
    df['SEASON'] = pd.to_numeric(df['SEASON'], errors='coerce')
    df['LAT'] = pd.to_numeric(df['LAT'], errors='coerce')
    df['LON'] = pd.to_numeric(df['LON'], errors='coerce')
    df['ISO_TIME'] = pd.to_datetime(df['ISO_TIME'], errors='coerce')
    return df.dropna(subset=['LAT', 'LON', 'ISO_TIME'])

if st.button("Run Analysis"):
    st.info("📥 Loading IBTrACS data...")
    ibtracs = load_ibtracs(ibt_file_path)
    ibtracs_seas = ibtracs[ibtracs['SEASON'] == season]
    storms = ibtracs_seas.groupby('NAME')

    for name, group in storms:
        if target_hurr and name.upper() not in target_hurr:
            continue

        with st.status(f"🔄 Processing {name} ({season})...", expanded=True) as status:
            group = group.sort_values('ISO_TIME')
            lats = group['LAT'].values
            lons = group['LON'].values
            times = pd.to_datetime(group['ISO_TIME'])

            lat_min, lat_max = lats.min() - bnd, lats.max() + bnd
            lon_min, lon_max = lons.min() - bnd, lons.max() + bnd
            time_min = times.min() - timedelta(days=bef_bnd),
            time_max = times.max() + timedelta(days=aft_bnd)

            try:
                ds = DataFetcher().region([
                    lon_min, lon_max, lat_min, lat_max, 0, 2000,
                    str(pd.to_datetime(time_min).date()), str(pd.to_datetime(time_max).date())
                ]).to_xarray()
            except Exception as e:
                st.error(f"❌ Argo data fetch failed for {name}: {e}")
                continue

            argo_before, argo_during, argo_after = [], [], []

            if ds is not None and all(k in ds for k in ['LATITUDE', 'LONGITUDE', 'TIME', 'PLATFORM_NUMBER', 'CYCLE_NUMBER']):
                argo_times = pd.to_datetime(ds['TIME'].values, errors='coerce')
                for lon, lat, time, pid, cycle in zip(ds['LONGITUDE'].values, ds['LATITUDE'].values, argo_times, ds['PLATFORM_NUMBER'].values, ds['CYCLE_NUMBER'].values):
                    if pd.isna(time) or pd.isna(lat) or pd.isna(lon):
                        continue
                    pid_str = pid.decode() if isinstance(pid, (bytes, bytearray)) else str(pid)
                    label = f"{pid_str}-{cycle}"
                    entry = f"{label}, {time.date()}, {lat:.2f}, {lon:.2f}"

                    for pt_time in times:
                        before_start = pt_time - timedelta(days=bef_bnd)
                        before_end = pt_time - timedelta(days=dur_bnd)
                        during_start = pt_time - timedelta(days=dur_bnd)
                        during_end = pt_time + timedelta(days=dur_bnd)
                        after_start = pt_time + timedelta(days=dur_bnd)
                        after_end = pt_time + timedelta(days=aft_bnd)

                        if before_start <= time < before_end:
                            argo_before.append(entry)
                        elif during_start <= time <= during_end:
                            argo_during.append(entry)
                        elif after_start < time <= after_end:
                            argo_after.append(entry)

            txt_filename = os.path.join(output_dir, f"argo_profiles_{name.lower().replace(' ', '_')}.txt")
            with open(txt_filename, 'w') as f:
                f.write(f"Argo Profiles for Hurricane: {name} {season}\n\n")
                f.write("[Before]\n" + ("\n".join(sorted(set(argo_before))) if argo_before else "None\n"))
                f.write("\n\n[During]\n" + ("\n".join(sorted(set(argo_during))) if argo_during else "None\n"))
                f.write("\n\n[After]\n" + ("\n".join(sorted(set(argo_after))) if argo_after else "None\n"))

            st.download_button("Download Profile Log", data=open(txt_filename).read(), file_name=os.path.basename(txt_filename))
            st.markdown("### Profile List")
            st.code(open(txt_filename).read(), language='text')

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
                    lon_p = [float(lon.strip()) for lat, lon in coords]
                    lat_p = [float(lat.strip()) for lat, lon in coords]
                    ax.scatter(lon_p, lat_p, color=color, s=10, label=label_text)

            plot_profiles(argo_before, 'magenta', 'Argo: Before')
            plot_profiles(argo_during, 'lime', 'Argo: During')
            plot_profiles(argo_after, 'blue', 'Argo: After')

            plt.title(f"{name} {season} – Hurricane Path & Argo Profiles")
            plt.legend()
            st.pyplot(fig)

            status.update(label=f"✅ Done with {name} ({season})", state="complete")
