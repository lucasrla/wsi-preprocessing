import wsi_preprocessing as pp

# if, for instance, CMU-1.svs is in your current directory:
slides = pp.list_slides(".")

pp.save_slides_mpp_otsu(slides, "slides_mpp_otsu.csv")

# this may take some minutes, depending on your local machine
pp.run_tiling("slides_mpp_otsu.csv", "tiles.csv")

pp.calculate_filters("slides_mpp_otsu.csv", "", "tiles_filters.csv")
