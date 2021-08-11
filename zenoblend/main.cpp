#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "blender.h"
namespace py = pybind11;
namespace bl = blender_2_83;


PYBIND11_MODULE(zenoblend_pybind11_module, m) {
    m.def("testMesh", [] (uintptr_t meshPtr) {
        auto mesh = reinterpret_cast<bl::Mesh const *>(meshPtr);
        printf("hello\n");
        printf("%p\n", mesh);
        printf("%p\n", mesh->mvert);
        printf("%f %f %f\n"
                , mesh->mvert->co[0]
                , mesh->mvert->co[1]
                , mesh->mvert->co[2]
        );
    });
}
