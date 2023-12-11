#pragma once

#include <boost/core/noncopyable.hpp>
#include <memory>
#include <string>
#include <vector>

namespace boost_python_utils{
namespace shallow_matrix{

class base;
typedef std::unique_ptr<base> mat;
typedef mat vec; // alias for vector

// call this factory to create a shallow matrix of the correct specialized type from the input
inline mat mat_factory(np::ndarray & input);
inline vec vec_factory(np::ndarray & input);
inline mat cupy_factory(p::object & input);

// abstract base class for storing rows and columns of a matrix and pointers to the data
class base : private boost::noncopyable
{
public:
    inline virtual ~base();

    inline size_t get_rows() const;
    inline size_t get_cols() const;
    inline size_t get_size() const;

    // attempt to get a pointer of a desired type (will return NULL if it's not valid)
    template <typename TYPE> const TYPE * data() const;
    template <typename TYPE> TYPE * data();

    // get data as a std::vector (makes a deep copy)
    template <typename TYPE> void get_vector(std::vector<TYPE> & vec) const;

    template <typename TYPE> std::vector<TYPE> asVector() const;

protected:
    inline base();
    char * _p; // use char * as a pointer to untyped data. This is to be consistent with return type of np::ndarray::get_data()
    size_t _rows, _cols;
};

// derived class involving specific data type (e.g. double, float)
template <typename T>
class typed : public base
{
public:
    typed(np::ndarray & input);
    typed(p::object & input);
    typed(T* p, const size_t rows, const size_t cols);
    void set_matrix(np::ndarray & input);
    void set_matrix(T* p, const size_t rows, const size_t cols);
    void set_cupy_ndarray(p::object & input);

    np::ndarray as_ndarray() const;
    const T* data() const;
    T* data();
};

// function to create a 2d ndarray from a specific C type
template <typename T>
np::ndarray make_2d_ndarray(const T * data, const size_t rows, const size_t cols);

// method and function definitions

mat mat_factory(np::ndarray & input)
{
    mat output;
    np::dtype dt = input.get_dtype();

    // double
    if (dt==np::dtype::get_builtin<double>())
        output.reset(new typed<double>(input));

    // float
    else if (dt==np::dtype::get_builtin<float>())
        output.reset(new typed<float>(input));

    // long long (int64 in python)
    else if (dt==np::dtype::get_builtin<long long>())
        output.reset(new typed<long long>(input));

    // otherwise throw
    else
        throw std::string("This dtype not supported-- C++ code may need to be generalized");

    return output;
}

vec vec_factory(np::ndarray & input)
{
    vec output(mat_factory(input));
    if (output->get_cols() != 1)
        throw std::string("Error: vectors can only have one dimension.");
    return output;
}

mat cupy_factory(p::object & input)
{
    mat output;
    // check type
    p::str dt = p::str(input.attr("dtype"));
    // double
    if (dt==p::str(np::dtype::get_builtin<double>()))
        output.reset(new typed<double>(input));

    // float
    else if (dt==p::str(np::dtype::get_builtin<float>()))
        output.reset(new typed<float>(input));

    // otherwise throw
    else
        throw std::string("This dtype not supported-- C++ code may need to be generalized");

    return output;
}

base::base()
{
    _p=NULL;
    _rows=_cols=0;
}

base::~base()
{
}

size_t base::get_rows() const
{
    return _rows;
}

size_t base::get_cols() const
{
    return _cols;
}

size_t base::get_size() const
{
    return _rows * _cols;
}

template <typename TYPE>
const TYPE * base::data() const
{
    // attempt to down-cast
    const typed<TYPE> * derived_p = dynamic_cast<const typed<TYPE>*>(this);

    // If the dyanmic cast succeeded, return a TYPE pointer
    // to the underlying data. Otherwise return a null pointer
    // to indicate that T is not the correct type.
    if (derived_p)
        return derived_p->data();
    else
        return NULL;
}

template <typename TYPE>
TYPE * base::data()
{
    // attempt to down-cast
    typed<TYPE> * derived_p = dynamic_cast<typed<TYPE>*>(this);

    // If the dyanmic cast succeeded, return a TYPE pointer
    // to the underlying data. Otherwise return a null pointer
    // to indicate that T is not the correct type.
    if (derived_p)
        return derived_p->data();
    else
        return NULL;
}

template <typename TYPE>
void base::get_vector(std::vector<TYPE> & vec) const
{
    size_t sze = _rows * _cols;
    if (sze == 0)
    {
        vec.resize(0);
        vec.shrink_to_fit();
    }
    else
    {
        const TYPE * ptr = data<TYPE>();
        if (!ptr)
            throw std::string("shallow_matrix Error: unable to convert to std::vector of desired type.");

        vec.resize(sze);
        for(size_t i=0;i<sze;++i)
            vec[i] = ptr[i];

        vec.shrink_to_fit();
    }
}

template <typename TYPE>
std::vector<TYPE> base::asVector() const
{
    std::vector<TYPE> vec;
    get_vector<TYPE>(vec);
    return vec;
}

template <typename T>
typed<T>::typed(np::ndarray & input) : base()
{
    set_matrix(input);
}

template <typename T>
typed<T>::typed(p::object & input) : base()
{
    set_cupy_ndarray(input);
}

template <typename T>
typed<T>::typed(T* p, const size_t rows, const size_t cols) : base()
{
    set_matrix(p, rows, cols);
}

template <typename T>
void typed<T>::set_matrix(T* p, const size_t rows, const size_t cols)
{
    _p = reinterpret_cast<char*>(p);
    _rows = rows;
    _cols = cols;
}

template <typename T>
void typed<T>::set_matrix(np::ndarray & input)
{
    // ensure the C_CONTIGUOUS flag is true
    if (!(input.get_flags() & np::ndarray::bitflag::C_CONTIGUOUS))
        throw std::string("C_CONTINUOUS flag must be true.");

    // ensure the WRITEABLE flag is true
    if (!(input.get_flags() & np::ndarray::bitflag::WRITEABLE))
        throw std::string("WRITEABLE flag must be true.");

    // check type is T
    np::dtype dt = input.get_dtype();
    np::dtype compare_dt = np::dtype::get_builtin<T>();
    if (dt != compare_dt)
        throw std::string("ndtype must match template type T");

    size_t nd = input.get_nd();

    // check that dimensions are 2
    if (!(nd ==1 || nd == 2))
        throw std::string("Matrices must have 2 dimensions.");

    // get rows and columns
    _rows = input.shape(0);

    if (nd==2)
        _cols = input.shape(1);
    else
        _cols = 1;

    // check that strides are exact (i.e. ensure the ndarray isn't a subset of some larger, contigiously-stored matrix)
    if  ( (size_t)input.strides(0) != _cols*sizeof(T) || (nd == 2 && (size_t)input.strides(1) != sizeof(T)) )
        throw std::string("Strides are not exact. Passed ndarray cannot be a (shallow) subset of another ndarray.");

    // get pointer to data
    _p = input.get_data();
}

template <typename T>
void typed<T>::set_cupy_ndarray(p::object & input)
{
    // ensure we're dealing with a cupy.ndarray
    if (p::str(input.attr("__class__"))!=p::str("<class 'cupy.core.core.ndarray'>"))
        throw std::string("Passed argument must be cupy.ndarray");

    // check type
    p::object dt = input.attr("dtype");
    np::dtype compare_dt = np::dtype::get_builtin<T>();
    if (p::str(dt) != p::str(compare_dt))
        throw std::string("ndtype must match template type T");

    // check flags
    p::object flags = input.attr("flags");
    if (!p::extract<bool>(flags.attr("c_contiguous")))
        throw std::string("Array must be c_contiguous");
    if (!p::extract<bool>(flags.attr("owndata")))
        throw std::string("Array must own data");

    // check that dimensions are 2
    p::object shape = input.attr("shape");
    size_t nd = p::extract<size_t>(shape.attr("__len__")());
    if (!(nd ==1 || nd == 2))
        throw std::string("Matrices must have 2 dimensions.");

    // get rows and columns
    _rows = p::extract<size_t>(shape[0]);

    if (nd==2)
        _cols = p::extract<size_t>(shape[1]);
    else
        _cols = 1;

    // check that strides are exact (i.e. ensure the ndarray isn't a subset of some larger, contigiously-stored matrix)
    p::object strides = input.attr("strides");
    if  ( p::extract<size_t>(strides[0]) != _cols*sizeof(T) || 
        (nd == 2 && p::extract<size_t>(strides[1]) != sizeof(T)) )
        throw std::string("Strides are not exact. Passed ndarray cannot be a (shallow) subset of another ndarray.");

    // check device number
    if (p::extract<size_t>(input.attr("data").attr("device").attr("id")) != 0)
        throw std::string("Memory must be allocated on cuda device 0.");

    // get pointer
    size_t _device_ptr = p::extract<size_t>(input.attr("data").attr("ptr"));
    _p = reinterpret_cast<char*>(_device_ptr);
}

template <typename T>
np::ndarray typed<T>::as_ndarray() const
{
    return make_2d_ndarray(data(), _rows, _cols);
}

template <typename T>
const T * typed<T>::data() const
{
    return reinterpret_cast<const T*>(_p);
}

template <typename T>
T * typed<T>::data()
{
    return reinterpret_cast<T*>(_p);
}

// creates a 2d ndarray of the specified type.
// note this makes a deep copy-- c++ is still responsible for deleting
// the pointer later. The resulting ndarray can be safely returned to python
// without any lifetime mgmt issues.
template <typename T>
np::ndarray make_2d_ndarray(const T * data, const size_t rows, const size_t cols)
{
    np::dtype dt = np::dtype::get_builtin<T>();
    p::tuple shape = p::make_tuple(rows, cols);
    p::tuple stride = p::make_tuple(cols*sizeof(T), sizeof(T));
    np::ndarray ret = np::from_data(data,dt,shape,stride,p::object());
    return ret.copy(); // copy makes the returned matrix deep
}

} // namespace shallow_matrix
} // namespace boost_python_utils