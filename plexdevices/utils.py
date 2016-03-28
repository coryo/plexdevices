import re
import xml.etree.ElementTree as ET
import json


def parse_xml(root):
    children = root.getchildren()
    x = {k: v for k, v in root.items()}
    x['_elementType'] = root.tag
    if len(children):
        x['_children'] = [parse_xml(child) for child in children]
    return x


def parse_response(res):
    try:
        data = json.loads(res)
    except Exception:
        try:
            # channels only return xml, maybe it's xml
            xml = ET.fromstring(res)
        except Exception:
            return {}
        else:
            data = parse_xml(xml)
            if 'totalSize' not in data:
                data['totalSize'] = 1
            return data
    else:
        return data

RE1 = re.compile('(.)([A-Z][a-z]+)')
RE2 = re.compile('([a-z0-9])([A-Z])')


def snake_case(name):
    s1 = RE1.sub(r'\1_\2', name)
    return RE2.sub(r'\1_\2', s1).lower()
