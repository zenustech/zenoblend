################################################################
## DON'T RUN THIS FILE, THIS IS FOR QUICK DEBUG FOR ARCHIBATE ##
################################################################

run: all
	optirun blender ~/Documents/zenoStair.blend -P blender.py -p 0 0 940 1080

dist: all
	./dist.py

all:
	cmake -B build
	cmake --build build --parallel
