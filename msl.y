
%{
#include<cstdio>
#include<iostream>
#include <map>
#include<algorithm>
#include <string>       // std::string
#include <sstream>
#include<fstream>
#include<string.h>
#include<cstdlib>
#include <vector>
#include <cctype> // is*
#include <iostream>
using namespace std;

std::map<string,string> hosts;

std::map<std::string, std::ofstream> write_map; 
std::map<string,string> options12;
extern int yylex(); //called in a loop to get the next token
extern int yyparse();
extern FILE *yyin;
void yyerror(const char *s);
#define YYDEBUG 1
std::string last_file;
using namespace std;
std::string get_filename_from_comments(std::string text)
{
    if (text.rfind("#stepnum", 0) == 0) { // pos=0 limits the search to the prefix
        return "";
    } 
    char space_char = ' ';

    stringstream sstream(text);
    std::string word;
    std::string last;
    while (std::getline(sstream, word, space_char)){
        word.erase(std::remove_if(word.begin(), word.end(), ::isspace), word.end());
        last = word;
    }
    last_file = last;
    return last;
}


void create_file_and_put_in_map(  std::string comment)
{
    std::string file_name = get_filename_from_comments( comment );
};

int to_int(int c) {
    if (not isxdigit(c)) return -1; // error: non-hexadecimal digit found
    if (isdigit(c)) return c - '0';
    if (isupper(c)) c = tolower(c);
    return c - 'a' + 10;
}

template<class InputIterator, class OutputIterator> int
unhexlify(InputIterator first, InputIterator last, OutputIterator ascii) {
    while (first != last) {
        int top = to_int(*first++);
        int bot = to_int(*first++);
        if (top == -1 or bot == -1)
            return -1; // error
        *ascii++ = (top << 4) + bot;
    }
     return 0;
}

inline bool exists_file (const std::string& name) {
    ifstream f(name.c_str());
    return f.good();
}

string last_send_name;
void func_write(char *sendname, char *s) {
    last_send_name = string(sendname);
    if (last_send_name.find("Continuation") == std::string::npos) {
        if (exists_file ( last_file ))  {
            return; //not a contiunuation line, so the file should be written all once. 
                //this is to care of cases where 2 different actions are using same file name
        } 
    }
    s += 2; //jump 0h
    size_t len = strlen(s);
    size_t asciilen = len/2;
    char ascii[len/2+1];
    ascii[len/2] = '\0';

    if (unhexlify(s, s+len, ascii) < 0) {
        throw "Wrong in hex decoding";
        return ; // error
    }
    
    std::ofstream myfile;
    myfile.open(last_file.c_str(), std::ios::out | std::ios::binary | std::ios::app );
    myfile.write( ascii, asciilen);
}

%}
%define parse.trace
%union{
char *sval;
}

//define terminal tokens and associate them with something from union

%token <sval> SCENARIO
%token <sval> HOSTS
%token <sval> OPTIONS
%token <sval> STEPS
%token <sval> LEFTBRACE
%token <sval> RIGHTBRACE
%token <sval> LEFTBRACKET
%token <sval> RIGHTBRACKET
%token <sval> ASCIISTRING
%token <sval> ANDSTRING
%token <sval> DOLLARSTRING
%token <sval> EQUALTO
%token <sval> COLON
%token <sval> TCP
%token <sval> UDP
%token <sval> COMMA
%token <sval> DOT
%token <sval> CLIENTSEND
%token <sval> SERVERSEND
%token <sval> CLIENTRECEIVE
%token <sval> SERVERRECEIVE
%token <sval> STRINGLINE
%token <sval> NUMBERS
%token <sval> ANYSTAR
%token <sval> ATSTRING
%token <sval> LEFTRECTANGLE
%token <sval> RIGHTRECTANGLE
%token <sval> STRUCT
%token <sval> LINE
%token <sval> COMMENT
%token <sval> VARIABLES
%token <sval> REGEXSTRING
%token <sval> FILTER
%token <sval> ASSERTION

%start msl
%%
msl:
|COMMENT msl
|SCENARIO LEFTBRACE components RIGHTBRACE  {}
;
components:
|hosts components
|options components
|steps components
|variables components
|COMMENT components
;
hosts: HOSTS LEFTBRACE hostvals RIGHTBRACE  {}
;
hostvals: hostval
|hostvals hostval
;
hostval: ANDSTRING EQUALTO ASCIISTRING { /* cout << "Host: " << $1 << " Value: " << $3 << endl; */ }
|ANDSTRING EQUALTO functionwithbrackets
|ATSTRING EQUALTO ASCIISTRING
|ATSTRING EQUALTO functionwithbrackets
|COMMENT
;
variables: VARIABLES LEFTBRACE variablevals RIGHTBRACE
;
variablevals: 
|hostval variablevals
;
options: OPTIONS LEFTBRACE optionvals RIGHTBRACE {}
;
optionvals: optionval {}
|optionvals optionval {}
;
optionval: DOLLARSTRING EQUALTO ASCIISTRING { /* cout << "Option: " << $1 << " Value: " << $3 << endl; */ }
|COMMENT
;
steps: STEPS LEFTBRACE sockssendsrecvs RIGHTBRACE
;
sockssendsrecvs:
 
|sockcreate
|socksend
|sockreceive
|COMMENT sockssendsrecvs
;
sockreceive: receiveargs
sockssendsrecvs
;
receiveargs: ASCIISTRING EQUALTO receivename  {/*cout << "ServerReceive... \n";*/  }
|ASCIISTRING EQUALTO receivename LEFTBRACE recvpayload RIGHTBRACE {/*cout << "ServerReceive... \n";*/  }
;
receivename: ASCIISTRING DOT SERVERRECEIVE
|ASCIISTRING DOT CLIENTRECEIVE
;
recvpayload: ASSERTION LEFTBRACE assertpayload RIGHTBRACE
;
assertpayload: 
|ASCIISTRING assertpayload
|REGEXSTRING assertpayload
|COMMENT assertpayload
;
socksend: sendargs
sockssendsrecvs
;
sendpayload:
|juststring sendpayload
|bitstring sendpayload
|variablestring sendpayload
|functionwithbrackets sendpayload
|functionwithrectangles sendpayload
|linedata sendpayload
|structdata sendpayload
|functionwithbrackets LEFTRECTANGLE sendpayload RIGHTRECTANGLE sendpayload
|ASCIISTRING EQUALTO functionwithbrackets LEFTRECTANGLE sendpayload RIGHTRECTANGLE sendpayload
;
juststring: ASCIISTRING {/* cout << $1 << endl; */ }
|NUMBERS { /* cout << $1 << endl; */ }
|ATSTRING {/* cout << $1 << endl;*/}
|STRINGLINE
;
bitstring: ATSTRING COLON NUMBERS
|ATSTRING COLON ASCIISTRING
|ASCIISTRING COLON ASCIISTRING
|ASCIISTRING COLON NUMBERS
|ASCIISTRING COLON STRINGLINE
;
variablestring: ASCIISTRING EQUALTO juststring { /* cout << "1-Variable String detected " << $2 << endl;*/ }
|ASCIISTRING EQUALTO bitstring {  /*cout << "1-Variable String detected " << $2 << endl;*/ }
;
funcparam:juststring 
|bitstring
;
commaseparatedparams:
|funcparam 
|functionwithrectangles
|functionwithbrackets
|funcparam COMMA commaseparatedparams
|functionwithrectangles COMMA commaseparatedparams
|functionwithbrackets COMMA commaseparatedparams
|linedata COMMA commaseparatedparams
|structdata COMMA commaseparatedparams
;
functionwithbrackets: ASCIISTRING LEFTBRACKET commaseparatedparams RIGHTBRACKET { /*cout << "Function data: " << $2 << endl;*/ }
;
functionwithrectangles: ASCIISTRING LEFTRECTANGLE commaseparatedparams RIGHTRECTANGLE { /*cout << "Function data: " << $2 << endl;*/ }
;
lineparams:
|funcparam lineparams
|linedata lineparams
|structdata lineparams
|functionwithbrackets lineparams
;
linedata: LINE LEFTRECTANGLE lineparams RIGHTRECTANGLE
;
structdata: STRUCT LEFTRECTANGLE lineparams RIGHTRECTANGLE
;
sendargs: ASCIISTRING EQUALTO sendname LEFTBRACE sendpayload RIGHTBRACE {  /* cout << "abbb " << $1 << "\n" ; */ func_write( $1, $6 );   /*cout << "ActualPayload[\n" << $6 << "\n]\n"; */ }
;
sendname: ASCIISTRING DOT SERVERSEND { /* cout << "Send name is[" << $1 << "]\n"; */ } 
|ASCIISTRING DOT CLIENTSEND
;
sockcreate: ASCIISTRING EQUALTO socktype LEFTBRACKET sockargs RIGHTBRACKET
sockssendsrecvs
;
socktype:
|TCP  { cout << "\ntcpSocket: ";  }
|UDP  { cout << "\nudpSocket: " ; }
sockargs: sockarg 
|sockargs sockarg
;
sockarg:ASCIISTRING COLON ASCIISTRING comma {  /*cout << "sockarg: detected: " << $1 << " " << $3 << endl;  */ }
|ASCIISTRING COLON NUMBERS comma { cout << "Port: " << $3 << endl;   }
|ASCIISTRING COLON ANDSTRING comma {  /*cout << "sockarg: detected: " << $1 << " " << $3 << endl; */  }
|FILTER COLON REGEXSTRING comma {  /*cout << "sockarg: detected: " << $1 << " " << $3 << endl;  */ }
;
comma: 
/*empty */
|COMMA
;
%%

int main(int argc, char** argv) {
  FILE *myfile = fopen(argv[1], "r");
  if (!myfile) {
    cout << "Usage: ./a.out <mslfile>" << endl;
    return -1;
  }
  yyin = myfile;
  yyparse();
}


void yyerror(const char *s) {
  cout << "Parser error!  Message: " << s << endl;
  exit(-1);
}

