################################################################
## DON'T RUN THIS FILE, THIS IS FOR QUICK DEBUG FOR ARCHIBATE ##
################################################################

run: all
	optirun blender ~/Documents/zenoblendprefer.blend -P blender.py -p 0 0 940 1080

dist: all
	./linux_dist.py

all:
	./build.py
