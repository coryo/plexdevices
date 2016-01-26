def parse_xml(root):
    children = root.getchildren()
    x = {k: v for k, v in root.items()}
    x['_elementType'] = root.tag
    if len(children):
        x['_children'] = [parse_xml(child) for child in children]
    return x
