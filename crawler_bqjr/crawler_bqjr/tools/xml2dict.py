"""
Thunder Chen<nkchenz@gmail.com> 2007.9.1
"""
try:
    import xml.etree.ElementTree as ET
except ImportError:
    import cElementTree as ET  # for 2.4

from re import compile as re_compile
from traceback import print_exc


class ObjectDict(dict):
    """
    object view of dict, you can
    """

    def __init__(self, initd=None):
        if initd is None:
            initd = {}
        dict.__init__(self, initd)

    def __getattr__(self, item):
        d = self.__getitem__(item)
        # if value is the only key in object, you can omit it
        if isinstance(d, dict) and 'value' in d and len(d) == 1:
            return d['value']
        else:
            return d

    def __setattr__(self, item, value):
        self.__setitem__(item, value)


class XML2Dict(object):
    """
    XML解析为字典工具类
    """

    def __init__(self):
        self.namespace_pattern = re_compile(r"\{(.*)\}(.*)")

    def _parse_node(self, node):
        node_tree = ObjectDict()
        # Save attrs and text, hope there will not be a child with same name
        if node.text:
            node_tree.value = node.text
        for (k, v) in node.attrib.items():
            k, v = self._namespace_split(k, v)
            node_tree[k] = v
        # Save childrens
        for child in node.getchildren():
            tag, tree = self._namespace_split(child.tag, self._parse_node(child))
            if tag not in node_tree:  # the first time, so store it in dict
                node_tree[tag] = tree
                continue
            old = node_tree[tag]
            if not isinstance(old, list):
                node_tree.pop(tag)
                node_tree[tag] = [old]  # multi times, so change old dict to a list
            node_tree[tag].append(tree)  # add the new one

        return node_tree

    def _namespace_split(self, tag, value):
        """
           Split the tag  '{http://cs.sfsu.edu/csc867/myscheduler}patients'
             ns = http://cs.sfsu.edu/csc867/myscheduler
             name = patients
        """
        result = self.namespace_pattern.search(tag)
        if result:
            value.namespace, tag = result.groups()
        return tag, value

    def get_dict(self, xml_or_path, is_path=False):
        """
        获取xml解析为字典
        :param xml_or_path:
        :param is_path: 是否为xml文件路径
        :return:
        """
        try:
            root = self.__load_xml(xml_or_path, is_path)
            if not root:
                return
            root_tag, root_tree = self._namespace_split(root.tag, self._parse_node(root))
            return ObjectDict({root_tag: root_tree})
        except Exception:
            print("[-]xml解析为字典失败")
            print_exc()
            return

    def __load_xml(self, xml_or_path, is_path):
        """
        解析XML
        :param xml_or_path:
        :param is_path:
        :return:
        """
        try:
            if is_path:
                return ET.parse(xml_or_path)
            else:
                return ET.fromstring(xml_or_path)
        except Exception:
            print("[-]解析XML失败")
            print_exc()
            return


if __name__ == '__main__':
    s = """<Response><HeaderInfos><Code>0000</Code><Reason>成功</Reason></HeaderInfos><ResponseData><Attach>test</Attach><ResultCode>0000</ResultCode><ResultDesc>操作成功</ResultDesc><Data><Count>0</Count><Items /></Data></ResponseData></Response>"""
    xml = XML2Dict()
    ret_dict = xml.get_dict(s)
    print(ret_dict)
