################################################################
## DON'T RUN THIS FILE, THIS IS FOR QUICK DEBUG FOR ARCHIBATE ##
################################################################

x=testnewui

run: all
	ZEN_LOGLEVEL=trace optirun blender -P blender.py ~/Documents/$x.blend -p 0 0 940 1080

debug: all
	ZEN_LOGLEVEL=trace gdb blender -ex 'r -P blender.py ~/Documents/$x.blend -p 0 0 940 1080'

dist: all
	./dist.py

all:
	cmake -B build
	cmake --build build --parallel 12
