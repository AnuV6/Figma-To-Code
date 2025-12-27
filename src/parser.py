import re
def rgb_to_hex(r, g, b):
    # Figma gives colors in 0-1 range
    return '#{:02x}{:02x}{:02x}'.format(int(r * 255), int(g * 255), int(b * 255))

def extract_colors(document):
    """
    Traverse the document to find all unique colors.
    Returns a list of dicts: {'hex': '#RRGGBB', 'r': 0.1, ...}
    """
    colors = {}

    def _traverse(node):
        if 'fills' in node:
            for fill in node['fills']:
                if fill['type'] == 'SOLID' and fill.get('visible', True) is not False:
                    color = fill['color']
                    hex_code = rgb_to_hex(color['r'], color['g'], color['b'])
                    if hex_code not in colors:
                        colors[hex_code] = color
        
        if 'strokes' in node:
            for stroke in node['strokes']:
                 if stroke['type'] == 'SOLID' and stroke.get('visible', True) is not False:
                    color = stroke['color']
                    hex_code = rgb_to_hex(color['r'], color['g'], color['b'])
                    if hex_code not in colors:
                        colors[hex_code] = color

        if 'children' in node:
            for child in node['children']:
                _traverse(child)

    _traverse(document)
    return colors

def extract_typography(document):
    """
    Traverse to find unique text styles.
    """
    text_styles = {}

    def _traverse(node):
        if node['type'] == 'TEXT':
            style = node.get('style')
            # Create a unique key for the style hash
            if style:
                key = f"{style.get('fontFamily')}-{style.get('fontWeight')}-{style.get('fontSize')}"
                if key not in text_styles:
                    text_styles[key] = style
        
        if 'children' in node:
            for child in node['children']:
                _traverse(child)

    _traverse(document)
    return text_styles.values()

def extract_images(document):
    """
    Find nodes that have image fills.
    Returns: list of dicts {'id': node_id, 'name': node_name, 'image_ref': ref}
    """
    images = []

    def _traverse(node):
        if 'fills' in node:
            for fill in node['fills']:
                if fill['type'] == 'IMAGE':
                    images.append({
                        'id': node['id'],
                        'name': node['name'],
                        'image_ref': fill.get('imageRef') # This ref is needed to lookup the URL
                    })
        
        if 'children' in node:
            for child in node['children']:
                _traverse(child)

    _traverse(document)
    return images


def generate_css(node):
    """
    Generate CSS for a specific node (very basic implementation).
    """
    css = []
    
    # Position (if absolute) is complex because it depends on parent, 
    # but we can do basic style props.
    
    if 'style' in node: # Text nodes
        s = node['style']
        css.append(f"font-family: '{s.get('fontFamily')}';")
        css.append(f"font-weight: {s.get('fontWeight')};")
        css.append(f"font-size: {s.get('fontSize')}px;")
        if 'lineHeightPx' in s:
             css.append(f"line-height: {s.get('lineHeightPx')}px;")

    # Fills (Background)
    if 'fills' in node:
        for fill in node['fills']:
            if fill['type'] == 'SOLID' and fill.get('visible', True) is not False:
                c = fill['color']
                hex_code = rgb_to_hex(c['r'], c['g'], c['b'])
                # Simplified: only taking the first solid fill as background
                css.append(f"background-color: {hex_code};")
                if 'opacity' in fill:
                     css.append(f"opacity: {fill['opacity']};")
                break 

    # Layout (Width/Height)
    if 'absoluteBoundingBox' in node:
        bbox = node['absoluteBoundingBox']
        css.append(f"width: {bbox['width']}px;")
        css.append(f"height: {bbox['height']}px;")
    
    # Corner Radius
    if 'cornerRadius' in node:
        css.append(f"border-radius: {node['cornerRadius']}px;")

    # Effects (Shadows)
    if 'effects' in node:
        for effect in node['effects']:
            if effect['type'] == 'DROP_SHADOW' and effect.get('visible', True) is not False:
                color = effect['color']
                hex_code = rgb_to_hex(color['r'], color['g'], color['b'])
                offset = effect['offset']
                radius = effect['radius']
                css.append(f"box-shadow: {offset['x']}px {offset['y']}px {radius}px {hex_code};")

    return "\n".join(css)

def find_node_by_id(node, target_id):
    """
    Recursively find a node by its ID.
    """
    if node['id'] == target_id:
        return node
    
    if 'children' in node:
        for child in node['children']:
            found = find_node_by_id(child, target_id)
            if found:
                return found
    return None

def get_top_level_frames(document):
    """
    Get all top-level frames (children of the document/canvas).
    """
    frames = []
    # Document -> Canvas -> Frames
    if 'children' in document:
        for canvas in document['children']:
            if 'children' in canvas:
                for child in canvas['children']:
                    if child['type'] == 'FRAME' or child['type'] == 'SECTION':
                       frames.append(child)
    return frames

def extract_css_recursive(node, depth=0):
    """
    Recursively generate CSS for a node and its children.
    Returns a string.
    """
    indent = "  " * depth
    css_output = []
    
    node_name = node['name']
    node_type = node['type']
    
    # Generate CSS for current node
    node_css = generate_css(node)
    
    if node_css:
        css_output.append(f"{indent}/* {node_name} ({node_type}) */")
        css_output.append(f"{indent}.{re.sub(r'[^a-zA-Z0-9]', '_', node_name)} {{")
        # Indent each line of CSS
        for line in node_css.split('\n'):
            css_output.append(f"{indent}  {line}")
        css_output.append(f"{indent}}}\n")
        
    if 'children' in node:
        for child in node['children']:
            css_output.append(extract_css_recursive(child, depth + 1))
            
    return "\n".join(css_output)
