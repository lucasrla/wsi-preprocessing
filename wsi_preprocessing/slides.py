import pathlib

import pandas as pd
import numpy as np

from wsi_tile_cleanup import utils, filters


def list_slides(slides_dir, glob_pattern="*.svs"):
    slides_dir = pathlib.Path(slides_dir)
    slides = [_ for _ in slides_dir.glob(glob_pattern)]
    print(f"{len(slides)} file(s) found via glob: {glob_pattern}")

    return slides


def save_slides_mpp_otsu(slides, csv_fname, mpp_key="openslide.mpp-x"):
    d = {}
    d["slide_path"] = []

    for file in slides:
        d["slide_path"].append(f"{file}")

    slides_df = pd.DataFrame(d)
    slides_df["slide_path"] = slides_df["slide_path"].astype("string")

    slides_df["slide_mpp"] = np.nan
    slides_df["otsu_thres"] = np.nan
    num_slides = len(slides_df)

    for idx, row in slides_df.iterrows():
        file = row["slide_path"]
        print(f"[{idx + 1}/{num_slides}] {file}")

        print(f"- finding slide resolution")

        vi = utils.read_image(file, access="sequential", level=2)

        try:
            # TODO: generalize the mpp_key?
            # some alternatives:
            # - "aperio.MPP", "openslide.mpp-y", "openslide.mpp-x"
            mpp = float(vi.get(mpp_key))
        except Exception as e:
            mpp = None
            print(f"ERROR: {file} does not have an 'aperio.MPP'")
            pass

        slides_df.loc[idx, "slide_mpp"] = mpp

        print(f"- calculating otsu threshold")

        try:
            otsu_threshold = filters.otsu_threshold(vi)
        except Exception as e:
            print(f"ERROR: {file} could not calculate otsu threshold")
            print(e)
            otsu_threshold = np.nan

        slides_df.loc[idx, "otsu_thres"] = otsu_threshold

        del vi

    slides_df["slide_mpp"] = slides_df["slide_mpp"].astype("float32")
    slides_df = slides_df.convert_dtypes()

    # print(f"{slides_df.groupby(['slide_mpp']).size()}")
    # print(f"{slides_df.head(3)}")

    slides_df.to_csv(csv_fname, index=False)
    print(f"slides info (mpp, otsu_thres) saved to {csv_fname}")

