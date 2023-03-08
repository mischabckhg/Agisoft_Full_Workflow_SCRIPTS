# Agisoft_full_workflow
### Author: Mischa Bauckhage
### Date: 24.11.2022
### Contact: mischa.bauckhage@bluewin.ch

This code contains scripts for a full Agisoft worflow for ricefields drone flights. The main scirpts are the following:
- Agisoft_Process_A.py
- Agisoft_Process_B.py

Agisoft_Process_A:
- create project
- load photos
- load ground control points (gcp)
- load processing settings from json file
- align photos
- detect markers
- place gcp according to detectet markers

Agisoft_Process_B:
- optimize alignment
- build dense cloud
- build tile model
- build DEM
- buil Orthophoto
- export DEM, ortho and report

After script A is done, check detected and placed markers and gcp's. Then delete detected markers. Then run script B.

The workflow needs a json file with all parameters. A schema is included here. 

