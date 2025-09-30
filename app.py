import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from argopy import DataFetcher
from datetime import timedelta
import os
import logging

logging.basicConfig(level=logging.INFO)
st.set_page_config(page_title="Hurricane & Argo Dashboard", layout="wide")
st.title("🌪️ Hurricane & Argo Profile Dashboard")

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

if st.button("Run Analysis"):
    st.info("📥 Loading IBTrACS data...")
    try:
        ibtracs = pd.read_csv(ibt_file_path, compression="gzip", header=0, low_memory=False)
        st.text("✅ IBTrACS file loaded")
        ibtracs.columns = ibtracs.columns.str.strip().str.upper()
        ibtracs['SEASON'] = pd.to_numeric(ibtracs['SEASON'], errors='coerce')
        ibtracs['LAT'] = pd.to_numeric(ibtracs['LAT'], errors='coerce')
        ibtracs['LON'] = pd.to_numeric(ibtracs['LON'], errors='coerce')
        ibtracs['ISO_TIME'] = pd.to_datetime(ibtracs['ISO_TIME'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
        st.text("✅ IBTrACS columns cleaned and parsed")
    except Exception as e:
        st.error(f"❌ Failed to load IBTrACS data: {e}")
        st.stop()

    ibtracs_seas = ibtracs[ibtracs['SEASON'] == season].dropna(subset=['LAT', 'LON', 'ISO_TIME'])
    st.text(f"✅ Filtered IBTrACS for season {season}, total rows: {len(ibtracs_seas)}")
    storms = ibtracs_seas.groupby('NAME')

    for name, group in storms:
        if target_hurr and name.upper() not in target_hurr:
            continue

        with st.status(f"🔄 Processing {name} ({season})...", expanded=True) as status:
            st.text(f"▶️ Starting storm: {name}")
            group = group.sort_values('ISO_TIME')
            lats = group['LAT'].values
            lons = group['LON'].values
            times = pd.to_datetime(group['ISO_TIME'].values)
            st.text(f"✅ Storm track loaded: {len(times)} points")

            lat_min, lat_max = lats.min() - bnd, lats.max() + bnd
            lon_min, lon_max = lons.min() - bnd, lons.max() + bnd

            argo_before, argo_during, argo_after = [], [], []

            for i, (point_time, point_lat, point_lon) in enumerate(zip(times, lats, lons)):
                st.text(f"🔍 [{i+1}/{len(times)}] Querying Argo at {point_time.date()} ({point_lat:.2f}, {point_lon:.2f})")
                before_start = point_time - timedelta(days=bef_bnd)
                before_end = point_time - timedelta(days=dur_bnd)
                during_start = point_time - timedelta(days=dur_bnd)
                during_end = point_time + timedelta(days=dur_bnd)
                after_start = point_time + timedelta(days=dur_bnd)
                after_end = point_time + timedelta(days=aft_bnd)

                lat_box_min, lat_box_max = point_lat - bnd, point_lat + bnd
                lon_box_min, lon_box_max = point_lon - bnd, point_lon + bnd

                try:
                    ds = DataFetcher
