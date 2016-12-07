#!/usr/bin/env python
#coding=utf-8

#---------------------------------------------
#         Name: SameCodeFinder.py
#       Author: Xing Chen 
#         Date: 2016-12-02
#  Description:	SameCodeFinder is a static code 
#  text scanner which can find the similar or 
#  the same code file in a big directory. 
#----------------------------------------------

import re
import os
import sys
import fileinput
import datetime
from simhash import Simhash, SimhashIndex

gb_detail  = 0
gb_max_dis = 20 
gb_min_linecount = 3
gb_output = "out.txt"

def main():
    global gb_detail
    global gb_max_dis
    global gb_min_linecount
    global gb_output

    if len(sys.argv) <= 1:
        print_help()
        return

    # Accoring to Argv as a Scanner Target root path
    root_path= sys.argv[1]
    suffix   = sys.argv[2]

    funciton_standard = 0

    for arg in sys.argv:
        if arg == "--help":
            print_help()
            return
        elif arg == "--detail":
            gb_detail = 1
        elif arg == "--functions":
            funciton_standard = 1
        elif arg.startswith("--max-distance="):
            arg_arr = arg.split("=")
            gb_max_dis = int(arg_arr[1])
        elif arg.startswith("--min-linecount="):
            arg_arr = arg.split("=")
            gb_min_linecount = int(arg_arr[1])
        elif arg.startswith("--output="):
            arg_arr = arg.split("=")
            gb_output = int(arg_arr[1])

    if not suffix:
        print "You must assign a suffix. eg: \".m\" \".java\""
    	return 

    if not os.path.isdir(root_path):
        print "You must assign a dir as first input"
        return 

    if funciton_standard == 1:
        print "Hashing all the functions..."
        hashed_arr  = hash_funcs(root_path, suffix)
    else:
        print "Hashing all the files..."
        hashed_arr  = hash_files(root_path, suffix)

    if len(hashed_arr) == 0:
        return
    
    print "Ranking all the hash results..."
    ranked_arr  = rank_hash(hashed_arr)

    print "Sorting   all the ranked results..."
    sorted_arr = sorted(ranked_arr, cmp=lambda x,y:cmp(x[2],y[2]))

    output_file = open(gb_output, 'w+')
    for obj in sorted_arr:
        print >>output_file, obj

    print "Finished! Result saved in %s" % (gb_output)


def hash_files(root_path, suffix):
    hashed_arr = []
    for file_path in scan_files(root_path, None, suffix):
        single_file_name = file_name(file_path)
        if gb_detail == 1:
            print "Start Hash File %s" % (single_file_name)
        signle_file = open(file_path, 'r') 
        single_file_content = signle_file.read() 
        single_hash_result  = Simhash(get_features(single_file_content))
        hashed_arr.append((single_file_name, single_hash_result))
    return hashed_arr

def hash_funcs(root_path, suffix):
    hashed_arr = []

    if not is_suffix_supported(suffix):
        print "The Funcs Standard SameCodeFinder just support Object-C and Java now. Use \".m\" or \".java\", please"
        return hashed_arr

    for file_path in scan_files(root_path, None, suffix):
        single_file_name = file_name(file_path)
        single_beauti_name   = ""
        single_func_content  = ""
        single_line_count    = 0
        single_bracket_count = 0
        is_function_started  = 0
        for line in fileinput.input(file_path):
            strip_line = line.strip()
            ## Skip comment lines
            if strip_line.startswith("//") or strip_line.startswith("/*") or strip_line.startswith("*"):
                continue

            if not is_function_started and re.findall(grammar_regex_by_suffix(suffix), line):
                ## for now, SameCodeFinder support Object-C and Java only
                if is_function_start_line(line, suffix):
                    single_beauti_name = beautify_func_name(line, suffix)

                    # Reset Line Content
                    single_func_content  = ""
                    single_line_count    = 0
                    single_bracket_count = 0

            single_func_content  = single_func_content + line
            single_line_count    = single_line_count   + 1
            single_bracket_count = single_bracket_count + count_func_bracket(line)
            if single_bracket_count > 0 and single_beauti_name:
                is_function_started = 1

            if single_bracket_count == 0 and is_function_started == 1:
                single_func_name = "%s(%s)" % (single_file_name, single_beauti_name)
                if gb_detail == 1:
                    print "Start Hash Func %s" % (single_func_name)
                
                single_hash_result = Simhash(get_features(single_func_content.strip()))
                if single_line_count >= gb_min_linecount:
                    hashed_arr.append((single_func_name, single_hash_result))

                is_function_started = 0

    return hashed_arr

def count_func_bracket(line):
    count = 0
    for word in line:
        if word=="{":
            count=count+1
        elif word=="}":
            count=count-1

    return count;

def rank_hash(hashed_arr):
    global gb_detail
    global gb_max_dis

    ranked_arr = []
    count = len(hashed_arr)
    for i in range(0, count):
        obj1 = hashed_arr[i]
        name1 = obj1[0]
        min_distance = 1000
        same_obj2_name = ""
        if gb_detail == 1:
            print "Start Rank %s" % (name1)
        for j in range(i + 1, count):
            obj2 = hashed_arr[j]
            name2 = obj2[0]
            distance = obj1[1].distance(obj2[1])
            if distance < min_distance:
                min_distance = distance
                same_obj2_name = name2
        
        if name1 != same_obj2_name and same_obj2_name != "":
            if min_distance < gb_max_dis:
                ranked_arr.append((name1, same_obj2_name, min_distance))
    
    return ranked_arr

##################################################
################ Start Util Funcs ################
def get_features(s):
    width = 3
    s = s.lower()
    s = re.sub(r'[^\w]+', '', s)
    return [s[i:i + width] for i in range(max(len(s) - width + 1, 1))]

#############################################
############### File Processor ##############
def scan_files(directory,prefix=None,postfix=None):  
    files_list=[]  
      
    for root, sub_dirs, files in os.walk(directory):  
        for special_file in files:  
            if postfix:  
                if special_file.endswith(postfix):  
                    files_list.append(os.path.join(root,special_file))  
            elif prefix:  
                if special_file.startswith(prefix):  
                    files_list.append(os.path.join(root,special_file))  
            else:  
                files_list.append(os.path.join(root,special_file))  
                            
    return files_list 

def file_name(file_path):
	name_arr=file_path.split("/")
	file_name=name_arr[len(name_arr) - 1]
	return file_name

############################################
############# Language Diversity ###########
def grammar_regex_by_suffix(suffix):
    if suffix == ".java":
        return ur"(public|private)(.*)\)\s?{";
    elif suffix == ".m":
        return ur"(\-|\+)\s?\(.*\).*(\:\s?\(.*\).*)?{?";

    return

def is_suffix_supported(suffix):
    if suffix == ".m" or suffix == ".java":
        return 1
    else:
        return 0

def is_function_start_line(line, suffix):
    if suffix == ".java":
        if line.strip().startswith("public") or line.strip().startswith("private"):
            return 1
    elif suffix == ".m":
        if line.startswith("+") or line.startswith("-"):
            return 1

    return 0

#############################################
########## Beautify function's name #########
def beautify_func_name(line, suffix):
    if suffix == ".m":
        return beautify_object_c_func_name(line)
    elif suffix == ".java":
        return beautify_java_func_name(line)
    else:
        return

def beautify_java_func_name(func_name):
    name_arr  = func_name.split("(");
    name_func_main = name_arr[0]
    name_func_arr = name_func_main.split(" ") 
    b_name = name_func_arr[len(name_func_arr) - 1]
    if b_name:
        return b_name
    else:
        return func_name

def beautify_object_c_func_name(func_name):
    has_startLeft = 0
    func_new_name = ""
    for char in func_name:
        if char=="(":
            has_startLeft = 1
        elif char == ')':
            has_startLeft = 0

        if has_startLeft == 0 and char != ')' and char != "+" and char != "-" and char != " " and char != "{":
            func_new_name = func_new_name + char;

    func_new_name = func_new_name.strip()
    func_new_name = func_new_name.replace(",...NS_REQUIRES_NIL_TERMINATION", "")

    return func_new_name

##########################################
############ Help ########################
def print_help(): 
    print "Usage:\n"
    print "\tpython SameFileFinder.python [arg0] [arg1]\n"
    print "Args:\n"
    print "\t[arg0] - Target Directory of files should be scan"
    print "\t[arg1] - Doc Suffix of files should be scan, eg"
    print "\t\t .m     - Object-C file"
    print "\t\t .swift - Swift file"
    print "\t\t .java  - Java file\n"
    print "\t--max-distance=[input] - max hamming distance to keep, default is 20"
    print "\t--min-linecount=[input] - for function scan, the function would be ignore if the total line count of the function less than min-linecount"
    print "\t--functions - Use Functions as code scan standard"
    print "\t              Attention: The \"--functions\" support just Object-C and Java now"
    print "\t--detail    - Show the detail of process\n"
    print "\t--output=[intput] - Customize the output file, default is \"out.txt\""

################ End Util Funcs ################

main()
