#include "boost_python_utils.h"
#include <boost/python/exception_translator.hpp>
#include "corridors_threaded_api.h"

using namespace boost_python_utils;

namespace p = boost::python;
namespace np = boost::python::numpy;
namespace sm = shallow_matrix;

BOOST_PYTHON_MODULE(_corridors_mcts) {
    Py_Initialize();
    np::initialize();

    // register std::string as a handled exception type.
    // now any C++ function can throw std::string("Some error message")
    // and the message will be sent to the user in Python.
    p::register_exception_translator<std::string>(
        [] (const std::string & e) {
            PyErr_SetString(PyExc_RuntimeError, e.c_str());
        }
    );

    p::class_<corridors_threaded_api,boost::noncopyable>(
        "_corridors_mcts",
        p::init
        <const double,
        const Seed, 
        const size_t, 
        const size_t, 
        const size_t>())
    .def("display", &corridors_threaded_api::display)
    .def("make_move", &corridors_threaded_api::make_move)
    .def("get_sorted_actions", &corridors_threaded_api::get_sorted_actions)
    .def("ensure_sims",&corridors_threaded_api::ensure_sims)
    .def("get_evaluation",&corridors_threaded_api::get_evaluation)
    .def("set_state_and_make_best_move",&corridors_threaded_api::set_state_and_make_best_move);
}