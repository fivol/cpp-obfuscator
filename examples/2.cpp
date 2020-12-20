#include <iostream>
#include <vector>

using namespace std;

void f(int n){
    for(int i = 0; i < n; ++i){
        cout << i;
    }
}

vector<int> g(int n){
    vector<int> v;
    for(int i = 0; i < n; ++i){
        v.emplace_back(v);
    }
    return v;
}

int main(){
    f(0);
    g(123);

    return 0;
}