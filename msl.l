%{
  #include <iostream>
  #include<string.h> 
  #include <cstdio>
  #include "msl.tab.h"  // to get the token types from Bison
  #include <map>
using namespace std;
extern void create_file_and_put_in_map(  std::string comment);
/*
As i understand it looks like the rules are scanned in order, so the general should 
be in  the end and specific rules should be in the begining....
*/
%}


%%
[ \t\n]           ;
"scenario"        {  return SCENARIO;     }
"hosts"           {  return HOSTS;        }
"options"         {  return OPTIONS;      }
"steps"           {  return STEPS;        }
"tcp"             {  return TCP;          }
"udp"             {  return UDP;          }
"client_send"     {  return CLIENTSEND;   }
"server_send"     {  return SERVERSEND;   }
"client_receive"  {  return CLIENTRECEIVE;}
"server_receive"  {  return SERVERRECEIVE; }
"struct"          {  return STRUCT;   }
"line"            {  return LINE;   }
"variables"       {  return VARIABLES;   }
"filter"       {  return FILTER;   }
"assertions"       {  return ASSERTION;   }
"{"               {  return LEFTBRACE;  }
"}"               {  return RIGHTBRACE; }
"("               {  return LEFTBRACKET;  }
")"               {  return RIGHTBRACKET; }
"["               {  return LEFTRECTANGLE;  }
"]"               {  return RIGHTRECTANGLE; }
"="               {  return EQUALTO; }
":"               {  return COLON; }
","               {  return COMMA; }
"."               {  return DOT; }
"&"[a-zA-Z0-9_]+      {
  yylval.sval = strdup(yytext);
  return ANDSTRING;
}
"@"[a-zA-Z0-9_]+      {
  yylval.sval = strdup(yytext);
  return ATSTRING;
}
"$"[a-zA-Z0-9_]+      {
  yylval.sval = strdup(yytext);
  return DOLLARSTRING;
}
[0-9]+           {
  yylval.sval = strdup(yytext);
    return NUMBERS;
}
[a-zA-Z0-9_]+      {
  yylval.sval = strdup(yytext);
  return ASCIISTRING;
}
"\""([^"\\]*(\\.[^"\\]*)*)"\""      {
  yylval.sval = strdup(yytext);
  return STRINGLINE;
}
"#".*      {
  yylval.sval = strdup(yytext);
  //std::cout << "Comment is[" << yylval.sval << "]\n";
  create_file_and_put_in_map(  yylval.sval );
  return COMMENT;
}
"\/"[a-zA-Z0-9_:\\\-()\[\]\*\+\.\/ ]+"\/"(":"[0-9]+)?      {
  yylval.sval = strdup(yytext);
  return REGEXSTRING;
}
%%
