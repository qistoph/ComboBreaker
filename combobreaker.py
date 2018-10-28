#!/usr/bin/python3

import sys
import argparse
import subprocess

class GroupingException(Exception):
    pass

def listGroups(cmds, d=0):
    #print('listGroups(', cmds, ')')
    i = 0
    depth = 0
    start = -1
    while i < len(cmds):
        if cmds[i] == '[':
            if depth == 0: start = i
            depth += 1
        if cmds[i] == ']':
            depth -= 1
            if depth < 0: raise GroupingException('Unmatched ] at {:d}'.format(i))
            if depth == 0:
                #print('[ ] match {:d}, {:d}'.format(start, i))
                sub = listGroups(cmds[start+1:i], d+1)
                cmds[start:i+1] = [sub]
                #print(cmds)
                i = start
        #print("  "*d, "i:", i)
        i += 1

    if depth > 0: raise GroupingException('Unmatched [ at {:d}'.format(start))
    return cmds

def parseCmdArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='count',
        help='Increase verbosity, use multiple times to increase more (-vv)')
    parser.add_argument('-s', '--silent', action='count', default=0,
        help='Silence stdout of called command. -ss silences stderr and -sss silences both')
    parser.add_argument('-z', '--zero', action='store_true',
        help='Break execution on first 0 exit code')
    parser.add_argument('-Z', '--notzero', action='store_true',
        help='Break execution on first none 0 exit code')
    parser.add_argument('-m', '--match', type=str, action='append',
        help='Break execution when stdout matches MATACH')
    parser.add_argument('-M', '--nomatch', type=str, action='append', metavar='MATCH',
        help='Break execution when stdout doesn\'t match MATACH')
    parser.add_argument('cmd_args', nargs=argparse.REMAINDER)

    args = vars(parser.parse_args())
    if '--' in args['cmd_args']: args['cmd_args'].remove('--')

    #print(args['cmd_args'])
    args['cmd_args'] = listGroups(args['cmd_args'])

    return args   

def generator(fields, d=0):
    for i in range(len(fields)):
        field = fields[i]
        if isinstance(field, list):
            for value in field:
                cmd = fields[:]
                cmd[i] = value
                for ans in generator(cmd, d+1):
                    yield ans
            return # Any following args are handled in the generator call

    yield fields

def verbose(text, level=1):
    if options['verbose'] and level <= options['verbose']:
        print(text)

def anyMatch(text, matches):
    for m in matches:
        if m.encode('utf-8') in text:
            return True
    return False

def allMatch(text, matches):
    for m in matches:
        if m.encode('utf-8') not in text:
            return False
    return True

if __name__ == '__main__':
    options = parseCmdArguments()
    print(options)

    combobreaker = None
    
    for cmd in generator(options['cmd_args']):
        verbose("exec: " + " ".join(cmd))

        p =subprocess.Popen(" ".join(cmd), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if options['silent'] & 1 == 0:
            sys.stdout.buffer.write(out)
            sys.stdout.buffer.flush()
        if options['silent'] & 2 == 0:
            sys.stderr.buffer.write(err)
            sys.stderr.buffer.flush()
        ret = p.returncode

        verbose("Exit code {:d}\n".format(ret), 2)

        if ret == 0 and options['zero']:
            combobreaker = "C-C-C-Combo Breaker! Exit code is 0."
            break
        if ret != 0 and options['notzero']:
            combobreaker = "C-C-C-Combo Breaker! Exit code is not 0."
            break
        if options['match'] is not None and anyMatch(out, options['match']):
            combobreaker = "C-C-C-Combo Breaker! Output matched."
            break
        if options['nomatch'] is not None and not allMatch(out, options['nomatch']):
            combobreaker = "C-C-C-Combo Breaker! Output didn't match."
            break
        
    if combobreaker:
        verbose("\n"+combobreaker)
        verbose(" ".join(cmd))
    elif options['zero'] or options['notzero'] or options['match'] or options['nomatch']:
        verbose("\nAll done, no combo breaker")
