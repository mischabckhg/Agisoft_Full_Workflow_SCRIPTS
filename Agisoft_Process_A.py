######################################################################
# Agisoft Metashape script for full workflow (tested on rice field data)
######################################################################
# SCRIPT A
#
# Agisoft Metashape and Python is needed for processing
#
# Devoloped for Agisoft Metashape 1.8.3
#
# Author: Mischa Bauckhage
# Date: 07.02.2023
# e-mail: mischa.bauckhage@bluewin.ch
#
######################################################################

import os
import Metashape
from read_json import read
import math
import importlib
import json
import time

# GET MAIN APP OBJECTS
doc = Metashape.app.document
app = Metashape.Application()

# Get home folder
if doc.chunk == None or len(doc.chunk.cameras) == 0:
    HomeDirectory = Metashape.app.getExistingDirectory("Select project folder:")
    project_name = Metashape.app.getSaveFileName("Save Project As")
    
# Check if only part of script should be run
rerun=False
if doc.chunk!= None and len(doc.chunks[0].cameras) > 0:
    rerun = app.getBool("Run a part of script again? 'No' if everything should be ran again")
    if rerun:
        rerun_chunk = 1
        if len(doc.chunks)==2:
            rerun_chunk = app.getInt("0: Run for both chunks (RGB and Spectral) \n1: Run only for RGB chunk \n2: Run only for Spectral chunk")
        part = app.getInt("2: Align photos and detect marker \n3: Place marker \n4: Calibrate reflectance",2)
        if part==2:
            conv_crs = app.getBool("Do again CRS conversion?")

# reload json if script does not run the first time
if doc.chunk!= None and len(doc.chunk.cameras) > 0 or rerun:
    print("Reload json file...")
    import read_json
    importlib.reload(read_json)
    from read_json import read

# make temp folder at location of scripts
temp_folder = os.path.join(os.path.dirname(__file__),"temp")
if not os.path.exists(temp_folder):
    os.mkdir(temp_folder)

# SAVE PROJECT
print("--- Save project...")
if doc.chunk!= None and len(doc.chunks[0].cameras)>0:
    doc.save()
    print("saved successfully")
elif doc.chunk== None or len(doc.chunks[0].cameras)==0:
    os.chdir(HomeDirectory)
    print("Home directory: " + HomeDirectory)
    try:
        doc.save(project_name + '.psx')
    except RuntimeError:
        Metashape.app.messageBox("Can't save project")

# existing project: define chunks
if doc.chunk!= None and len(doc.chunks[0].cameras) > 0:
    for chunk in doc.chunks:
        if chunk.label == "RGB": chunk_RGB=chunk
        if chunk.label == "Spectral":
            chunk_Spectral=chunk
            spectral=True

# new project: create chunk
if doc.chunk==None or len(doc.chunks[0].cameras) == 0:
    chunk_RGB = None
    chunk_Spectral = None
    if not doc.chunk:
        doc.addChunk()
    chunk_RGB = doc.chunk
    chunk_RGB.label = 'RGB'
    spectral = app.getBool("Add Multispectral cameras?")
    print("SPECTRAL:",spectral)
    if spectral:    
        chunk_Spectral = doc.addChunk()
        chunk_Spectral.label = 'Spectral'

# get crs of chunks
crs_input =  chunk_RGB.crs
crs_output = chunk_RGB.crs


# read json files
convert_crs = read.convert_crs
crs_input_str = read.crs_input_str
crs_output_str = read.crs_output_str
image_quality_threshold = read.image_quality_threshold
align_accuracy = read.align_accuracy
generic_preselection = read.generic_preselection
reference_preselection = read.reference_preselection
keypoint_limit = read.keypoint_limit 
tiepoint_limit = read.tiepoint_limit
mask_tiepoints = read.mask_tiepoints
detectMarkers = read.detectMarkers
placeMarker = read.placeMarker

targets = {
      "CircularTarget12bit":Metashape.CircularTarget12bit,
      "CircularTarget14bit":Metashape.CircularTarget14bit,
      "CircularTarget16bit":Metashape.CircularTarget16bit,
      "CircularTarget20bit":Metashape.CircularTarget20bit,
      "CircularTarget":Metashape.CircularTarget,
      "CrossTarget":Metashape.CrossTarget
   }

# ----------------------------
# PART 01 LOAD
# This script builds up the project, imports photos, gcp and saves the project
# ----------------------------

# write cameras to txt file
def spectral_camera_list(chunk,bands, darkest_band):
    print("Number of bands:",bands)
    print("Darkest band:",darkest_band)
    with open(os.path.join(temp_folder,"cameras.txt"), mode = "w") as f:
        for i in range(1,len(chunk.cameras)):
            if i%bands==0:
                cam = chunk.cameras[i-(bands+1-darkest_band)].label
                f.write(str(cam)+'\n')

# load all parameters
def load(chunk_RGB,chunk_Spectral=None,spectral=False):

    bands=0
    darkest_band=0
    panelWidth=0
    gsd=0
    dist_faktor=0
    do_seg=True

    # REMOVE EXISTING MARKER AND PHOTOS
    print("---> remove existing markers and cameras")
    for chunk in doc.chunks:
        for marker in chunk.markers:
            print("----> remove marker:",marker.label)
            chunk.remove(marker)
        for camera in chunk.cameras:
            print("----> remove camera:",camera.label)
            chunk.remove(camera)

    # DEFINE PHOTOS PATH
    if spectral:
        print("spectral 1 = ",spectral)
        path_photos = Metashape.app.getExistingDirectory("Select parent folder of RGB and Spectral photos folder:")
        assert os.path.exists(os.path.join(path_photos,'RGB')), "Folder 'RGB' does not exist!"
        assert os.path.exists(os.path.join(path_photos,'Spectral')), "Folder 'Spectral' does not exist!"
        path_photos_RGB = os.path.join(path_photos,'RGB')
        path_photos_Spectral = os.path.join(path_photos,'Spectral')
        path_photos_Segmentation = os.path.join(path_photos,'Segmentation')
        # ask for bands if segmentation wasn't done yet
        if not os.path.exists(path_photos_Segmentation) or len(os.listdir(path_photos_Segmentation))==0:
            if not os.path.exists(path_photos_Segmentation): print("seg folder doesn not exist")
            if os.path.exists(path_photos_Segmentation) and len(os.listdir(path_photos_Segmentation))==0: print("seg folder empty")
            bands = app.getInt("Number of bands...",5)
            darkest_band = app.getInt("Darkest band... (for rice normally R-Band (1))",1)
            print("bands:",bands)
            print("darkest band:",darkest_band)
            # delete files from temp folder, so it's empty at the beginning of the process
            for filename in os.listdir(temp_folder):
                os.remove(os.path.join(temp_folder,filename))

        # ask to do segmentation again if already done. If it should be done again, delete all files from segmentation directory and temp directory
        elif os.path.exists(path_photos_Segmentation):
            print("seg folder exists already")
            if len(os.listdir(path_photos_Segmentation))!=0:
                print("len of seg folder:",len(os.listdir(path_photos_Segmentation)))
                do_seg=app.getBool("Do segmentation again?")
                print("do seg:",do_seg)
                if do_seg:
                    bands = app.getInt("Number of bands...",5)
                    darkest_band = app.getInt("Darkest band... (for rice normally R-Band (1))",1)
                    print("bands:",bands)
                    print("darkest band:",darkest_band)
                    # delete files from temp folder, so it's empty at the beginning of the process
                    for filename in os.listdir(path_photos_Segmentation):
                        os.remove(os.path.join(path_photos_Segmentation,filename))
                    for filename in os.listdir(temp_folder):
                        os.remove(os.path.join(temp_folder,filename))
                elif not do_seg:
                    print("don't do segmentation again")
                    with open(os.path.join(temp_folder,"done.txt"),mode="w") as f: f.write(" ")
    else:
        print("spectral 2: ",spectral)
        path_photos_RGB = Metashape.app.getExistingDirectory("Select photos folder:")

    # DEFINE MARKER PATH
    path_marker = Metashape.app.getOpenFileNames("Select marker file")

    # DEFINE PROCESSING SETTINGS
    print("---Defining processing settings...")
    read.pr()

    # DETECT MARKER IN SPECTRAL IMAGES
    if spectral and do_seg:
        panelWidth = app.getFloat("Rough GCP panel size (m):",0.3)
        app.getBool("Run batch file: run_spectralDetect.bat \n Continue?")

    # SET COORDINATE SYSTEM
    print("---Settings coordinate system...")
    # init coordinate system object
    crs_input = Metashape.app.getCoordinateSystem("Chunk coordinate system before convert",Metashape.CoordinateSystem(crs_input_str))
    crs_output = Metashape.app.getCoordinateSystem("Coordinates to convert chunk to",Metashape.CoordinateSystem(crs_output_str))

    # LOAD AERIAL IMAGE
    image_list_RGB = os.listdir(path_photos_RGB)
    if spectral:
        image_list_Spectral = os.listdir(path_photos_Spectral)
        print("Photos path Spectral: ",path_photos_Spectral)
    print("Photos path RGB: ",path_photos_RGB)
    photo_list_RGB = list()
    photo_list_Spectral = list()

    print(photo_list_RGB)

    for photo in image_list_RGB:
        photo_list_RGB.append("/".join([path_photos_RGB, photo]))
    chunk_RGB.addPhotos(photo_list_RGB)

    if spectral:
        for photo in image_list_Spectral:
            photo_list_Spectral.append("/".join([path_photos_Spectral,photo]))
        chunk_Spectral.addPhotos(photo_list_Spectral,layout=Metashape.MultiplaneLayout)

    print("Photos added to chunks")

    # save camera list 
    if spectral and do_seg:
        spectral_camera_list(chunk_Spectral,bands,darkest_band)

    # LOAD MARKER
    print("--- import marker...")
    for chunk in doc.chunks:
        chunk.importReference(
            path=path_marker,
            format=Metashape.ReferenceFormatCSV,
            delimiter=",",
            skip_rows=1,
            crs=Metashape.CoordinateSystem("EPSG::2056"),
            items=Metashape.ReferenceItemsMarkers,
            columns="nyxz",
            create_markers=True
            )
    print("marker import done")


    # SAVE PATHS AND PARAMETERS TO JSON FILE
    if spectral and do_seg:
        cam = chunk_Spectral.cameras[0]
        f = cam.sensor.focal_length / 1000
        dist = round(abs(cam.reference.location[2] - chunk_Spectral.markers[0].reference.location[2]),1)
        
        print("Dist:")
        gsd = (dist * cam.sensor.pixel_width/1000)/f
        dist_faktor = round(dist/10)

        locations = {
            "home":HomeDirectory,
            "photos":path_photos,
            "marker":path_marker[0],
            "panelWidth":panelWidth,
            "gsd": gsd,
            "dist_faktor":dist_faktor
        }
        output = os.path.join(temp_folder,"locations.json")
        print(output)
        j = json.dumps(locations)
        f = open(output,"w")
        f.write(j)
        f.close()
    

    # SAVE PROJECT
    print("---Saving project...")
    doc.save()
    print("saved successfully")

    return crs_input, crs_output

# load only markers
def load_markers():
    # REMOVE EXISTING MARKER
    for chunk in doc.chunks:
        for marker in chunk.markers:
            chunk.remove(marker)
    # DEFINE MARKER PATH
    path_marker = Metashape.app.getOpenFileNames("Select marker file")
    # LOAD MARKER
    print("--- import marker...")
    for chunk in doc.chunks:
        chunk.importReference(
            path=path_marker,
            format=Metashape.ReferenceFormatCSV,
            delimiter=",",
            skip_rows=1,
            crs=Metashape.CoordinateSystem("EPSG::2056"),
            items=Metashape.ReferenceItemsMarkers,
            columns="nyxz",
            create_markers=True
            )

# ----------------------------
# PART 02 ALIGN
# This script calculates quality, aligns the photos, and detects the Markers
# ----------------------------
def spectral_detect(chunk, centers):
    
    print("---DETECT SPECTRAL MARKERS...")
    # separate gcp and detected markers
    marker_gcp = []
    marker_detect = []
    for marker in chunk.markers:
        if str.__contains__(marker.label,"point"):
            marker_detect.append(marker)
        else: marker_gcp.append(marker)

    # iterate over all cameras
    for num, camera in enumerate(chunk.cameras):
        # only look for R-channel cameras       
        if camera.label in centers and camera.transform != None:
            print('\n',camera,"->",camera.label,centers[camera.label])
            # check if a marker was detected in the selected image
            if len(centers[camera.label])!=0:
                # iterate over all markers
                for i in range(len(centers[camera.label])):
                    x = centers[camera.label][i][0]
                    y = centers[camera.label][i][1]
                    point = Metashape.Vector((x,y))
                    sensor = camera.sensor
                    pointPick = chunk.point_cloud.pickPoint(camera.center, camera.transform.mulp(sensor.calibration.unproject(point)))
                    # create marker
                    created_marker = chunk.addMarker(point = pointPick)
                    marker_detect.append(created_marker)
                    print("--->",marker_detect)

                    check = True
                    if len(marker_detect)>=2:
                        for num, m in enumerate(marker_detect):
                            # remove marker if marker at same position already exists
                            if check and m!=marker_detect[-1] and abs(m.position.x - created_marker.position.x)<= 0.1:
                                print(num, "same point found:",m,m.position,created_marker.label,created_marker.position)
                                chunk.remove(created_marker)
                                print(num, "chunk.remove",created_marker)
                                marker_detect = marker_detect[:-1]
                                print(num, "removed from list:",marker_detect)
                                check =False

    # remove markers that are too close to each other
    print("--------------------")
    t = []
    for m in chunk.markers:
        for n in chunk.markers:
            if m not in t and m.label != n.label and abs(m.position.x - n.position.x) <= 0.12:
                print(m.label, n.label, m.position.x, n.position.x)
                t.append(n)
    for i in t:
        print(i)
        chunk.remove(i)

def align(chunk_RGB,crs_input,crs_output,chunk_Spectral=None,rgb=True,spectral=False,convert_crs=True):


    def disable_cameras(chunk_RGB, image_quality_threshold):
        # disable images with bad quality
        count_disabled = 0
        for i in range(0, len(chunk_RGB.cameras)):
            camera = chunk_RGB.cameras[i]
            camera.enabled = True
            quality = float(camera.frames[0].meta["Image/Quality"])
            if quality < image_quality_threshold:
                camera.enabled = False
                count_disabled += 1
                print("Camera", camera, "disabled: Qaulity", quality)
        return count_disabled

    # CONVERT REFERENCE
    if convert_crs:

        print("CRS before convert: ",crs_input,type(crs_input))
        print("CRS after convert: ",crs_output,type(crs_output))

        if rgb: chunk_RGB.crs = crs_input
        if spectral: chunk_Spectral.crs = crs_input


        # CONVERT IMAGES
        print("---convert images---")
        if rgb:
            for camera in chunk_RGB.cameras:
                if camera.reference.location:
                    camera.reference.location = Metashape.CoordinateSystem.transform(camera.reference.location, chunk_RGB.crs, crs_output)
        
        if spectral:
            for camera in chunk_Spectral.cameras:
                if camera.reference.location:
                    camera.reference.location = Metashape.CoordinateSystem.transform(camera.reference.location, chunk_Spectral.crs, crs_output)
        print("convertion done")
        
        print("---set new chunk crs---")
        chunk_RGB.crs = crs_output 
        if spectral: chunk_Spectral.crs = crs_output
        print("new crs for RGB chunk:", chunk_RGB.crs)
        if spectral: print("new crs for Spectral chunk:", chunk_Spectral.crs)

    # SAVE PROJECT
    print("---Saving project...")
    doc.save()

    # CALCULATE IMAGE QUALITY
    print("---calculate image quality---")
    if rgb: chunk_RGB.analyzePhotos()
    if spectral: chunk_Spectral.analyzePhotos()

    # disable cameras with image quality below threshold
    if rgb:
        count_disabled = disable_cameras(chunk_RGB,image_quality_threshold)
        # calculate percantage of cameras with bad quality
        perc_disabled = count_disabled/len(chunk_RGB.cameras)*100
        # if more than 40% are with bad quality, ask if yout want to continue or change threshold parameter
        while perc_disabled > 5:
            prompt_threshold = app.getBool(str(str(round(perc_disabled))+"% of the cameras are disabled! Do you want to change the quality threshold?"))
            if prompt_threshold:
                image_quality_threshold_update = app.getFloat("Set new threshold for image quality...",image_quality_threshold)
                count_disabled = disable_cameras(chunk_RGB,image_quality_threshold_update)
                perc_disabled = count_disabled/len(chunk_RGB.cameras)*100
                print("DISABLED IMAGES:",perc_disabled,"%")
            elif not prompt_threshold:
                prompt_continue = app.getBool("Do you want to abort the process?")
                if not prompt_continue: return

    # SAVE PROJECT
    print("---Saving project...")
    doc.save()


    # All init done! Ready to start processing.
    # -----------------------------------------

    # ALIGN PHOTOS
    for chunk in doc.chunks:
        print("---Match photos ...")
        chunk.matchPhotos(
            downscale=align_accuracy,
            generic_preselection=generic_preselection,
            mask_tiepoints=mask_tiepoints,
            reference_preselection=reference_preselection,
            keypoint_limit=keypoint_limit,
            tiepoint_limit=tiepoint_limit)
        print("---Align Cameras for",chunk,"...")
        chunk.alignCameras()
        print("---> alignment done...")


    # DETECT MARKERS RGB
    print("######################## marker detect:",print(len(doc.chunks[0].markers)))
    if len(doc.chunks[0].markers) != 0:
        target = targets[detectMarkers["target_type"]]
        tolerance = detectMarkers["tolerance"]
        if rgb: chunk_RGB.detectMarkers(target_type=target,tolerance=tolerance)

        if spectral:
            done_file = os.path.join(temp_folder,"done.txt")
            if not os.path.exists(done_file):
                print("Waiting for Marker Detection...")
                while not os.path.exists(done_file):time.sleep(1)
            os.remove(done_file)
            json_centers = os.path.join(temp_folder,"centers.json")
            centers = json.load(open(json_centers))
            spectral_detect(chunk_Spectral, centers)

    # SAVE PROJECT
    print("---Saving project...")
    doc.save()
    print("saved successfully")

# ----------------------------
# PART 03 PLACE MARKER
# This script places the gcp according to the detected markers from 02 ALIGN
# ----------------------------
def findSecondSmallest(lst):
    temp_lst = lst.copy()
    temp_lst.sort()
    index = lst.index(temp_lst[1])
    return index

def place(chunk_RGB=None,chunk_Spectral=None,spectral=False,convert_crs=True):

    
    chunk = chunk_RGB
    if spectral: chunk = chunk_Spectral
    if chunk==None: return
    # save gcp markers and detected markers in separate lists
    marker_gcp = []
    marker_detect = []
    for marker in chunk.markers:
        if str.__contains__(marker.label,"point"):
            marker_detect.append(marker)
        else: marker_gcp.append(marker)

    # PLACE MARKER
    print("--- PLACE MARKER...")
    print("-> search radius:",placeMarker["search_radius"])
    # iterate through all cameras
    pairs = []
    if len(marker_gcp)!=0:
        for count, camera in enumerate(chunk.cameras):

            # iterate through all markers
            for marker in marker_detect:
                # look only at marker that is in this camera
                if camera in marker.projections.keys():
                    print("Camera",camera,"Marker",marker)
                    # calculate position between self detected marker and gcp
                    dist_to_gcp = []
                    marker_gcp_tuple = []
                    for marker2 in marker_gcp:
                        dist = 0.0
                        point_detect = (marker.position.x, marker.position.y)
                        point_gcp = (marker2.position.x, marker2.position.y)
                        dist = math.dist(point_detect,point_gcp)
                        dist_to_gcp.append(dist)
                        marker_gcp_tuple.append((marker, marker2))
                        assert len(marker_gcp_tuple) == len(dist_to_gcp), "list length to not match"
            
                    # Minimum element indices in list
                    temp = min(dist_to_gcp)
                    index = [i for i, j in enumerate(dist_to_gcp) if j == temp][0]

                    mark = marker_gcp_tuple[index][0]
                    mark2 = marker_gcp_tuple[index][1]
                    pair_tuple = (mark,mark2)

                    min_dist = min(dist_to_gcp)
                    second_mind_dist = dist_to_gcp[findSecondSmallest(dist_to_gcp)]

                    # check if marker should be considered
                    if 0.0 < min_dist <= placeMarker["search_radius"]:
                        
                        """
                        # uncomment to debug
                        for num,i in enumerate(marker_gcp_tuple):
                            if marker.label=='point 3':
                                print("Makrer:",i[0],i[1],"distance:",dist_to_gcp[num])
                        """

                        # define pair level: 1=perfect match, 2=medium match
                        if 2*min_dist < second_mind_dist:
                            pair_level = 1
                        elif  2*min_dist >= second_mind_dist:
                            pair_level = 2
                        
                        # check if pair already exists:
                        pair = [pair_tuple,pair_level]
                        print("Pair",pair)
                        check = False
                        # append pari to list if list is empty
                        if len(pairs) == 0:
                            pairs.append(pair)
                            print("NEW LIST (len=0)",pairs)
                        # if list no empty...
                        elif pair not in pairs:
                            print("pair not in list!")
                            for p in pairs:
                                # check if theres a different match to the detected marker and if the match is better (pair_level=1 instead of pair_level=2)
                                detectet_marker = p[0][0]
                                gcp_marker = p[0][1]
                                if detectet_marker==marker and gcp_marker!=marker2 and pair_level==1:
                                    # if the match is better (pair_level=1) replace gcp
                                    p[0][1] = marker2
                                    p[1] = pair_level
                                    print(".............................")
                                    print("GCP",gcp_marker,"replaced by",p[0][1])
                                    print("NEW LIST (replaced):",pairs)
                                    print(".............................")
                                    check=True
                            # append pair to list if it was not replaced
                            if not check:
                                pairs.append(pair)
        print("LIST\n",pairs)
    
        # APPLY MARKER COORDINATES TO GCPs
        print("Apply markers for chunk",chunk.label)
        for camera in chunk.cameras:
            for markers_ in pairs: # replace "pairs" with "final_list" to use changed list
                m_detect = markers_[0][0]
                m_gcp = markers_[0][1]
                
                if camera in m_detect.projections.keys():
                    print("--> place",m_detect,"with",m_gcp)
                    m_gcp.projections[camera] = m_detect.projections[camera]
    
    if len(doc.chunks)==1: app.messageBox(str("Part A done: Check ground control points:"+str([str(x[0][1].label) for x in pairs if x[1]==2])+"for chunk"+str(chunk.label)))
    

    # REMOVE DETECTED MARKERS
    print("--- REMOVE MARKERS...")
    for marker in marker_detect:
        chunk.remove(marker)

    # SAVE PROJECT
    print("---Saving project...")
    doc.save()
    print("saved successfully")

# ----------------------------
# PART 04 CALIBRATE REFLECTANCE
# This script calibrates the sun sensor
# ----------------------------
def calibrateReflectance(chunk_=chunk_Spectral):
    print("--- CALIBRATE REFLECTANCE...")
    print("---> image brightness for chunk",chunk_.label,": 5000%")
    print("---> image contrast for chunk",chunk_.label,": 70%")
    chunk_.calibrateReflectance(use_reflectance_panels=False, use_sun_sensor=True)
    

# ----------------------------
# run all funtions
# ----------------------------

# run all parts
if not rerun:
    crs_input, crs_output = load(chunk_RGB,chunk_Spectral=chunk_Spectral,spectral=spectral)
    align(chunk_RGB,crs_input,crs_output,chunk_Spectral=chunk_Spectral,spectral=spectral)
    place(chunk_RGB)
    if spectral:
        place(chunk_Spectral=chunk_Spectral,spectral=True)
        calibrateReflectance(chunk_Spectral)

# run only selected parts
elif rerun:
    # rerun 02 ALIGN
    if part==2:
        if rerun_chunk==0:
            load_markers()
            align(chunk_RGB,crs_input,crs_output,chunk_Spectral=chunk_Spectral,rgb=True, spectral=True, convert_crs=conv_crs)
        if rerun_chunk==1: align(chunk_RGB,crs_input,crs_output,chunk_Spectral=chunk_Spectral,rgb=True, spectral=False,convert_crs=conv_crs)
        if rerun_chunk==2:
            load_markers()
            align(chunk_RGB,crs_input,crs_output,chunk_Spectral=chunk_Spectral,rgb=False,spectral=True, convert_crs=conv_crs)
    # reurn 03 PLACE
    if part==3:
        if rerun_chunk==0:
            place(chunk_RGB)
            place(chunk_Spectral=chunk_Spectral,spectral=True)
        if rerun_chunk==1: place(chunk_RGB)
        if rerun_chunk==2: place(chunk_Spectral=chunk_Spectral,spectral=True)
    # rerun 04 CALIBRATE REFLECTANCE
    if part ==4:
        if spectral:
            """
            for chunk in doc.chunks:
                if chunk.label=="Spectral":
                    chunk_Spectral=chunk"""
            calibrateReflectance(chunk_Spectral)

if spectral: app.messageBox("Part A done: Check all ground control points for RGB and Spectral chunk! Adjust the image brightness as required!")