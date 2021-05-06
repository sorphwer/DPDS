import os
import ast
import time
import csv
import json
import sys
def cprint(content,module='DEBUG',*args):
    if args:
        print('\033[1;32;43m ['+module+'] \033[0m '+ content + '\033[1;35m' +str(args) +' \033[0m' + time.strftime(" |%Y-%m-%d %H:%M:%S|", time.localtime()) )
    else:
        print('\033[1;32;43m ['+module+'] \033[0m '+ content + time.strftime(" |%Y-%m-%d %H:%M:%S|", time.localtime()))

def env(key, default=None, required=True):
    """
    Retrieves environment variables and returns Python natives. The (optional)
    default will be returned if the environment variable does not exist.
    """
    try:
        value = os.environ[key]
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value
    except KeyError:
        if default or not required:
            return default
        raise RuntimeError("Missing required environment variable '%s'" % key)
def file_write_log(path,info):
    with open(path, mode='a+',encoding="utf-8") as file_a:
        file_a.write( str(info) + time.strftime(" |%Y-%m-%d %H:%M:%S|", time.localtime()) + '\n')
    file_a.close()