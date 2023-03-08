import numpy as np
from cv2 import imread,imwrite, dilate, erode
from cv2 import cvtColor, COLOR_BGR2HLS, calcHist
import cv2 as cv
import random
import matplotlib as mpl
from matplotlib import pyplot as plt
#from skimage.measure import label
import os
import json
from tqdm import tqdm
import time
import datetime

# function to wait for required files
def waiting(file):
    a = "."
    if not os.path.exists(file):
        print("Waiting for Agisoft...")
        while not os.path.exists(file):
            a += "."
            print(a)
            time.sleep(1)
    if os.path.exists(file):
        print("Waiting for Agisoft (updating files)...")
        result = time.time()-os.stat(file).st_mtime
        if result > 60:
            td_str = str(datetime.timedelta(seconds=result))
            x = td_str.split(':')
            print(file,"is older than 60 seconds.", 'Time in hh:mm:ss:', x[0], 'Hours', x[1], 'Minutes', x[2], 'Seconds.',"Waiting to be updated...")
            while time.time()-os.stat(file).st_mtime > 60:
                a += "."
                print(a)
                time.sleep(1)
    
    

# get all directories and files
temp_folder = os.path.join(os.path.dirname(__file__),"temp")
locations_path = os.path.join(temp_folder,"locations.json")
waiting(locations_path)
locations = open(locations_path,"r")
location = json.load(locations)
photos_path = os.path.join(location["photos"],"Spectral")
parent = location["photos"]
panelWidth = location["panelWidth"]
gsd = location["gsd"]
dist_faktor = location["dist_faktor"]

# segmentation function
def find_target(img, panelWidth, gsd,dist_faktor):
    original_img = img
    image = cv.imread(img, cv.IMREAD_UNCHANGED)
    seg = (image > 45000)*1

    kernel=np.ones([21, 21], np.uint8)
    img = seg.astype('uint8') * 255
    img = cv.dilate(img,kernel,iterations=3)
    img = cv.erode(img,np.ones([5, 5], np.uint8),iterations=10)

    contours, hierarchy = cv.findContours(img, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    #conturs = cv.drawContours(sure_bg, contours, -1, (20,255,200), 3)
    center = []
    for i in contours:

        area = cv.contourArea(i)
        perimeter = cv.arcLength(i, True)
        perimeter = round(perimeter, 4)
        img1 = cv.drawContours(img, [i], -1, (0,255,255), 3)

        panel_area = (panelWidth/gsd)**2 * dist_faktor**2
        #print(original_img,"-> Area:",area,"PanelArea:",panel_area)

        if area < panel_area:
            
            # calculate moments of binary image
            M = cv.moments(i)

            # calculate x,y coordinate of center
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])

            #print(cX,cY)
            center.append([cX,cY])

            # put text highlight the center
            img = cv.circle(img, (cX, cY), 15, (120, 200, 200), -1)

    return img, center

# run segmention function
cameras = os.path.join(temp_folder,"cameras.txt")
waiting(cameras) 
while os.path.getsize(cameras)==0:
    print("Cameras not loaded yet...")
    time.sleep(1)
    
fileObject = open(cameras, "r")
data = fileObject.readlines()
count = 0
centers = {}
img_seg = []
for line in tqdm(data):
    count += 1
    strip = line.strip()
    s = strip + ".TIF"
    img, center = find_target(os.path.join(photos_path,s),panelWidth,gsd,dist_faktor)
    centers[strip]=center
    img_seg.append(img)

try:
    centers_file = os.path.join(temp_folder,'centers.txt')
    file = open(centers_file,'w')
    file.write(str(centers))
    file.close()
    print("Centers written to file:",centers_file)
    print("\n Export visualization...")
    with open(os.path.join(temp_folder,"done.txt"),mode="w") as f: f.write(" ")
except:
    print("Unable to write file")

j = json.dumps(centers)
f = open(os.path.join(temp_folder,"centers.json"),"w")
f.write(j)
f.close()

if not os.path.exists(os.path.join(parent,"Segmentation")):
    os.mkdir(os.path.join(parent,"Segmentation"))

for line, seg in tqdm(zip(data,img_seg)):
    strip = line.strip()
    s = strip + ".TIF"
    img = os.path.join(photos_path,s)
    fig, axis = plt.subplots(1, 2, figsize=(15,8))
    axis[0].imshow(cv.imread(img, cv.IMREAD_UNCHANGED),cmap=mpl.colormaps['gray'])
    axis[1].imshow(seg,cmap=mpl.colormaps['afmhot'])
    plt.savefig(os.path.join(parent,"Segmentation",strip+"_SEG.png"))
    mpl.pyplot.close()


print("---> Files stored under",os.path.join(parent,"Segmentation"))