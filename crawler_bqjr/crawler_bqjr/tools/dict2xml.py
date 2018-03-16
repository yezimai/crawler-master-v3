# encoding: utf-8
"""
structured.py - handle structured data/dicts/objects
Created by Maximillian Dornseif on 2009-12-27.
Copyright (c) 2009-2011, 2015 HUDORA. All rights reserved.
"""

from re import compile as re_compile
from xml.etree import cElementTree as ET


# Code is based on http://code.activestate.com/recipes/573463/
def _convert_dict_to_xml_recurse(parent, dictitem, listnames, sort=True):
    """Helper Function for XML conversion."""

    if isinstance(dictitem, list):
        raise TypeError('Unable to convert bare lists')

    if isinstance(dictitem, dict):
        items = dictitem.items()
        if sort:
            items = sorted(items)
        for (tag, child) in items:
            if isinstance(child, list):
                # iterate through the array and convert
                itemname = listnames.get(tag)
                # itemname = listnames.get(tag, "item")
                listelem = ET.SubElement(parent, tag) if itemname is not None else parent

                for listchild in child:
                    if itemname is not None:
                        elem = ET.SubElement(listelem, itemname)
                    else:
                        elem = ET.SubElement(listelem, tag)
                    _convert_dict_to_xml_recurse(elem, listchild, listnames, sort=sort)
            else:
                if tag.startswith('@'):
                    parent.attrib[tag[1:]] = child
                else:
                    elem = ET.Element(tag)
                    parent.append(elem)
                    _convert_dict_to_xml_recurse(elem, child, listnames, sort=sort)
    elif dictitem is not None:
        parent.text = str(dictitem)


def dict2et(xmldict, roottag, listnames=None, sort=True):
    """Converts a dict to an ElementTree.
    Converts a dictionary to an XML ElementTree Element::
    """

    if not listnames:
        listnames = {}
    root = ET.Element(roottag)
    _convert_dict_to_xml_recurse(root, xmldict, listnames, sort=sort)
    return root


def dict2xml(datadict, roottag='data', remove_roottag=True, listnames=None, sort=True):
    """Converts a dictionary to an UTF-8 encoded XML string.
    See also dict2et()
    """
    root = dict2et(datadict, roottag, listnames, sort=sort)
    return to_string(root, roottag, remove_roottag)


def to_string(root, roottag, remove_roottag, encoding='utf-8'):
    """Converts an ElementTree to a string"""

    xml_bytes = ET.tostring(root)
    xml_str = xml_bytes.decode(encoding)
    if remove_roottag:
        pattern = '<%s>(.+)</%s>' % (roottag, roottag)
        xml_str = re_compile(pattern).search(xml_str).group(1)
    return xml_str


if __name__ == '__main__':
    dic = {
        "Request": {
            "HeaderInfos": {
                "ClientType": "#6.2.1#channel29#Huawei LON-AL00#",
                "Source": "110003",
                "SourcePassword": "Sid98s",
                "Code": "queryPhoneSections",
                "Timestamp": "20180108173628"
            },
            "Content": {"Attach": "test"}
        }
    }

    xml = dict2xml(dic, roottag="data")
    print(xml, end="\n\n")

    xml = dict2xml(dic, roottag="data", remove_roottag=False)
    print(xml, end="\n\n")

    xml = dict2xml(dic)
    print(xml, end="\n\n")

    dic = {
        "Request": {
            "cmd": "getUserInfo",
            "counts": [1, 2, 3],
            "datas": [
                {
                    "name": "tom"
                },
                {
                    "name": "bob"
                }
            ]
        }
    }

    xml = dict2xml(dic)
    print(xml, end="\n\n")

    xml = dict2xml(dic, listnames={"counts": "counts", "datas": "datas"})
    print(xml, end="\n\n")
