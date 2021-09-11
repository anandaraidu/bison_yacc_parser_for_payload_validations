%{
  #include <iostream>
  #include<string.h>
  #include <cstdio>
  #include "msl.tab.h"  // to get the token types from Bison
  #include <map>
using namespace std;
extern void create_file_and_put_in_map(  std::string comment);
void payload_write_newline( char *s) ;
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

\""HTTP/1.1"[ ]+[0-9]*[ ]*[0-9a-zA-Z ]*\\r\\n\" {
    yylval.sval = strdup(yytext);
    cout  << "HTTP Response detected\n"  << yylval.sval << " \n\n";
    payload_write_newline( yylval.sval );
    return HTTP_RESPONSE;
}

\""GET".*"HTTP/1.1"\\r\\n\" {
  cout  << "HTTP GET Request detected";
  yylval.sval = strdup(yytext);
  payload_write_newline( yylval.sval );
  return HTTP_REQUEST;
}

\""POST".*"HTTP/1.1"\\r\\n\" {
  cout  << "HTTP GET Request detected";
  yylval.sval = strdup(yytext);
  payload_write_newline( yylval.sval );
  return HTTP_REQUEST;
}

\""PUT".*"HTTP/1.1"\\r\\n\" {
  cout  << "HTTP GET Request detected";
  yylval.sval = strdup(yytext);
  payload_write_newline( yylval.sval );
  return HTTP_REQUEST;
}
\""OPTIONS".*"HTTP/1.1"\\r\\n\" {
  cout  << "HTTP Options detected";
  yylval.sval = strdup(yytext);
  payload_write_newline( yylval.sval );
  return HTTP_REQUEST;
}


"content_"[0-9]+[ ]*=[ ]*"0h"[^}]* {
    int i = 0;
    for (; i < yyleng; i++) {
        if (yytext[i] == 'h') {
            yylval.sval = strdup(yytext+i-1);
            payload_write_newline( yylval.sval );
            return HTTP_BODY;
               }
    }
    //cout  << "hex content line:[" <<  yylval.sval <<  "]\n\n";
}
"header"[ ]*"("[ ]*"header_name"[ ]*":"[ ]*\""Content-Length"\"[ ]*")"[ ]*"[" {
    yylval.sval = strdup(yytext);
    cout  << "HEADER line  " << yylval.sval << "\n\n";
    //payload_write_newline( yylval.sval );
    return HEADERFUNCLINE;
}
"length_string"[ ]*"("[ ]*"of"[ ]*":"[ ]*[a-zA-Z_0-9]*")" {
    yylval.sval = strdup(yytext);
    //payload_write_newline( yylval.sval );
    //payload_write_newline("]");
    payload_write_newline("Content-Length:xxx");
    cout << "Lennnnnnnnnnnnnnnnnnnnnnnnnn"  << yylval.sval << "\n";
    return LENGTH_STRING;
}

\"\\r\\n\" {
    cout  << "empty line line\n\n";
    yylval.sval = strdup(yytext);
    payload_write_newline( yylval.sval );
    return HTTP_HDR_END;
}

"0h"[0-9a-fA-F]* {
    yylval.sval = strdup(yytext);
    cout  << "Hex payload detected[" << yylval.sval << "]\n";
    payload_write_newline( yylval.sval );
    return HEX_BODY;
}

[a-zA-Z0-9_]+      {
  yylval.sval = strdup(yytext);
  //cout  << "ASCIII " << yylval.sval << "]\n";
  //payload_write_newline( yylval.sval );
  return ASCIISTRING;
}

"\""([^"\\]*(\\.[^"\\]*)*)"\""      {
  yylval.sval = strdup(yytext);
  //cout  << "stingdata....... " << yylval.sval << "]\n";
  payload_write_newline( yylval.sval );
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
