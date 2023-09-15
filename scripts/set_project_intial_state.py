import os
import re
import pandas as pd

from cwi import PACKAGEDIR

if __name__ == "__main__":
    os.chdir(os.path.abspath(os.path.dirname(__file__)))
    data = {"src": [], "ECOREIGON_ID": []}

    for root, dirs, files in os.walk(
        "Y:\Wetlands\CNWI\working\cnwi-pipeline\priority-areas"
    ):
        for file in files:
            if "training" in file and file.endswith(".shp"):
                src_file = os.path.join(root, file)
                data["src"].append(src_file)
                data["ECOREIGON_ID"].append(
                    int(re.findall(r"\b\d{2,3}\b", src_file)[0])
                )

    df1 = pd.DataFrame(data=data)
    zones = pd.read_csv(os.path.join(PACKAGEDIR, "data", "zones.csv"))

    df = pd.merge(df1, zones, on="ECOREIGON_ID", how="inner")
    df.to_csv("src.csv")

    grouped = df.groupby("ECOZONE_NAME")

    for name, group in grouped:
        if not os.path.exists(name):
            os.mkdir(name)
            os.makedirs(os.path.join(name, "data", "processed"))
            os.makedirs(os.path.join(name, "data", "raw"))

            group.to_csv(os.path.join(name, "datasource.csv"))
