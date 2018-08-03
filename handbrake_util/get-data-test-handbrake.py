import json
import pprint
import subprocess
import json
import re

in_file = "I:\\MovieFolder\\MOVIES\\processed\\Black Panther"
runstr = 'HandBrakeCLI -i "{}" --scan --json'.format(in_file)


subproc_call = subprocess.Popen(
    runstr, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out, err = subproc_call.communicate()
errcode = subproc_call.returncode

# dict_out = json.loads(out.decode('utf-8'))
# print(out.decode('utf-8'))
# print("-----------------------------")
dict_out = re.search(r"(?s)(?<=(JSON Title Set:))(.*$)",
                    out.decode('utf-8'))
dict_out = json.loads(dict_out.group())

height = dict_out['TitleList'][0]['Geometry']['Height']
width = dict_out['TitleList'][0]['Geometry']['Width']

print(f"Film Width  : {width}\nFilm Height : {height}")
# print(type(out.decode('utf-8')))
# pprint.pprint(dict_out)
# jjson = out.decode('utf-8')

# print(jjson)
