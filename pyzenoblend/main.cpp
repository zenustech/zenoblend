#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <zeno/zeno.h>
namespace py = pybind11;


PYBIND11_MODULE(pyzenoblend_pybind11_module, m) {
    py::register_exception_translator([](std::exception_ptr p) {
        try {
            if (p)
                std::rethrow_exception(p);
        } catch (zeno::BaseException const &e) {
            PyErr_SetString(PyExc_RuntimeError, e.what());
        }
    });
}
