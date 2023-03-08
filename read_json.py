class read:

    import json
    import Metashape
    # read json file

    json_file = Metashape.app.getOpenFileNames("Open JSON file with input variables")[0]
    input_data = json.load(open(json_file))
    print("INPUT DATA-------------------------------------")
    print(input_data)

    # json variables:
    # ---------------

    # - general
    convert_crs = input_data["convert_CRS"]
    crs_input_str = input_data["CRS_Input"]
    crs_output_str = input_data["CRS_Output"]

    # - analyze photos
    image_quality_threshold = input_data["analyzePhotos"]["image_quality_threshold"]

    # - align photos
    align_accuracy = input_data["align"]["align_accuracy"]
    mask_tiepoints = input_data["align"]["mask_tiepoints"]
    generic_preselection = input_data["align"]["generic_preselection"]
    reference_preselection = input_data["align"]["reference_preselection"]
    keypoint_limit = input_data["align"]["keypoint_limit"]
    tiepoint_limit = input_data["align"]["tiepoint_limit"]

    convert_crs = input_data["convert_CRS"]
    crs_input_str = input_data["CRS_Input"]
    crs_output_str = input_data["CRS_Output"]
    image_quality_threshold = input_data["analyzePhotos"]["image_quality_threshold"]
    align_accuracy = input_data["align"]["align_accuracy"]
    mask_tiepoints = input_data["align"]["mask_tiepoints"]

    detectMarkers = input_data["detectMarkers"]
    placeMarker = input_data["placeMarker"]

    # - optimize alignment
    optimizeCameras = input_data["optimizeCameras"]

    # - buil depth maps
    depth_map_quality = input_data["buildDepthMaps"]["depth_map_quality"]
    depth_filtering = input_data["buildDepthMaps"]["depth_filtering"]
    reuse_depth = input_data["buildDepthMaps"]["reuse_depth"]

    # - build Models
    buildModel = input_data["buildModel"]
    calibrateColors = input_data["calibrateColors"]
    buildUV = input_data["buildUV"]
    buldTexture = input_data["buldTexture"]
    buildTileModel = input_data["buildTileModel"]
    buildDem = input_data["buildDem"]
    buildOrthomosaic = input_data["buildOrthomosaic"]

    # - build ortho
    surface_data = input_data["buildOrthomosaic"]["surface_data"]

    # - export models

    # -- ortho
    exportOrtho = input_data["exportOrtho"]
    image_compression = exportOrtho["image_compression"]
  

    # -- dem
    exportDEM = input_data["exportDEM"]

    # print json settings
    def pr(input_data=input_data):
        print("---project setting:")
        for i in input_data:
            print("-->",i,":", input_data[i])
