#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py = pybind11;

#include <blender/DNA_mesh_types.h>
#include <blender/DNA_meshdata_types.h>

#include <zeno/zeno.h>
#include <zeno/types/PrimitiveObject.h>


PYBIND11_MODULE(zenoblend_pybind11_module, m) {

    m.def("primitiveSetVertices", []
            ( uintptr_t primPtr
            , uintptr_t vertPtr
            , size_t vertCount
            ) -> void
    {
        auto prim = reinterpret_cast<zeno::PrimitiveObject *>(primPtr);
        prim->resize(vertCount);
        auto vert = reinterpret_cast<MVert const *>(vertPtr);
        auto &pos = prim->add_attr<zeno::vec3f>("pos");
        for (int i = 0; i < vertCount; i++) {
            pos[i] = {vert[i].co[0], vert[i].co[1], vert[i].co[2]};
        }
    });

    m.def("primitiveGetVerticesCount", []
            ( uintptr_t primPtr
            ) -> size_t
    {
        auto prim = reinterpret_cast<zeno::PrimitiveObject *>(primPtr);
        return prim->size();
    });

    m.def("primitiveGetVertices", []
            ( uintptr_t primPtr
            , uintptr_t vertPtr
            , size_t vertCount
            ) -> void
    {
        auto prim = reinterpret_cast<zeno::PrimitiveObject *>(primPtr);
        auto vert = reinterpret_cast<MVert const *>(vertPtr);
        auto &pos = prim->add_attr<zeno::vec3f>("pos");
        for (int i = 0; i < vertCount; i++) {
            pos[i] = {vert[i].co[0], vert[i].co[1], vert[i].co[2]};
        }
    });

}
