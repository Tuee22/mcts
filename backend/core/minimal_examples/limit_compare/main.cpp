#include <ostream>
#include <iostream>
#include <ctime>
#include <vector>
#include <limits>

#define TYPE unsigned short

int main() {
    
    TYPE max_value=std::numeric_limits<TYPE>::max();

    if (max_value==std::numeric_limits<TYPE>::max())
    {
        std::cout << "matches" << std::endl;
    }
    else
    {
        std::cout << "doesn't match" << std::endl;
    }

    return 0;
}