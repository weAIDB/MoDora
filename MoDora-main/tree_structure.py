import copy

class TreeNode:

    def __init__(self, title, typ=None, metadata=None, data=None, location=None, children=None, path=None):
        self.title = title
        self.type = typ
        self.metadata = metadata
        self.data = data
        self.location = location
        self.children = [] if children is None else children
        self.path = [] if path is None else path

    def insert_child(self, child_node):
        child_node.path = self.path + [child_node.title]
        self.children.append(child_node)

    def delete_child(self, child_node):
        if child_node in self.children:
            self.children.remove(child_node)
        
    def find_child(self, title):
        for node in self.children:
            if node.title == title:
                return node
        return None

    def find_child_by_path(self, path):
        

        path = path.copy()

        for i in range(0, len(self.path)):
            if self.path[i] != path[i]:
                return None
        path = path[len(self.path):]

        if not path:
            return self
        child = self.find_child(path[0])
        for title in path[1:]:
            if child:
                child = child.find_child(title)
            else:
                return None
        return child
    
    def to_dict(self):
        
        dict_node = {
            "type":self.type,
            "metadata":self.metadata,
            "data":self.data,
            "location":self.location,
            "children":{}
        }

        dict_node["children"] = {child.title: child.to_dict() for child in self.children}

        return dict_node

def clone_tree(node):
    new_root = TreeNode(
        title=node.title,
        typ=node.type,
        metadata=copy.deepcopy(node.metadata),
        data=copy.deepcopy(node.data),
        location=copy.deepcopy(node.location),
        children=[],
        path=copy.deepcopy(node.path)
    )

    for child in node.children:
        new_child = clone_tree(child)
        new_root.insert_child(new_child)
    return new_root

def dict_to_tree(dict_node, root_title="ROOT", path=None):

    root = TreeNode(title=root_title, typ=dict_node['type'], metadata=dict_node['metadata'], data=dict_node['data'], location=dict_node['location'], path = path+[root_title] if path else [root_title])

    def add_subtree(dict_node, root):
        for sub_title, dict_child in dict_node['children'].items():
            child_node = TreeNode(title=sub_title, typ=dict_child['type'], metadata=dict_child['metadata'], data=dict_child['data'], location=dict_child['location'])
            root.insert_child(child_node)
            add_subtree(dict_child, child_node)
    
    add_subtree(dict_node, root)
    return root

