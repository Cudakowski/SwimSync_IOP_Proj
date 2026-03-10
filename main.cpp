#include <iostream> 
using namespace std; 
int multiply(int a, int b) {
  return a * b; 
} 

int subtract(int a, int b) {
  return a - b; 
} 

int add(int a, int b) { 
   return a + b; 
} 

int main() {
  cout << "Witaj w naszym programie!" << endl;
  cout << "2 + 3 = " << add(2,3) <<endl;
  cout << "2 * 3 = " << multiply(2, 3) << endl;
  cout << "5 - 3 = " << subtract(5, 3) << endl;
  return 0;
} 
