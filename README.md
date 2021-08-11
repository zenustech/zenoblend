# ZENO Addon Wizard

Demo project showing on how to add custom nodes to ZENO.

# Setup

First of all, run this command:
```bash
git submodule update --init --recursive
```
To fetch ZENO which is included a submodule.

## Build

- Linux

```bash
cmake -B build
cmake --build build --parallel
```

- Windows

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
```

Then open ```build/zeno_addon_wizard.sln``` in Visual Studio 2019, and **switch to Release mode in build configurations**, then run `Build -> Build All`.

IMPORTANT: In MSVC, Release mode must **always be active** when building ZENO, since MSVC uses different allocators in Release and Debug mode. If a DLL of Release mode and a DLL in Debug mode are linked together in Windows, it will crash when passing STL objects.

## Run

```bash
./run.py
```

Then open `graphs/MyPrimitiveOps.zsg` and click `Run`.

# Coding

The `YourProject/` is a demo project for showing how to add custom nodes in ZENO with its C++ API.

See [MyPrimitiveOps.cpp](YourProject/MyPrimitiveOps.cpp) for custom primitive operation.
See [CustomNumber.cpp](YourProject/CustomNumber.cpp) for defining custom object.

Let me know if you need more demos here by opening an [issue](https://github.com/zenustech/zeno_addon_wizard/issues).
