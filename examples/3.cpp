#include <iostream>

class HelloWorld{
    HelloWorld(){
        int variable = 0;
    }

    ~HelloWorld(){

    }

    void printHello(){
        cout << "Hello world" << '\n';
    }
}

int main(){
    HelloWorld hello;

    hello.printHello();

    return 0;
}