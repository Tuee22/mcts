#pragma once
#include <cstdint>
// code taken from https://mail.python.org/pipermail/cplusplus-sig/2009-May/014505.html

namespace boost_python_utils{

#define PYTHON_ERROR(TYPE, REASON) \
{ \
    PyErr_SetString(TYPE, REASON); \
    throw boost::python::error_already_set(); \
}

template<class T>
inline PyObject * managingPyObject(T *p)
{
    return typename boost::python::manage_new_object::apply<T *>::type()(p);
}

template<class Copyable>
boost::python::object
generic__copy__(boost::python::object copyable)
{
    Copyable *newCopyable(new Copyable(boost::python::extract<const Copyable
&>(copyable)));
    boost::python::object
result(boost::python::detail::new_reference(managingPyObject(newCopyable)));

    boost::python::extract<boost::python::dict>(result.attr("__dict__"))().update(
        copyable.attr("__dict__"));

    return result;
}

template<class Copyable>
boost::python::object
generic__deepcopy__(boost::python::object copyable, boost::python::dict memo)
{
    boost::python::object copyMod = boost::python::import("copy");
    boost::python::object deepcopy = copyMod.attr("deepcopy");

    Copyable *newCopyable(new Copyable(boost::python::extract<const Copyable
&>(copyable)));
    boost::python::object
result(boost::python::detail::new_reference(managingPyObject(newCopyable)));

    // HACK: copyableId shall be the same as the result of id(copyable) in Python -
    // please tell me that there is a better way! (and which ;-p)
    //int copyableId = (int)(copyable.ptr());
    int copyableId = reinterpret_cast<std::uintptr_t>(copyable.ptr()); // MN: changed casting to avoid precision loss error from compiler
    memo[copyableId] = result;

    boost::python::extract<boost::python::dict>(result.attr("__dict__"))().update(
        deepcopy(boost::python::extract<boost::python::dict>(copyable.attr("__dict__"))(),
memo));

    return result;
}

} // namespace boost_python_utils