import pathlib
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import numpy as np
import pandas as pd
from wsi_tile_cleanup import filters, utils

from .timer import Timer


# TODO: extract this function (it is repeated from tiles.py)
def consolidate_tiles_csvs(output_dir, consolidated_csv, glob_pattern):
    output_dir_path = pathlib.Path(output_dir)
    dfs = [pd.read_csv(_) for _ in output_dir_path.glob(glob_pattern)]
    consolidated_df = pd.concat(dfs, ignore_index=True)

    # prevent floats with 9999999... from wasting disk space
    consolidated_df = consolidated_df.round(
        {"bg_otsu": 5, "r_pen": 5, "g_pen": 5, "b_pen": 5, "blackish": 5}
    )

    consolidated_df.to_csv(consolidated_csv, index=False)
    print(f"tiles info (with filters) consolidated and saved to {consolidated_csv}")


def exec_multiprocess(fn, iterable, out_dict, *fn_params):
    function = partial(fn, *fn_params)

    with ProcessPoolExecutor() as executor:
        for el in executor.map(function, iterable["tile_path"]):
            if el is not None:
                ftr = iterable["tile_path"] == el[0]  # tile
                idx = iterable[ftr].index.tolist()[0]  # 1st item of index

                # f_size, bg, r_pen, g_pen, b_pen, blackish
                out_dict[idx] = [_ for _ in el[1:]]

    return out_dict


def compute_masks(fsize_thres, otsu_thres, tile_path):
    # https://stackoverflow.com/questions/6591931/getting-file-size-in-python
    f_size = pathlib.Path(tile_path).stat().st_size
    if f_size < (fsize_thres * 1024):
        return tile_path, f_size, None, None, None, None, None

    vi_tile = utils.read_image(tile_path)
    vi_bands = utils.split_rgb(vi_tile)

    r_pen = filters.pen_percent(vi_bands, "red")
    g_pen = filters.pen_percent(vi_bands, "green")
    b_pen = filters.pen_percent(vi_bands, "blue")

    blackish = filters.blackish_percent(vi_bands)

    bg = filters.background_percent(vi_tile, otsu_thres)

    del vi_tile
    del vi_bands

    return tile_path, f_size, bg, r_pen, g_pen, b_pen, blackish


def calculate_filters(slides_csv, tiles_dir, consolidated_csv, min_file_size_kb=50):
    t = Timer()

    slides_df = pd.read_csv(slides_csv)
    slides_df = slides_df.convert_dtypes()

    # remove slides that do not have otsu thresholds available
    slides_df = slides_df[pd.notnull(slides_df["otsu_thres"])]
    num_slides = len(slides_df)

    tiles_path = pathlib.Path(tiles_dir)

    for idx, row in slides_df.iterrows():
        slide_path = pathlib.Path(row["slide_path"])
        otsu_threshold = int(row["otsu_thres"])

        print(f"[{idx + 1}/{num_slides}] {slide_path.name}")

        tiles_csv_path = [
            _ for _ in tiles_path.glob(f"{slide_path.name}*-tile_path.csv")
        ]

        # it should be safe to assume that there is only one match
        tiles_csv_path = tiles_csv_path[0]

        output_csv = f"{tiles_csv_path}".replace(".csv", "-filters_cleanup.csv")

        if pathlib.Path(output_csv).is_file():
            print(f"- {output_csv} already exists. Will skip this slide...")
            continue

        tiles_df = pd.read_csv(tiles_csv_path)
        tiles_df = tiles_df.convert_dtypes()

        # make the path absolute
        tiles_df["tile_path"] = tiles_dir + tiles_df["tile_path"]

        new_cols = ["f_size", "bg_otsu", "r_pen", "g_pen", "b_pen", "blackish"]
        for col in new_cols:
            tiles_df[col] = np.nan
        tiles_df[new_cols] = tiles_df[new_cols].astype("float32")

        tt = Timer()

        tiles_dict = {}

        tiles_dict = exec_multiprocess(
            compute_masks,  # function
            tiles_df,  # iterable
            tiles_dict,  # output (dictionary)
            min_file_size_kb,  # function parameter (1st)
            otsu_threshold,  # function parameter (2nd)
        )

        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.from_dict.html
        output_df = pd.DataFrame.from_dict(
            tiles_dict, orient="index", columns=new_cols,
        )

        # https://stackoverflow.com/a/44806099
        tiles_df.loc[output_df.index, new_cols] = output_df.values
        tiles_df["f_size"] = tiles_df["f_size"].astype("uint32")

        # prevent floats with 9999999... from wasting disk space
        tiles_df = tiles_df.round(
            {"bg_otsu": 5, "r_pen": 5, "g_pen": 5, "b_pen": 5, "blackish": 5}
        )

        # remove absolute path before saving to csv
        tiles_df["tile_path"] = tiles_df["tile_path"].str.replace(
            tiles_dir, "", regex=False
        )

        # print(tiles_df.info())

        tiles_df.to_csv(output_csv, index=False)
        print(f"- data saved to {output_csv}")

        print(f"- time elapsed: {tt.elapsed()}")

    consolidate_tiles_csvs(tiles_dir, consolidated_csv, "*-filters_cleanup.csv")
