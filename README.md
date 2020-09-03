# wsi-preprocessing

Simple library for preprocessing histopathological whole-slide images (WSI) towards deep learning.

This project is a series of simple scripts that wraps [pyvips](https://github.com/libvips/pyvips) and builds upon [lucasrla/wsi-tile-cleanup](https://github.com/lucasrla/wsi-tile-cleanup).

Features:

- Find the whole-slide image (WSI) resolution (in microns per pixel, MPP) via [OpenSlide](https://github.com/openslide)
- Calculate the [Otsu threshold](https://en.wikipedia.org/wiki/Otsu%27s_method) for whole-slide image (WSI) via [lucasrla/wsi-tile-cleanup](https://github.com/lucasrla/wsi-tile-cleanup)
- Set the target MPP (say, 0.5) and the tile dimensions (say, 224px) and let libvips do its (**fast!**) magic to create tiles from whole-slide images (WSI)
- Compute masks on tiles for filtering out unneeded tiles via [lucasrla/wsi-tile-cleanup](https://github.com/lucasrla/wsi-tile-cleanup)

For an example of an actual pipeline (built with [SoS Workflow](https://github.com/vatlab/sos)) that uses `wsi_preprocessing`, see [lucasrla/wsi-preprocessing-sos-workflow](https://github.com/lucasrla/wsi-preprocessing-sos-workflow).


## Installation

### Conda

```sh
conda create --name YOUR_ENV_NAME --channel conda-forge python=3.6 libvips pyvips numpy
conda activate YOUR_ENV_NAME

# note: `python3.6 -m pip` is just to make sure we are using pip from python=3.6
python3.6 -m pip install git+https://github.com/lucasrla/wsi-preprocessing.git
```

### pip or poetry

```sh
# first of all, install libvips 
# https://libvips.github.io/libvips/install.html
# (tip: have it installed with openslide support)

# next, create a new virtualenv and activate it using your tool of choice
# (e.g., pyenv, virtualenv, etc)

# then, depending on your dependency manager, run either:
poetry add git+https://github.com/lucasrla/wsi-preprocessing.git
# or
pip install git+https://github.com/lucasrla/wsi-preprocessing.git
```

## Usage

If you don't have a whole-slide image available in your local machine, you need to download one first. I suggest you this one: [http://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/CMU-1.svs](http://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/CMU-1.svs) (170 MB). It is hosted by the folks that created the great [OpenSlide](https://openslide.org) at [CMU](https://www.cs.cmu.edu/~satya/).

```python
# example.py

import wsi_preprocessing as pp

# if, for instance, CMU-1.svs is in your current directory ("."):
slides = pp.list_slides(".")
pp.save_slides_mpp_otsu(slides, "slides_mpp_otsu.csv")

# this may take a few minutes (depending on your local machine, of course)
pp.run_tiling("slides_mpp_otsu.csv", "tiles.csv")

pp.calculate_filters("slides_mpp_otsu.csv", "", "tiles_filters.csv")
```

```sh
python3.6 example.py
```

Voilà! After running `example.py`, you will have the defaults:

- `png` tiles (at `0.5` mpp) that have `224x224` pixels generated from your whole-slide image
- `csv` files with metadata that will enable you filter out most of the gibberish


## Credits and Acknowledgments

Just like `wsi_tile_cleanup`, please note that `wsi_preprocessing` is just a very thin wrapper around `libvips`, `pyvips` and `numpy`. They are the ones doing the heavy lifting (and doing it amazingly well).

Besides them, I should also mention:

- [OpenSlide](https://github.com/openslide): makes it possible to do digital pathology on an open source environment. They also host [several test files that you easily can peruse online](http://openslide.cs.cmu.edu/download/openslide-testdata/).


## License

`wsi-preprocessing` is [Free Software](https://www.gnu.org/philosophy/free-sw.html) distributed under the [GNU General Public License v3.0](https://choosealicense.com/licenses/gpl-3.0/).

Dependencies have their own licenses, check them out.