import json
from ... import setup as se

version_json = f'''
{
 
 "version": {se.version} + {se.name}
}
'''  # END VERSION_JSON


def get_versions():
    return json.loads(version_json)