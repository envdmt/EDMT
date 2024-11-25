import json

version_json = '''
{
 "date": "2024-12-02T14:23:16+0200",
 "dirty": false,
 "error": null,
 "full-revisionid": "e4314d53bc69452de1202e36b3cf0c5806a7d3b1",
 "version": "1.0.0.2"
}
'''  # END VERSION_JSON


def get_versions():
    return json.loads(version_json)
