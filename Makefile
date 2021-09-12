################################################################
## DON'T RUN THIS FILE, THIS IS FOR QUICK DEBUG FOR ARCHIBATE ##
################################################################

run: all
	ZEN_LOGLEVEL=trace optirun blender -P blender.py ~/Documents/tutor.blend -p 0 0 940 1080

debug: all
	ZEN_LOGLEVEL=trace gdb blender -ex 'r -P blender.py ~/Documents/sss.blend -p 0 0 940 1080'

lastrun: all
	optirun blender -P blender.py ~/Documents/testlineviewer.blend -p 0 0 940 1080

oldrun: all
	optirun blender -P blender.py ~/Documents/testspraypars.blend -p 0 0 940 1080

baterun: all
	optirun blender ~/Documents/testvoronoi.blend -P blender.py -p 0 0 940 1080

zhxxrun: all
	~/Downloads/blender-2.93.3-linux-x64/blender ~/Documents/zenoStair.blend -P blender.py

dist: all
	./dist.py

all:
	cmake -B build
	cmake --build build --parallel 12
