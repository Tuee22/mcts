#include <ostream>
#include <iostream>
#include <ctime>
#include <vector>
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

int main() {
    
    size_t i = 1000000000;
    clock_t begin, end;
    double elapsed_secs;

    begin = clock();
    std::vector<numeric_test_no_init> no_init(i);
    end = clock();
    elapsed_secs = double(end - begin) / CLOCKS_PER_SEC;
    std::cout << "numeric_test_no_init took " << elapsed_secs << " seconds." << std::endl;
    
    begin = clock();
    std::vector<numeric_test_zero_init> zero_init(i);
    end = clock();
    elapsed_secs = double(end - begin) / CLOCKS_PER_SEC;
    std::cout << "numeric_test_zero_init took " << elapsed_secs << " seconds." << std::endl;

    begin = clock();
    std::vector<numeric_test_max_init> max_init(i);
    end = clock();
    elapsed_secs = double(end - begin) / CLOCKS_PER_SEC;
    std::cout << "numeric_test_max_init took " << elapsed_secs << " seconds." << std::endl;

    return 0;
}