######################################################################
# Agisoft Metashape script for full workflow (tested on rice field data)
######################################################################
# SCRIPT B
#
# Agisoft Metashape and Python is needed for processing
#
# Devoloped for Agisoft Metashape 1.8.3
#
# Author: Mischa Bauckhage
# Date: 08.02.2023
# e-mail: mischa.bauckhage@bluewin.ch
#
######################################################################

import os
import Metashape
import read_json
import math
import sys
import importlib
# alway reload json to get adjusted parameters from json file
importlib.reload(read_json)
from read_json import read


# GET MAIN APP OBJECTS
doc = Metashape.app.document
app = Metashape.Application()

# Check if only part of script should be run
rerun=False
rerun_chunk=0
part=0

if doc.chunks[0].model != None:
    rerun = app.getBool("Run a part of script (and following parts) again?")
    if rerun:
        rerun_chunk = 0
        if len(doc.chunks)==2:
            rerun_chunk = app.getInt("0: Run for both chunks (RGB and Spectral) \n1: Run only for RGB chunk \n2: Run only for Spectral chunk")
        part = app.getInt("0: optimize \n1: build dense cloud \n2: build model \n3: buld texture \n4: build tile model \n5: build DEM \n6: build orthomosaic",2)
        print("---RUN AGAIN...")
        print("- Chunks:",rerun_chunk)
        print("- From part:", part)

# reload json if script does not run the first time
if doc.chunks[0].model != None or rerun:
    print("Reload json file...")
    import read_json
    importlib.reload(read_json)
    from read_json import read

# IMPORT SHAPES
shapes = app.getBool("Do you want to import shapes?")
if shapes:
    path_marker = Metashape.app.getOpenFileNames("Select shape file")
    shape = Metashape.Shape.BoundaryType.OuterBoundary
    crs = Metashape.app.getCoordinateSystem("CRS",Metashape.CoordinateSystem("EPSG::2056"))

# READ JSON FILE
convert_crs = read.convert_crs
crs_input_str = read.crs_input_str
crs_output_str = read.crs_output_str
image_quality_threshold = read.image_quality_threshold
align_accuracy = read.align_accuracy
mask_tiepoints = read.mask_tiepoints
detectMarkers = read.detectMarkers
depth_map_quality = read.depth_map_quality
depth_filtering = read.depth_filtering
reuse_depth = read.reuse_depth
exportOrtho = read.exportOrtho
image_compression = read.image_compression
exportDEM = read.exportDEM
optimizeCameras = read.optimizeCameras

surface_data_sources = {
    "PointCloudData":Metashape.DataSource.PointCloudData,
    "DenseCloudData":Metashape.DataSource.DenseCloudData,
    "DepthMapsData":Metashape.DataSource.DepthMapsData,
    "ModelData": Metashape.DataSource.ModelData,
    "TiledModelData":Metashape.DataSource.TiledModelData,
    "ElevationData":Metashape.DataSource.ElevationData,
    "OrthomosaicData":Metashape.DataSource.OrthomosaicData,
    "ImagesData":Metashape.DataSource.ImagesData
    }
surface_data = surface_data_sources[read.buildOrthomosaic["surface_data"]]

targets = {
      "CircularTarget12bit":Metashape.CircularTarget12bit,
      "CircularTarget14bit":Metashape.CircularTarget14bit,
      "CircularTarget16bit":Metashape.CircularTarget16bit,
      "CircularTarget20bit":Metashape.CircularTarget20bit,
      "CircularTar":Metashape.CircularTarget,
      "CrossTarget":Metashape.CrossTarget
   }

image_formats = {
    "None":Metashape.ImageFormat.ImageFormatNone,
    "JPEG":Metashape.ImageFormat.ImageFormatJPEG,
    "TIFF":Metashape.ImageFormat.ImageFormatTIFF,
    "PNG":Metashape.ImageFormat.ImageFormatPNG,
    "BMP":Metashape.ImageFormat.ImageFormatBMP,
    "EXR":Metashape.ImageFormat.ImageFormatEXR,
    "PNM":Metashape.ImageFormat.ImageFormatPNM,
    "SGI":Metashape.ImageFormat.ImageFormatSGI,
    "CR2":Metashape.ImageFormat.ImageFormatCR2,
    "SEQ":Metashape.ImageFormat.ImageFormatSEQ,
    "BIL":Metashape.ImageFormat.ImageFormatBIL,
    "XYZ":Metashape.ImageFormat.ImageFormatXYZ,
    "ARA":Metashape.ImageFormat.ImageFormatARA,
    "TGA":Metashape.ImageFormat.ImageFormatTGA,
    "DDS":Metashape.ImageFormat.ImageFormatDDS,
    "JP2":Metashape.ImageFormat.ImageFormatJP2,
    "WebP":Metashape.ImageFormat.ImageFormatWebP,
    "JXL":Metashape.ImageFormat.ImageFormatJXL
}


ortho_format = image_formats[exportOrtho["image_format"]]  
dem_format = image_formats[exportDEM["image_format"]]  

data_sources = {
    "PointCloud": Metashape.DataSource.PointCloudData,
    "DenseCloud": Metashape.DataSource.DenseCloudData,
    "DepthMaps": Metashape.DataSource.DepthMapsData,
    "Model": Metashape.DataSource.ModelData,
    "TileModel": Metashape.DataSource.TiledModelData,
    "Elevation": Metashape.DataSource.ElevationData,
    "Orthomosaic": Metashape.DataSource.OrthomosaicData,
    "Images": Metashape.DataSource.ImagesData,
}

data_source = data_sources[exportDEM["source_data"]]

def optimize(chunk):
    # OPTIMIZE CAMERAS
    print("---OPTIMIZE CAMERAS "+str(chunk.label)+"...")
    print("settings: ",optimizeCameras)

    chunk.optimizeCameras(
        fit_f=optimizeCameras["fit_f"],
        fit_cx=optimizeCameras["fit_cx"],
        fit_cy=optimizeCameras["fit_cy"],
        fit_b1=optimizeCameras["fit_b1"],
        fit_b2=optimizeCameras["fit_b2"],
        fit_k1=optimizeCameras["fit_k1"],
        fit_k2=optimizeCameras["fit_k2"],
        fit_k3=optimizeCameras["fit_k3"],
        fit_k4=optimizeCameras["fit_k4"],
        fit_p1=optimizeCameras["fit_p1"],
        fit_p2=optimizeCameras["fit_p2"],
        fit_corrections=optimizeCameras["fit_corrections"],
        adaptive_fitting=optimizeCameras["adaptive_fitting"],
        tiepoint_covariance=optimizeCameras["tiepoint_covariance"],
        )
    print("camera optimization done")

    # SAVE PROJECT
    print("---Saving project...")
    doc.save()
    print("saved successfully")

def buildDense(chunk):
    # BUILD DENSE MODEL
    print("---BUILD DENSE MODEL "+str(chunk.label)+"...")
    filters = {
        "no":Metashape.NoFiltering,
        "mild":Metashape.MildFiltering,
        "moderate":Metashape.ModerateFiltering,
        "aggressive":Metashape.AggressiveFiltering
    }

    chunk.buildDepthMaps(
        downscale=depth_map_quality,
        filter_mode=filters[depth_filtering],
        reuse_depth=reuse_depth)

    # BUILD DENSE CLOUD
    print("---Build Dense Cloud...")
    chunk.buildDenseCloud()

    # SAVE PROJECT
    print("---Saving project...")
    doc.save()
    print("saved successfully")

def buildModel(chunk):
    # BUILD MODEL
    print("---BUILD MODEL "+str(chunk.label)+"...")
    chunk.buildModel()

    # SAVE PROJECT
    print("---Saving project...")
    doc.save()
    print("saved successfully")

def texture(chunk):
    # CALIBRATE COLORS
    print("---CALIBRATE COLORS "+str(chunk.label)+"...")
    chunk.calibrateColors()

    # SAVE PROJECT
    print("---Saving project...")
    doc.save()
    print("saved successfully")

    # BUILD TEXTURE
    print("---BUILD TEXTURE "+str(chunk.label)+"...")
    chunk.buildUV()
    chunk.buildTexture()

    # SAVE PROJECT
    print("---Saving project...")
    doc.save()
    print("saved successfully")

def tile(chunk):
    # BUILD TILE MODEL
    print("---BUILD TILE MODEL "+str(chunk.label)+"...")
    chunk.buildTiledModel()    

    # SAVE PROJECT
    print("---Saving project...")
    doc.save()
    print("saved successfully")

def dem(chunk):
    # BUILD DEM
    print("---BUILD DEM "+str(chunk.label)+"...")
    chunk.buildDem()

    # SAVE PROJECT
    print("---Saving project...")
    doc.save()
    print("saved successfully")

def ortho(chunk):
    # BUILD ORHTOMOSAIC
    print("---BUILD ORTHOMOSAIC "+str(chunk.label)+"...")
    chunk.buildOrthomosaic(
        surface_data=surface_data
    )

    # SAVE PROJECT
    print("---Saving project...")
    doc.save()
    print("saved successfully")

    # SAVE PROJECT
    print("---Saving project...")
    doc.save()
    print("saved successfully")

def export(chunk,spectral=False):

    HomeDirectory = os.path.dirname(doc.path)
    project_name = os.path.basename(doc.path).split(".")[0]
    
    chunk.raster_transform.enabled = False

    # EXPORT ORTHOMSAIC
    print("---EXPORT ORTHOMOSAIC  "+str(chunk.label)+"...")
    
    output_ortho = os.path.join(HomeDirectory,project_name+'_'+chunk.label+'_ortho.tif')
    compression = Metashape.ImageCompression()
    compression.tiff_big = image_compression["tiff_big"]
    compression.tiff_tiled = image_compression["tiff_tiled"]
    compression.tiff_overviews = image_compression["tiff_overviews"]
    compression.tiff_compression = image_compression["tiff_compression"]
    compression.jpeg_quality = image_compression["jpeg_quality"]


    chunk.exportRaster(
        path=output_ortho,
        image_format=ortho_format,
        block_height=exportOrtho["block_height"],
        block_width=exportOrtho["block_width"],
        image_compression=compression,
        clip_to_boundary=True,
        raster_transform=Metashape.RasterTransformNone
        )
    
    # EXPORT DEM
    print("---EXPORT DEM  "+str(chunk.label)+"...")
    output_dem = os.path.join(HomeDirectory,project_name+'_'+chunk.label+'_dem.tif')
    chunk.exportRaster(
        path=output_dem,
        image_format=dem_format,
        source_data=data_source,
        clip_to_boundary=True
    )
    # EXPORT REPORT
    print("---EXPORT REPORT "+str(chunk.label)+"... ")
    output_report = os.path.join(HomeDirectory,project_name+'_'+chunk.label+'_report.pdf')
    chunk.exportReport(
        path=output_report,
        title=project_name)

    # CALCULATE AND EXPORT NDVI FOR SPECTRAL
    if spectral:
        print("---CALCULATE NDVI "+str(chunk.label)+"...")
        # ndvi formula
        formula = ['(B5-B3)/(B5+B3)']
        # apply transformation
        chunk_Spectral = chunk
        chunk_Spectral.raster_transform.formula = formula
        chunk_Spectral.raster_transform.calibrateRange()
        chunk_Spectral.raster_transform.enabled = True
        
        # define output name of NDVI file
        output_ndvi = os.path.join(HomeDirectory,project_name+'_'+chunk.label+'_NDVI.tif')

        # export file
        print("---EXPORT NDVI ORTHO "+str(chunk.label)+"...")
        chunk.exportRaster(
            path=output_ndvi,
            image_format=ortho_format,
            block_height=exportOrtho["block_height"],
            block_width=exportOrtho["block_width"],
            image_compression=compression,
            clip_to_boundary=True,
            raster_transform=Metashape.RasterTransformValue
            )


chunks = doc.chunks
if rerun:
    if rerun_chunk==0: chunks = doc.chunks
    if rerun_chunk==1: chunks=[doc.chunks[0]]
    if rerun_chunk==2: chunks=[doc.chunks[1]]

for chunk in chunks:

    #if chunk.label != 'Spectral':continue
    print("START PROCESSING",chunk.label,"...")
    print("------------------------------")

    # import shapes for all chunks
    if shapes:
        chunk.importShapes(
            path=path_marker,
            boundary_type=shape,
            format=Metashape.ShapesFormat.ShapesFormatSHP,
            crs=crs
            )

    if part==0:
        optimize(chunk)
        part += 1
    if part==1:
        buildDense(chunk)
        part += 1
    if part==2:
        buildModel(chunk)
        part += 1
    if part==3:
        texture(chunk)
        part += 1
    if part==4:
        tile(chunk)
        part += 1
    if part==5:
        dem(chunk)
        part += 1
    if part==6:
        ortho(chunk)
        part += 1

    part = 0

# export RGB chunk
print("---EXPORT CHUNK",doc.chunks[0].label)
export(doc.chunks[0],spectral=False)
print("CHUNK",doc.chunks[0].label,"DONE")
print("-------------------------------")

# export Spectral
if len(doc.chunks)>= 2 and doc.chunks[0].label == 'RGB' and doc.chunks[1].label == 'Spectral':
    print("---EXPORT CHUNK",doc.chunks[1].label)
    export(doc.chunks[1],spectral=True)
    print("CHUNK",doc.chunks[1],"DONE")
    print("-------------------------------")


app.messageBox("Part B done: Check result!")