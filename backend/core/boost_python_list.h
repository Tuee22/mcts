#pragma once

#include <type_traits>
#include <vector>
#include <list>
#include <deque>

namespace boost_python_utils{

// forward declaration of functor 
template<typename T, typename Inner_Type> struct stl_to_pylist_functor;

// type trait to determine innermost type of nested STL containers
template<typename T> struct stl_base_type {using type = T;};
template<typename T> struct stl_base_type<std::vector<T>> : stl_base_type<T> {};
template<typename T> struct stl_base_type<std::list<T>> : stl_base_type<T> {};
template<typename T> struct stl_base_type<std::deque<T>> : stl_base_type<T> {};

// Nested_Container is a type representing a a nested series of stl
// containers (e.g. a vector of deques of lists etc) eventually terminating
// in some non-stl type (e.g. double or boost::python::object).
// This function will return an equivalent python list of lists, duplicating
// the exact same nesting.
template <typename Nested_Container>
boost::python::list recursive_stl_to_list(const Nested_Container& c)
{
  // get template type of this stl container
  typedef typename Nested_Container::value_type T;

  boost::python::list lst;
  std::for_each(c.cbegin(), c.cend(), [&](const T& t)
  {
    lst.append(stl_to_pylist_functor<T, typename stl_base_type<T>::type>()(t));
  });

  return lst;
}

// functor to take an element of some type T and
// 1) return a boost::python::list of T is not Inner_Type, or
// 2) just return that element back if T is Inner_Type.
template<typename T, typename Inner_Type>
struct stl_to_pylist_functor
{
  // Method that takes in an argument of type T and returns a list,
  // by calling recursive_vect_to_list. Only want to be enabled when
  // T is not the same type as IT.
  template <typename Q = T, typename IT = Inner_Type>
  typename std::enable_if<!std::is_same<Q, IT>::value, boost::python::list>::type
  operator()(const Q & t) const
  {
    return recursive_stl_to_list(t);
  }

  // naive method that just passes through the argument. We want to use this
  // when there are no further levels of recursion. Only want to be enabled
  // when T is the same type as IT.
  template <typename Q = T, typename IT = Inner_Type>
  typename std::enable_if<std::is_same<Q, IT>::value, const Q & >::type
  operator()(const Q & t) const
  {
    return t;
  }
};

template <typename Container>
void list_to_stl(const boost::python::list& lst, Container& vec) {
  typedef typename Container::value_type T;
  boost::python::stl_input_iterator<T> beg(lst), end;
  std::for_each(beg, end, [&](const T& t) { vec.push_back(t); });
}

} // namespace boost_python_utils