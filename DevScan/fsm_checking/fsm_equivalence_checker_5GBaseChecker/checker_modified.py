#!/usr/bin/env python
"""
simple script to visualize the trace output of smv / NuSMV
via Graphviz's dot-format. first, the trace is parsed and
then coded as dot-graph with states as nodes and input 
(transitions) as arcs between them. even if the counterexample's
loop start- and end-state are the same, they are represented by
two different nodes as there can be differences in the completeness
of the state variables' representation.

this is only a simple hack to get quick and dirty trace graphs ;-)
"""

import os,sys,getopt
from Dot2FSM import get_states_and_tx, list_to_dict
from collections import OrderedDict
from iterative_checker import parseDOT, dump_variables, dump_states, dump_actions, dump_defines, dump_assigns, dump_property, get_unique_action_names

digraph = ""
import subprocess
import re
import time
try:
   import pydot
except:
   print ("this module depends on pydot\nplease visit http://dkbza.org/ to obtain these bindings")
   sys.exit(2)

# CHANGE HERE:
VIEW_CMD="gv -antialias" #used as: VIEW_CMD [file]
DOT_CMD="dot -Tps -o" #used as:    DOT_CMD [outfile] [infile]
TEMPDIR="/tmp"        #store dot-file and rendering if viewmode without output-file


# for internal purposes, change only, if you know, what you do


class State(object):
    def __init__(self, label, input, action1, action2, state1, state2, transition1, transition2):
        self.label = label
        self.input = input
        self.action1 = action1
        self.action2 = action2
        self.state1 = state1
        self.state2 = state2
        self.transition1 = transition1
        self.transition2 = transition2

    def set_transition1(self,transition1):
        transition1 = []
        for transition in transition1:
            self.transition1.append(transition)
    def set_transition2(self,transition1):
        transition2 = []
        for transition in transition2:
            self.transition2.append(transition)


class Transition(object):
    def __init__(self, action_label, value):
        self.action_label = action_label
        self.value = value


DEBUG=False
PROFILE=False
PSYCO=True
if PSYCO:
   try:
      import psyco
   except (ImportError, ):
      pass
   else:
      psyco.full()
      if DEBUG: print ("psyco enabled")



def trace2dotlist(traces):
    """this function takes the trace output of (nu)smv as a string;
    then, after cleaning the string of warnings and compiler messages,
    decomposes the output into separate single traces which are translated
    to dot-graphs by _singletrace2dot. as a traceoutput can combine several
    traces, this method returns a list of the dot-graphs"""

    # beautify ;-)

    lines = [line for line in traces if not (line.startswith("***") or
      line.startswith("WARNING") or line == "\n" or line == '')]

    map(lambda x: x.lstrip("  "), lines)

    #print ("Printing lines .....")
    #for l in lines:
        #print l
    #print("EOL.......")
    # cut list at each "-- specification"
    index=0
    trace_list=[]
    trace=[]
    # trace_list = traces for multiple properties.
    # each trace consists of sequence of states.
    # each state consists of a list of variables and their values
    '''
    for line in lines:
        if (line.startswith("-- no counterexample found with bound") or "" in line):
            index = lines.index(line)
            continue
        elif line.startswith("-- specification"):
            # TODO: need to commemnt out the following line
            #formulae = line.rstrip("is false\n").lstrip("-- specification")
            #print ('formulae = ', formulae)
            last = index
            index = lines.index(line)
            trace_list.append(lines[last: index])
    trace_list.append(lines[index: len(lines)])
    '''
    for line in lines:
        if "specification" in line or "as demonstrated by the following execution sequence" in line or "Trace Description: LTL Counterexample " in line or "Trace Type: Counterexample " in line:
            continue
        trace.append(line)
    trace_list.append(trace)
    #print len(trace_list)
    #print trace_list
    #sort out postive results. And filter out the empty trace.
    trace_list = [trace for trace in trace_list if len(trace)>1 and not str(trace[0]).endswith("true")]

    #print ('### trace_list = #### ', trace_list)

        # Draw graph for each trace
    graph=[]
    for trace in trace_list:
        #print "IK"
        #print trace
        graph.append(_singletrace2dot(trace,True))
   
    return graph


def _singletrace2dot(trace,is_beautified=False):
    """translate a single trace into a corresponding dot-graph;
    wheras the parsing assumes a correct trace given as
    trace ::=  state ( input state )*
    """

    # if not is_beautified:
    #     lines = [line for line in trace if not (line.startswith("***") or
    #         line.startswith("WARNING") or line == "\n"
    #              or line.startswith("-- specification") or line.startswith("-- as demonstrated")
    #              or line.startswith("Trace Description: ") or line.startswith("Trace Type: "))]
    #     map(lambda x: x.lstrip("  "), lines)
    # else:
    #     lines = trace

    # strip the headers of each trace.
    global digraph
    lines = []
    #print ('trace = ', trace)
    for line in trace:
        #print(line)
        if( not (line.startswith("***") or
            line.startswith("WARNING") or line == "\n"
                 or line.startswith("-- specification") or line.startswith("-- as demonstrated")
                 or line.startswith("Trace Description: ") or line.startswith("Trace Type: "))):
            lines.append(line.lstrip("  "))

    #print (lines)
    #slice list at "->"
    index=0
    states=[]
    for item in lines:
        #print ('item = ', item)
        if item.startswith("->"):
            last=index
            index=lines.index(item)
            states.append(lines[last:index]) # the first state is empty
    states.append(lines[index:len(lines)])

    #print ('states', states)

    lines=False #free space!
   
    graph = pydot.Graph()

    loop=False #flag to finally add an additional dotted edge for loop

    # print states
    # print states[1][0]
    assert states[1][0].startswith("-> State:") #starting with state!

    digraph = 'Digraph G{\n'
    digraph += 'rankdir=LR\n'
    stateVariablesDict = OrderedDict()
    counter = 0
    for item in states[1:]: #first item is header
        name= item[0].lstrip("-> ").rstrip(" <-\n")
        if (name.startswith("State")):
            state=name.lstrip("State: ")
            node=pydot.Node(state)
            props=name+'\\n' #to reach pydotfile: need double '\'
            digraph =  digraph + 'S' + str(counter) + '[shape=box,label=\"' + name + '\\n'
            counter = counter + 1
            #print (name)
            for i in (item[1:]):
                #props+=i.rstrip('\n')
                #props+="\\n"
                isNewValue = False
                s = str(i).rstrip('\n')
                variable = s[:s.rfind('=')].strip()
                value = s[s.rfind('=')+1:].strip()

                if(variable not in stateVariablesDict):
                    isNewValue = False
                else:
                    (val, newValInd) = stateVariablesDict[variable]
                    if(str(val) != str(value)):
                        isNewValue = True
                stateVariablesDict[variable] = (value, isNewValue)

            #stateVariablesList = [[k, v] for k, v in stateVariablesDict.items()]

            for var, (val, newValInd) in stateVariablesDict.items():
                if(newValInd == True):
                    props += '*' + str(var) + ' = ' + str(val) + '\\n'
                    digraph = digraph + '*' + str(var) + ' = ' + str(val) + '\\n'
                else:
                    props += str(var) + ' = ' + str(val) + '\\n'
                    digraph = digraph + str(var) + ' = ' + str(val) + '\\n'

            node.set_label('"'+props+'"')

            digraph = digraph + '\"]\n'

            graph.add_node(node)

            for var, (val, newValInd) in stateVariablesDict.items():
                stateVariablesDict[var] = (val, False)


        elif name.startswith("Input"):
            assert state #already visited state
            trans=name.lstrip("Input: ")
            edge=pydot.Edge(state,trans)

            hasLoop = [it for it in item[1:] if it.startswith("-- Loop starts here")]
            #TODO: check trace-syntax, if this can happen only in the last line of a transition
            #      then list-compreh. can be avoided
            if hasLoop:
                loop=state #remember state at which loop starts
                item.remove(hasLoop[0])

            props=""
            for i in (item[1:]):
                props+=i.rstrip('\n')
                props+="\\n"
                edge.set_label(props)
                graph.add_edge(edge)

        else:
            assert False #only states and transitions!

    if loop:
        edge=pydot.Edge(state,loop)
        edge.set_style("dotted,bold")
        edge.set_label(" LOOP")
        graph.add_edge(edge)

    for i in range(1, counter):
        digraph = digraph + 'S' + str(i-1) + ' -> ' + 'S' + str(i) + '\n'
    digraph = digraph + '\n}\n'

    return graph



def get_states(nodes):
    states = []
    #nodes.sort(key=lambda x: x.label, reverse=False)
    for i in range(0,len(nodes)):
        node = nodes[i].to_string()
        node_list = node.split("\\n")
        #print (node_list)
        transition1 = []
        transition2 = []
        for field in node_list:
            if "State: " in field:
                label_list = re.findall("\d+\.\d+", field)
                label = label_list[0]
                #print 'State label = ', label

            if "input" in field:
                input = field.split("= ",1)[1] 
                #print 'input = ', input


            if "BLE1_" in field:
                remaining = field.split("T",1)[1]
                label_t1 = remaining.split('=')[0].strip()
                value =  remaining.split("= ",1)[1].strip()
                tran1 = Transition(label_t1,value)
                if('true' in value.lower()):
                    #print (label_t1, value)
                    transition1.append(tran1)
                    tlabel = "BLE1__T" + str(label_t1)
                    #print tlabel, value

            if "BLE2_" in field:
                remaining = field.split("T",1)[1] 

                label_t2 = remaining.split('=')[0].strip()
                value = remaining.split("= ", 1)[1].strip()
                tran2 = Transition(label_t2,value)
                if ('true' in value.lower()):
                    #print (label_t2, value)
                    transition2.append(tran2)
                    tlabel = "BLE2_T" + str(label_t2)
                    #print tlabel, value


            if "ble1_action" in field:
                action1 = field.split("= ",1)[1].strip()
                #print 'action 1 = ', action1

            if "ble2_action" in field:
                action2 = field.split("= ",1)[1].strip()
                #print 'action 2 = ', action2
            
            if "ble1_state" in field:
                state1 = field.split("= ",1)[1].strip()

            if "ble2_state" in field:
                state2 = field.split("= ",1)[1].strip()

        state = State(label,input,action1,action2,state1, state2, transition1,transition2)
        states.append(state)
        
    states.sort(key=lambda x: x.label, reverse=False)
    return states

ltlspec_out_file = open("ltlspec_out_file.txt", 'w')

def copy_fsm(src_path, dst_path, remove_edges = None):
    with open(src_path, 'r') as src_file, open(dst_path, 'w') as dst_file:
        for line in src_file:
            flag = True
            if remove_edges is not None:
                for edge_str in remove_edges:
                    # print("edge_str :", edge_str)
                    if edge_str in line:
                        flag = False
                        continue
            if flag:
                dst_file.write(line)
            else:
                print("Removed edge :", line)

        dst_file.close()
        src_file.close()

def compute_diff(nuxmfilename, commandfilename, outputfilename, input_condition = None, fsm1_action=None, fsm2_action=None, fsm1_inFile=None, fsm2_inFile=None):
    if not input_condition == "deregistration_req_protected" or not fsm1_action == "null_action" or not fsm2_action == "deregistration_accept":
        return []

    print("Running with :", input_condition, fsm1_action, fsm2_action)

    fsm1_inFile_temp = fsm1_inFile.split(".",1)[0].strip() + "_temp.dot"
    fsm2_inFile_temp = fsm2_inFile.split(".",1)[0].strip() + "_temp.dot"
    #print(fsm1_inFile_temp)
    open(fsm1_inFile_temp, 'w').close()
    open(fsm2_inFile_temp, 'w').close()
    open(nuxmfilename, 'w').close()
    # open both files
    with open(fsm1_inFile,'r') as firstfile, open(fsm1_inFile_temp,'w') as secondfile:
        # read content from first file
        for line in firstfile:
                # append content to second file
                secondfile.write(line)

    
    #print(fsm2_inFile_temp)
    # open both files
    with open(fsm2_inFile,'r') as firstfile, open(fsm2_inFile_temp,'w') as secondfile:
        # read content from first file
        for line in firstfile:
                # append content to second file
                secondfile.write(line)
    


    output_list = []
    outputfilename_time = outputfilename+"_time"
    if outputfilename_time:
        outputfile_time = open(outputfilename_time, 'a')
    else:
        import tempfile
        tempdir = tempfile.mkdtemp(dir=TEMPDIR)
        outputfile_time = os.path.join(tempdir, "trace")
        outputfile_time = open(outputfilename_time, 'a')
    outputfile_time.write("\n New Round Starting \n")
    print (" ########## Equivalence Checking for <output1: " +""+fsm1_action + ", output2: "+  fsm2_action + "> diversity class ############")

    # -----------------------------------

    
    # ----------------------------------------------
    bashCommand = "./nuXmv EQCHECK.smv > ctx"
    cmd = ['./nuXmv','-source', commandfilename, nuxmfilename]

    iter = 0
    new_out = None
    prev_out = None

    saved_inputs_set = set()

    will_try_removing_edges = True
    edge_remove_idx = 0
    saved_inputs = ""
    saved_input_condition = ""
    saved_ue1_ctx_output = ""
    saved_ue2_ctx_output = ""
    removing_edges = False

    while True:
        ltlspec_out_file.write("INPUT_CONDITION :" + str(input_condition) + "\n")
        ltlspec_out_file.write("edge_remove_idx :" + str(edge_remove_idx) + "\n")

        # if edge_remove_idx != 0:
        #     sys.exit()
        if edge_remove_idx >= len(saved_inputs.split()):
            removing_edges = False
            will_try_removing_edges = True

        if removing_edges:
            ltlspec_out_file.write("REACHED CHECK 3: removing_edges\n")
            # copy_fsm(fsm1_inFile, fsm1_inFile_temp)
            copy_fsm(fsm1_inFile_temp.replace(".dot", "_2.dot"), fsm1_inFile_temp)
            will_try_removing_edges = False
            fsm1_outputs, fsm1_states = LQFSM(saved_inputs.split(), fsm1_inFile_temp)
            ltlspec_out_file.write("saved_inputs :" + str(saved_inputs) + "\n")
            ltlspec_out_file.write("fsm1_states :" + str(fsm1_states) + "\n")


            # ltlspec_out_file.write("REACHED CHECK 4: else case\n")
            src_state = fsm1_states[edge_remove_idx]
            dst_state = fsm1_states[edge_remove_idx+1]
            input_symbol = saved_inputs.split()[edge_remove_idx]
            edge_str = "{} -> {} [label=\"{}".format(src_state, dst_state, input_symbol)
            ltlspec_out_file.write("edge_str : " + edge_str + "\n")
            copy_fsm(fsm1_inFile_temp.replace(".dot", "_2.dot"), fsm1_inFile_temp, [edge_str])
            edge_remove_idx = edge_remove_idx + 1
            # if edge_remove_idx >= len(fsm1_states) - 1:
            #     ltlspec_out_file.write("REACHED CHECK 3.5: removing_edges = False\n")
            #     removing_edges = False

        if not removing_edges and saved_input_condition != "":
            ltlspec_out_file.write("REACHED CHECK 5: not removing_edges and saved_input_condition available \n")
            # copy_fsm(fsm1_inFile, fsm1_inFile_temp)
            copy_fsm(fsm1_inFile_temp.replace(".dot", "_2.dot"), fsm1_inFile_temp)

            # the following part modifies output symbol as done in BLEDiff
            fsm1_label = 'BLE1'
            fsm2_label = 'BLE2'
            file_2 = open(fsm2_inFile_temp, 'r')
            lines = file_2.readlines()
            file_2.close()
            changed_lines = []
            flag = 0

            fsm2_outputs, fsm2_states = LQFSM(saved_inputs.split(), fsm2_inFile_temp)
            src_state = fsm2_states[-2]
            dst_state = fsm2_states[-1]
            input_symbol = saved_inputs.split()[-1]
            edge_str = "{} -> {} [label=\"{}".format(src_state, dst_state, input_symbol)
            ltlspec_out_file.write("fsm2_states :" + str(fsm2_states) + "\n")

            for line in lines:
                if edge_str in line and saved_input_condition in line and saved_ue2_ctx_output in line and flag == 0:
                    flag = 1
                    ltlspec_out_file.write("before changing line :" + line + "\n")
                    # line_splits = line.split()
                    # line_splits[-1] = line_splits[-1].replace(saved_ue2_ctx_output, saved_ue1_ctx_output)
                    # line = " ".join(line_splits)
                    line = line.replace(saved_ue2_ctx_output, saved_ue1_ctx_output)
                    ltlspec_out_file.write("changed line :" + line + "\n")

                changed_lines.append(line)
            file = open(fsm2_inFile_temp, 'w')

            if flag == 0:
                will_try_removing_edges = True

            for line in changed_lines:
                file.write(line)
            file.close()
            # sys.exit()
            iter = iter + 1
            will_try_removing_edges = True
            edge_remove_idx = 0
            saved_inputs = ""
            saved_input_condition = ""
            saved_ue1_ctx_output = ""
            saved_ue2_ctx_output = ""
            removing_edges = False
            if iter == 5:
                will_try_removing_edges = True
                break
            if prev_out is not None and new_out == prev_out:
                will_try_removing_edges = True
                break
            prev_out = new_out
            ###############################################################################


        fsm1_label = 'BLE1'
        fsm2_label = 'BLE2'         
        fsm1 = parseDOT(fsm1_inFile_temp, fsm1_label) # return (fsm, env_vars)
        fsm2 = parseDOT(fsm2_inFile_temp, fsm2_label) # return (fsm, env_vars)

        

        incoming_messages = []
        for in_msg in fsm1.incoming_messages:
            in_msg = in_msg.strip()
            if in_msg not in incoming_messages and in_msg not in 'null_action':
                incoming_messages.append(in_msg)

                
        for in_msg in fsm2.incoming_messages:
            in_msg = in_msg.strip()
            if in_msg not in incoming_messages and in_msg not in 'null_action':
                incoming_messages.append(in_msg)



        f = open(nuxmfilename, "w")
        f.write("MODULE main\n")
    
                
        dump_variables(f, incoming_messages)

        dump_states(f, (fsm1, fsm2))
        dump_actions(f, (fsm1, fsm2))
        
        dump_defines(f, (fsm1, fsm2))
        dump_assigns(f, (fsm1, fsm2))

      
        action_labels_1 = get_unique_action_names(fsm1)
        action_labels_2 = get_unique_action_names(fsm2)
        if fsm1_action not in action_labels_1 : 
            print("Output symbol not present in FSM 1 :", fsm1_action, ":", action_labels_1)
            break
        
        if fsm2_action not in action_labels_2:
            print("Output symbol not present in FSM 2 :", fsm2_action, ":", action_labels_2)
            break

        ltlspec =  "\n\nLTLSPEC ( \n G( ! (input = "+ input_condition + " & ble1_action = " + fsm1_action + " & ble2_action = " + fsm2_action + "))\n);"
        ltlspec_out_file.write(ltlspec+"\n")
        dump_property(f, ltlspec)
        f.close()   

        # print("CMD :", cmd)

        states = []
        offen_state = 0
        start_time = time.time()
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        output, error = process.communicate()
        new_out = output
        

        #print(output)
        total_time = (time.time() - start_time)
        outputfile_time.write('Duration: {}'.format(time.time() - start_time))
        outputfile_time.write("\n")
        print (output)
        if "is true" in output and not removing_edges:
            break
        elif "is true" in output and removing_edges:
            edge_remove_idx = edge_remove_idx + 1
            continue

        #print ("reached loop")
        trace = output.split("\n")
        
        if "State" in trace[-2]:
            del trace[-2]
        graph = trace2dotlist(trace)
        nodes = graph[0].get_nodes()
        states = get_states(nodes)

        ctx_inputs = ""
        ue1_ctx_outputs = ""
        ue1_ctx_output = ""
        ue2_ctx_outputs = ""
        ue2_ctx_output = ""
        ue1_ctx_state1 = ""
        ue1_ctx_state2 = ""
        ue2_ctx_state1 = ""
        ue2_ctx_state2 = ""
        input_list = []
        out_list1 = []
        out_list2 = []


        for state in states:
            trans1 = state.transition1
            trans2 = state.transition1
            if state.action1 == fsm1_action and state.action2 == fsm2_action and state.input == input_condition:                             
                offen_state = states.index(state) - 1
                break
            ctx_inputs = ctx_inputs.lstrip() + " " + state.input
            input_list.append(state.input)
            out_list1.append(states[states.index(state) + 1].action1)
            out_list2.append(states[states.index(state) + 1].action2)
            ue1_ctx_outputs = ue1_ctx_outputs.lstrip() + " " + states[states.index(state) + 1].action1
            ue2_ctx_outputs = ue2_ctx_outputs.lstrip() + " " + states[states.index(state) + 1].action2
            ue1_ctx_output =  states[states.index(state) + 1].action1
            ue2_ctx_output =  states[states.index(state) + 1].action2
            ue1_ctx_state1 =  states[states.index(state)].state1
            ue1_ctx_state2 =  states[states.index(state) + 1].state2
            ue2_ctx_state1 =  states[states.index(state)].state1
            ue2_ctx_state2 =  states[states.index(state) + 1].state2

            # fsm1_outputs, fsm1_states = LQFSM(ctx_inputs.split(), fsm1_inFile_temp)
            # fsm2_outputs, fsm2_states = LQFSM(ctx_inputs.split(), fsm2_inFile_temp)
            #
            # ltlspec_out_file.write("ctx_inputs :"+ str(ctx_inputs) + "\n")
            # ltlspec_out_file.write("fsm1_states :"+ str(fsm1_states) + "\n")
            # ltlspec_out_file.write("fsm2_states :"+ str(fsm2_states) + "\n")



        if input_condition == input_list[len(input_list)-1]:
            ltlspec_out_file.write("REACHED CHECK 6: found deviation\n")

            fsm1_outputs, fsm1_states = LQFSM(ctx_inputs.split(), fsm1_inFile)
            fsm1_real_output = " ".join(fsm1_outputs)
            # assert fsm1_real_output == ue1_ctx_outputs

            fsm2_outputs, fsm2_states = LQFSM(ctx_inputs.split(), fsm2_inFile)
            fsm2_real_output = " ".join(fsm2_outputs)
            # assert fsm2_real_output == ue2_ctx_outputs

            # s =  "[" + ctx_inputs + " / " + ue1_ctx_outputs + "] [" + ctx_inputs + " / " + ue2_ctx_outputs + "]"
            # s =  str(iter) + ": [" + ctx_inputs + " / " + fsm1_real_output + "] [" + ctx_inputs + " / " + fsm2_real_output + "]"
            s =  "[" + ctx_inputs + " / " + fsm1_real_output + "] [" + ctx_inputs + " / " + fsm2_real_output + "]"
            ltlspec_out_file.write("{}\n".format(s))

            output_list.append(s)

            if will_try_removing_edges and ctx_inputs not in saved_inputs_set:
                ltlspec_out_file.write("REACHED CHECK 1: will_try_removing_edges and not removing_edges\n")
                saved_input_condition = input_condition
                saved_ue1_ctx_output = fsm1_outputs[-1]
                saved_ue2_ctx_output = fsm2_outputs[-1]
                saved_inputs = ctx_inputs
                saved_inputs_set.add(ctx_inputs)
                copy_fsm(fsm1_inFile_temp, fsm1_inFile_temp.replace(".dot", "_2.dot"))
                edge_remove_idx = 0
                removing_edges = True

        elif not removing_edges and saved_input_condition == "":
            ltlspec_out_file.write("REACHED CHECK 7: no deviation\n")
            break

        elif not removing_edges:
            ltlspec_out_file.write("REACHED CHECK 2: not removing_edges and saved_input_condition available\n")
            will_try_removing_edges = True
            edge_remove_idx = 0
            # saved_inputs = ""
            saved_input_condition = ""
            saved_ue1_ctx_output = ""
            saved_ue2_ctx_output = ""
            removing_edges = False

        # if removing_edges:
        #     ltlspec_out_file.write("REACHED CHECK 3: removing_edges\n")
        #     # copy_fsm(fsm1_inFile, fsm1_inFile_temp)
        #     copy_fsm(fsm1_inFile_temp.replace(".dot", "_2.dot"), fsm1_inFile_temp)
        #     will_try_removing_edges = False
        #     fsm1_outputs, fsm1_states = LQFSM(saved_inputs.split(), fsm1_inFile_temp)
        #     ltlspec_out_file.write("saved_inputs :" + str(saved_inputs) + "\n")
        #     ltlspec_out_file.write("fsm1_states :" + str(fsm1_states) + "\n")
        #
        #
        #     # ltlspec_out_file.write("REACHED CHECK 4: else case\n")
        #     src_state = fsm1_states[edge_remove_idx]
        #     dst_state = fsm1_states[edge_remove_idx+1]
        #     edge_str = src_state + " -> " + dst_state
        #     ltlspec_out_file.write("edge_str : " + edge_str + "\n")
        #     copy_fsm(fsm1_inFile_temp.replace(".dot", "_2.dot"), fsm1_inFile_temp, [edge_str])
        #     edge_remove_idx = edge_remove_idx + 1
        #     if edge_remove_idx >= len(fsm1_states) - 1:
        #         ltlspec_out_file.write("REACHED CHECK 3.5: removing_edges = False\n")
        #         removing_edges = False

        # if not removing_edges:
        #     ltlspec_out_file.write("REACHED CHECK 5: not removing_edges\n")
        #     # copy_fsm(fsm1_inFile, fsm1_inFile_temp)
        #     copy_fsm(fsm1_inFile_temp.replace(".dot", "_2.dot"), fsm1_inFile_temp)
        #
        #     # the following part modifies output symbol as done in BLEDiff
        #     fsm1_label = 'BLE1'
        #     fsm2_label = 'BLE2'
        #     file_2 = open(fsm2_inFile_temp, 'r')
        #     lines = file_2.readlines()
        #     changed_lines = []
        #     flag = 0
        #     for line in lines:
        #         if saved_input_condition != "" and saved_input_condition in line and saved_ue2_ctx_output in line and flag == 0:
        #             flag = 1
        #             ltlspec_out_file.write("before changing line :" + line + "\n")
        #             line = line.replace(saved_ue2_ctx_output, saved_ue1_ctx_output)
        #             ltlspec_out_file.write("changed line :" + line + "\n")
        #
        #         changed_lines.append(line)
        #     file_2.close()
        #     file = open(fsm2_inFile_temp, 'w')
        #
        #     if flag == 0:
        #         will_try_removing_edges = True
        #
        #     for line in changed_lines:
        #         file.write(line)
        #     file.close()
        #     # sys.exit()
        #     iter = iter + 1
        #     if iter == 5:
        #         will_try_removing_edges = True
        #         break
        #     if prev_out is not None and new_out == prev_out:
        #         will_try_removing_edges = True
        #         break
        #     prev_out = new_out
        #     ###############################################################################

    # else:
    #     outputfile = sys.stdout

    outputfile_time.close()
    output_list = list(dict.fromkeys(output_list))
    
    return output_list

def LQFSM(Query, FSMpath): #load a FSM and query it
    output = []
    transition_states = []

    states, transitions, start_state = get_states_and_tx(FSMpath)
    INIT_STATE = start_state
    transition_states.append(start_state)
    Transitions = {}  # empty dict to store transitions

    state = INIT_STATE
    response = ""

    for i in transitions:
        Transitions.update(list_to_dict(i))

    for j in range(len(Query)):
        (response, dst_state) = Transitions[(state, Query[j])]
        state = dst_state
        transition_states.append(dst_state)
        output.append(response)

    return output, transition_states

def usage():
    print ("usage:")
    print (str(os.path.basename(sys.argv[0]))+" nuXmvFilename CommandFilename OutputFilename")
  
def main():
    global digraph
    '''
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvo:", ["view","help","output="])
    except getopt.GetoptError:
        # print help information and exit:
        usage()
        sys.exit(2)
    '''
    if len(sys.argv)<4:
        usage()
        sys.exit(2)

    nuxmfilename = None
    commandfilename = None
    outputfilename = None
    verbose = False
    view=False
    tempdir=None
    '''
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("-o", "--output"):
            outputfilename = a
        if o == "--view":
            view=True
    '''
  
    filename="ctx"

    nuxmfilename = sys.argv[1]
    commandfilename = sys.argv[2]
    outputfilename = sys.argv[3]
    #print nuxmfilename

    compute_diff(nuxmfilename, commandfilename, outputfilename)
    return

#
if __name__=="__main__":
    if DEBUG:
        # for post-mortem debugging
        import pydb,sys
        sys.excepthook = pydb.exception_hook
    elif PROFILE:
        if PSYCO:
            raise (Exception, "cannot profile whilst using psyco!!!")
        import hotshot
        prof = hotshot.Profile("_hotshot",lineevents=1)
        prof.runcall(main)
        prof.close()
    else:
        main()
