# argo-hurricane-dashboard

https://argo-hurricane-dashboard-enzjpxbqwspmid6b5nc6iv.streamlit.app/
---

## 🌪️ Hurricane & Argo Profile Dashboard  
**User Guide for First-Time Visitors**

https://github.com/user-attachments/assets/526f887c-2610-4021-974c-0f9f0d270933



### 🧠 What is this dashboard for?

This dashboard helps you explore the relationship between hurricanes and ocean conditions using **Argo float profiles**. Argo floats are autonomous instruments that collect ocean data like temperature, salinity, and biogeochemical properties. By analyzing Argo data before, during, and after hurricanes, you can study how storms impact the ocean.

---

### 🚀 How to use the dashboard

#### 1. **Select a Hurricane Season**
Use the number input to choose a year (e.g., 2023). The dashboard will load hurricane data from that season.

#### 2. **Enter Hurricane Names**
Type one or more hurricane names from the list separated by commas (e.g., `ADRIAN,HILARY`). These names must match official records from the IBTrACS dataset.

#### 3. **Set Analysis Parameters**
- **Boundary Box (degrees)**: Defines the spatial range around each hurricane point to search for Argo profiles.
- **Days Before / During / After**: Defines the time window for analysis relative to each hurricane point.
  - *Before*: Days leading up to the hurricane
  - *During*: ± days around the hurricane (centered)
  - *After*: Days following the hurricane

#### 4. **Run the Analysis**
Click the **Run Analysis** button to start. The dashboard will:
- Load hurricane track data
- Search for Argo profiles within the defined time and space
- Categorize profiles into Before, During, and After groups
- Extract sensor information from each profile

#### 5. **View and Download Results**
- A downloadable log file will be generated for each hurricane, listing all matching Argo profiles and their sensor types.
- A map will display the hurricane path and Argo profile locations, color-coded by time group:
  - 🔴 Before
  - 🟢 During
  - 🔵 After

---

### 📦 What kind of data will I see?

Each Argo profile entry includes:
- Float ID and cycle number
- Date and location (latitude, longitude)
- Sensor types (e.g., TEMP, PSAL, DOXY, CHLA, PH)

---

### 🧭 Tips for better results

- Use accurate hurricane names from the selected season.
- Increase the boundary box or time window if no profiles are found.
- Profiles may be sparse in certain regions or timeframes.

---
