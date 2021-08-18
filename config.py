#!/usr/bin/env python3

import subprocess

args = [
'-DCMAKE_BUILD_TYPE=Release',
'-DZENOFX_ENABLE_OPENVDB:BOOL=ON',
'-DEXTENSION_oldzenbase:BOOL=ON',
'-DEXTENSION_ZenoFX:BOOL=ON',
'-DEXTENSION_Rigid:BOOL=OFF',
'-DEXTENSION_FastFLIP:BOOL=OFF',
'-DEXTENSION_zenvdb:BOOL=ON',
'-DZENO_ENABLE_PYTHON:BOOL=OFF',
'-DZENO_ENABLE_OPENMP:BOOL=ON',
'-DZENO_FAULTHANDLER:BOOL=ON',
'-DZENO_GLOBALSTATE:BOOL=OFF',
'-DZENO_VISUALIZATION:BOOL=OFF',
'-DZENO_BENCHMARKING:BOOL=OFF',
'-DZENO_BUILD_EXTENSIONS:BOOL=ON',
'-DZENO_FAIL_SILENTLY:BOOL=OFF',
'-DZENO_BUILD_TESTS:BOOL=OFF',
'-DZENO_BUILD_ZFX:BOOL=ON',
]

subprocess.check_call(['cmake', '-B', 'build'] + args)