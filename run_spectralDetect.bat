@echo ON

call C:\Programme\Anaconda3\Scripts\activate.bat
call conda activate GIS
python SpectralMarkerDetect.py
pause
