#include <ostream>
#include <iostream>
#include <ctime>
#include <vector>
#include <limits>

#define TYPE unsigned short
const TYPE max = 65535; // value returned by std::numeric_limits<unsigned short>::max();

class numeric_test_no_init
{
    public:
        numeric_test_no_init() noexcept
        {
            return;
        }
    private:
        TYPE _l;
};

class numeric_test_zero_init
{
    public:
        numeric_test_zero_init() noexcept
        {
            _l=max;
        }
    private:
        TYPE _l;
};

class numeric_test_max_init
{
    public:
        numeric_test_max_init() noexcept
        {
            _l=std::numeric_limits<TYPE>::max();
        }
    private:
        TYPE _l;
};

int main() {
    
    size_t inner_size = 1000000;
    size_t outer_size = 1000;
    clock_t begin, end;
    double elapsed_secs;

    begin = clock();
    for (size_t i=0;i<outer_size;++i)
        std::vector<numeric_test_no_init> no_init(inner_size);
    end = clock();
    elapsed_secs = double(end - begin) / CLOCKS_PER_SEC;
    std::cout << "numeric_test_no_init took " << elapsed_secs << " seconds." << std::endl;
    
    begin = clock();
    for (size_t i=0;i<outer_size;++i)
        std::vector<numeric_test_zero_init> zero_init(inner_size);
    end = clock();
    elapsed_secs = double(end - begin) / CLOCKS_PER_SEC;
    std::cout << "numeric_test_zero_init took " << elapsed_secs << " seconds." << std::endl;

    begin = clock();
    for (size_t i=0;i<outer_size;++i)
        std::vector<numeric_test_max_init> max_init(inner_size);
    end = clock();
    elapsed_secs = double(end - begin) / CLOCKS_PER_SEC;
    std::cout << "numeric_test_max_init took " << elapsed_secs << " seconds." << std::endl;

    return 0;
}