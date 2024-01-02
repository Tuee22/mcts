#pragma once
#include <limits>

class numeric_test_no_init
{
    public:
        numeric_test_no_init() noexcept
        {
            return;
        }
    private:
        unsigned long _l;
};

class numeric_test_zero_init
{
    public:
        numeric_test_zero_init() noexcept
        {
            _l=0;
        }
    private:
        unsigned short _l;
};

class numeric_test_max_init
{
    public:
        numeric_test_max_init() noexcept
        {
            _l=std::numeric_limits<unsigned short>::max();
        }
    private:
        unsigned long _l;
};

