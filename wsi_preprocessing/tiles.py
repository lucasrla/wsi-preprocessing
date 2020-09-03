import pathlib
import re
import datetime

import pyvips as vips
import pandas as pd
from wsi_tile_cleanup import filters, utils

from .timer import Timer

# defaults
MPP = 0.5
DIMS = 224
FMT = ".png"
OUT_DIR = "."


def rescale_slide(vi, mpp=MPP, mpp_key="openslide.mpp-x"):
    # TODO: generalize the mpp_key? some alternatives:
    # - "aperio.MPP", "openslide.mpp-y", "openslide.mpp-x"
    vi_mpp = float(vi.get(mpp_key))
    mpp = float(mpp)

    scale = vi_mpp / mpp

    # 5% "tolerance" because mpp tend to vary within a certain range
    if scale > 1.05:
        print(f"- slide will be scaled up by {scale}")
        print("WARNING: beware potential losses")
    elif scale < 0.95:
        print(f"- slide will be scaled down by {scale}")
    else:
        print(f"- slide will NOT be rescaled | {vi_mpp} is within range of targeted mpp")
        return vi

    return vi.resize(scale)


def fit_tiles(vi, dims=DIMS):
    # resized dimensions
    re_width = vi.width
    re_height = vi.height

    dims = int(dims)

    # forcing perfectly squared tiles on both dimensions
    tiles_across_x = re_width // dims
    tiles_across_y = re_height // dims

    # calculate excess for each dimensions
    excess_x = re_width - tiles_across_x * dims
    excess_y = re_height - tiles_across_y * dims

    return (
        tiles_across_x * dims,
        tiles_across_y * dims,
        excess_x,
        excess_y,
    )


def center_crop(vi, coords):
    fitted_width, fitted_height, excess_x, excess_y = coords

    vi = vi.crop(excess_x // 2, excess_y // 2, fitted_width, fitted_height,)

    return vi


def deepzoom_save(vi, base_name, dir_name=OUT_DIR, dims=DIMS, file_format=FMT):
    # as of pyvips 2.1.12: dir_name is required
    # and not optional as the docs say
    # https://libvips.github.io/pyvips/vimage.html#pyvips.Image.dzsave

    vips.Image.dzsave(
        vi,
        dir_name,
        basename=base_name,
        suffix=file_format,
        tile_size=dims,
        overlap=0,
        depth="one",
        properties=False,
    )

    # delete .dzi file
    pathlib.Path(f"{dir_name}/{base_name}.dzi").unlink()


def create_tiles(
    slide_path, mpp=MPP, tile_dims=DIMS, file_format=FMT, output_dir=OUT_DIR
):
    t = Timer()

    vi = utils.read_image(slide_path)

    vi = rescale_slide(vi, mpp=mpp)
    coords = fit_tiles(vi, dims=tile_dims)

    vi = center_crop(vi, coords)

    coords_str = f"{coords[2] // 2}-{coords[3] // 2}"
    base_name = f"{slide_path.name}_mpp-{mpp}_crop{coords_str}"

    output_path = pathlib.Path(f"{output_dir}/{base_name}_files")
    if output_path.is_dir():
        print("- tiles already exist, will skip this slide")
        return output_path

    deepzoom_save(
        vi, base_name, dir_name=output_dir, dims=tile_dims, file_format=file_format
    )

    print(f"- time elapsed: {t.elapsed()}")

    return output_path


def save_tiles_csv(output_path, file_format=FMT, relative_paths=True):
    tiles = [_ for _ in output_path.glob(f"0/*{file_format}")]
    print(f"- directory {output_path}/ has {len(tiles)} {file_format} tiles")

    if relative_paths:
        # "output/tiles/CMU-1.svs_mpp-0.5_crop106-72_files/0/31_27.png"
        # .parents[0]: 'output/tiles/CMU-1.svs_mpp-0.5_crop106-72_files/0'
        # .parents[2]: 'output/tiles'
        tiles = [t_path.relative_to(t_path.parents[2]) for t_path in tiles]

    tiles_df = pd.DataFrame({"tile_path": tiles})
    tiles_csv = f"{output_path.parents[0]}/{output_path.name}-tile_path.csv"
    tiles_df.to_csv(tiles_csv, index=False)
    print(f"- tile_path data saved to {tiles_csv}")


# TODO: extract this function (it is repeated from filters.py)
def consolidate_tiles_csvs(output_dir, consolidated_csv, glob_pattern):
    output_dir_path = pathlib.Path(output_dir)
    dfs = [pd.read_csv(_) for _ in output_dir_path.glob(glob_pattern)]
    consolidated_df = pd.concat(dfs, ignore_index=True)
    consolidated_df.to_csv(consolidated_csv, index=False)
    print(f"tiles info consolidated and saved to {consolidated_csv}")


def run_tiling(
    slide_csv,
    consolidated_csv,
    output_dir=OUT_DIR,
    mpp=MPP,
    tile_dims=DIMS,
    file_format=FMT,
):
    slides_df = pd.read_csv(slide_csv)
    slides_df = slides_df.convert_dtypes()

    num_slides = len(slides_df)

    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)

    for idx, row in slides_df.iterrows():
        slide_path = pathlib.Path(row["slide_path"])
        print(f"[{idx + 1}/{num_slides}] {slide_path}")

        tiles_path = create_tiles(
            slide_path,
            mpp=mpp,
            tile_dims=tile_dims,
            file_format=file_format,
            output_dir=output_dir,
        )

        save_tiles_csv(tiles_path, file_format=file_format)

    consolidate_tiles_csvs(output_dir, consolidated_csv, "*-tile_path.csv")
