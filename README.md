# ZenoBlend

Integrate the [ZENO node system](https://github.com/zenustech/zeno) into Blender for creating robust physics animations!

# End-user Installation

Goto [Release page](https://github.com/zenustech/zenoblend/releases), and click Assets -> download `zeno-linux-20xx.x.x.zip`.

Then, start Blender and `Edit -> Preferences -> Add-ons -> Install`, and choose the file you just downloaded.
Afterwards, type 'Zeno' in the search bar, and tick the `Physics: Zeno Blend` line it pops in.

# Developer Build

## Setup

First of all, please run this command:
```bash
git submodule update --init --recursive
```
To fetch ZENO which is included a submodule.

## Requirements

> For configurations of ZENO, please refer to [the README of ZENO itself](https://github.com/zenustech/zeno/blob/master/README.md).
> This README will focus on ZenoBlend itself here.

You need **Python 3.9** cause latest Blender use it too.

### Ubuntu 20.04

```bash
apt-get install -y python3.9-dev
```

### Windows

Install **Python 3.9** with a `.msi` from https://www.python.org, and add it to PATH.

## Build

> NOTE: It's suggested to use Blender 2.93 or 3.0, other versions are untested now thus may not work.

### Linux

```bash
cmake -B build -DPYTHON_EXECUTABLE=$(which python3.9)
cmake --build build --parallel
```

### Windows

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release

@rem Use this if you are using vcpkg:
@rem cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_TOOLCHAIN_FILE=[path to vcpkg]/scripts/buildsystems/vcpkg.cmake
```

Then open ```build/zenoblend.sln``` in Visual Studio 2019, and **switch to Release mode in build configurations**, then run `Build -> Build All`.

IMPORTANT: In MSVC, Release mode must **always be active** when building ZENO, since MSVC uses different allocators in Release and Debug mode. If a DLL of Release mode and a DLL in Debug mode are linked together in Windows, it will crash when passing STL objects.

## Run

### Linux

```bash
./debug.py
```
