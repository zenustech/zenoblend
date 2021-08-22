# ZenoBlend

Integrate the [ZENO node system](https://github.com/zenustech/zeno) into Blender for creating robust physics animations!

# Setup

First of all, please run this command:
```bash
git submodule update --init --recursive
```
To fetch ZENO which is included a submodule.

## Developer Build

> NOTE: It's suggested to use Blender 2.93 or 3.0, other versions are untested now thus may not work.

> For configurations of ZENO, please refer to [the README of ZENO itself](https://github.com/zenustech/zeno/blob/master/README.md).
> This README will focus on ZenoBlend itself here.

### Linux

```bash
cmake -B build
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
