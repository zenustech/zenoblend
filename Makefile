################################################################
## DON'T RUN THIS FILE, THIS IS FOR QUICK DEBUG FOR ARCHIBATE ##
################################################################

run: all
	optirun blender ~/Documents/zenoblendprefer.blend -P debug.py -p 0 0 940 1080

dist: all
	./dist.py

all:
	./build.py
