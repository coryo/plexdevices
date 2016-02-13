import re


def parse_xml(root):
    children = root.getchildren()
    x = {k: v for k, v in root.items()}
    x['_elementType'] = root.tag
    if len(children):
        x['_children'] = [parse_xml(child) for child in children]
    return x

RE1 = re.compile('(.)([A-Z][a-z]+)')
RE2 = re.compile('([a-z0-9])([A-Z])')


def snake_case(name):
    s1 = RE1.sub(r'\1_\2', name)
    return RE2.sub(r'\1_\2', s1).lower()
