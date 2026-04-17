# src/pipeline/download.py
import copernicusmarine
import os

AOI = dict(
    minimum_longitude=60.0,
    maximum_longitude=100.0,
    minimum_latitude=5.0,
    maximum_latitude=25.0,
)

DATASET_ID = "cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D"

def download_historical():
    os.makedirs("data/raw/chl_historical", exist_ok=True)
    copernicusmarine.subset(
        dataset_id=DATASET_ID,
        variables=["CHL"],
        start_datetime="2019-01-01T00:00:00",
        end_datetime="2023-12-31T00:00:00",
        output_directory="data/raw/chl_historical",
        output_filename="chl_india_2019_2023.nc",
        **AOI,
    )
    print("Historical download complete.")

def download_demo_window():
    os.makedirs("data/raw/chl_nrt", exist_ok=True)
    copernicusmarine.subset(
        dataset_id=DATASET_ID,
        variables=["CHL"],
        start_datetime="2024-01-01T00:00:00",
        end_datetime="2024-03-31T00:00:00",
        output_directory="data/raw/chl_nrt",
        output_filename="chl_india_2024_Q1.nc",
        **AOI,
    )
    print("Demo window download complete.")

if __name__ == "__main__":
    download_historical()
    download_demo_window()