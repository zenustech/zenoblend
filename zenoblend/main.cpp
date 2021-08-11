#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <blender/DNA_mesh_types.h>
#include <blender/DNA_meshdata_types.h>
namespace py = pybind11;


PYBIND11_MODULE(zenoblend_pybind11_module, m) {
    m.def("testMesh", [] (uintptr_t vertPtr, size_t vertCount) {
        auto vert = reinterpret_cast<MVert const *>(vertPtr);
        for (int i = 0; i < vertCount; i++) {
            printf("%f %f %f\n"
                    , vert[i].co[0]
                    , vert[i].co[1]
                    , vert[i].co[2]
            );
        }
    });
}
