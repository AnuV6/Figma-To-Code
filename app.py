import streamlit as st
import src.figma_client as figma
import src.parser as parser
import re
import zipfile
import io
import json
import requests
import concurrent.futures
import time

st.set_page_config(page_title="Figma to Code", layout="wide")

st.title("Figma to Code Extractor")

# sidebar
with st.sidebar:
    st.header("Configuration")
    token = st.text_input("Figma Personal Access Token", type="password")
    # Pre-filled with user provided URL
    default_url = "https://www.figma.com/design/GpGRhxQdQor2b2SUcqvscn/POS-System-Web-UI--Community-?node-id=0-1"
    file_url = st.text_input("Figma File URL", value=default_url)
    
    st.info("Upload your local .fig file to Figma Drafts to get a URL.")
    
    load_btn = st.button("Load File")

def parse_file_key(url):
    # Support both old /file/ and new /design/ URLs
    # Also sometimes it is /proto/ for prototypes
    match = re.search(r"(?:file|design|proto)/([a-zA-Z0-9]+)/", url)
    if match:
        return match.group(1)
    return None

    return None

@st.cache_data(ttl=600)
def get_file_data(token, file_key):
    client = figma.FigmaClient(token)
    return client.get_file(file_key)

@st.cache_data(ttl=600)
def get_rendered_images(token, file_key, ids):
    client = figma.FigmaClient(token)
    return client.get_images(file_key, ids)

if load_btn and token and file_url:
    file_key = parse_file_key(file_url)
    if not file_key:
        st.error(f"Could not parse File ID from URL: {file_url}")
    else:
        with st.spinner(f"Fetching file data for ID: {file_key}..."):
            # client = figma.FigmaClient(token) # No longer needed directly here
            try:
                # Use cached function
                data = get_file_data(token, file_key)
                
                if data and 'document' in data:
                    st.session_state['file_data'] = data
                    # Also fetch image fills (URLs)
                    try:
                         # We can suppress image errors if file loaded ok
                         # Use cached function
                         st.session_state['image_meta'] = get_image_data(token, file_key)
                    except Exception as e:
                        st.warning(f"Could not fetch images (might be empty): {e}")
                        
                    st.success("File loaded successfully!")
                else:
                     st.error("API returned data but no document found. Check permissions.")
            except Exception as e:
                st.error(f"API Error: {e}")
                st.info("Check your **Personal Access Token** and **File URL**.")
                if "403" in str(e):
                    st.warning("403 Forbidden: Your token might be invalid or doesn't have access to this file.")
                if "404" in str(e):
                    st.warning("404 Not Found: The file ID might be wrong or the file was deleted.")

if 'file_data' in st.session_state:
    data = st.session_state['file_data']
    document = data['document']
    
    # Safely get image metadata, defaulting to empty dict if None
    raw_image_meta = st.session_state.get('image_meta')
    image_meta = raw_image_meta.get('meta', {}) if raw_image_meta else {}
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Colors", "Typography", "Inspector", "Assets", "Screens"])
    
    with tab1:
        st.header("Color Palette")
        colors = parser.extract_colors(document)
        if colors:
            cols = st.columns(5)
            for i, (hex_code, color) in enumerate(colors.items()):
                with cols[i % 5]:
                    st.color_picker(hex_code, hex_code, disabled=True)
                    st.code(hex_code)
        else:
            st.info("No colors found.")

    with tab2:
        st.header("Typography")
        text_styles = parser.extract_typography(document)
        if text_styles:
            # Prepare data for dataframe
            df_data = []
            for s in text_styles:
                df_data.append({
                    "Font Family": s.get('fontFamily'),
                    "Weight": s.get('fontWeight'),
                    "Size": f"{s.get('fontSize')}px",
                    "Line Height": f"{s.get('lineHeightPx')}px" if 'lineHeightPx' in s else "Auto"
                })
            st.dataframe(df_data, use_container_width=True)
        else:
            st.info("No text styles found.")

    with tab3:
        st.header("Node Inspector")
        st.write("Enter a Node ID to inspect its properties and generated CSS.")
        
        # Helper to recursively list all nodes? Too many.
        # Just input for now.
        node_id_input = st.text_input("Node ID (e.g. 1:123)")
        
        if node_id_input:
           found_node = parser.find_node_by_id(document, node_id_input)
           if found_node:
               st.success(f"Found Node: {found_node['name']} ({found_node['type']})")
               
               col_a, col_b = st.columns(2)
               with col_a:
                   st.subheader("Raw Properties")
                   st.json(found_node, expanded=False)
               
               with col_b:
                   st.subheader("Generated CSS")
                   css = parser.generate_css(found_node)
                   st.code(css, language='css')
           else:
               st.error("Node not found in this document.")
        else:
            st.info("Tip: You can find Node IDs in the 'Raw Properties' of parent nodes or by guessing if you know the structure.")
    
    with tab4:
        st.header("Assets (Images)")
        images = parser.extract_images(document)
        if images and image_meta:
            st.write(f"Found {len(images)} images.")
            
            for img in images:
                ref = img.get('image_ref')
                if ref and ('images' in image_meta) and (ref in image_meta['images']):
                    img_url = image_meta['images'][ref]
                    with st.expander(f"Image: {img['name']}"):
                         st.image(img_url, width=200)
                         st.markdown(f"[Download]({img_url})")
        else:
            st.info("No images found or failed to load image metadata.")
            
    with tab5:
        st.header("Bulk Export")
        frames = parser.get_top_level_frames(document)
        
        if frames:
            frame_names = [f['name'] for f in frames]
            
            # Multiselect for screens
            selected_frames_names = st.multiselect("Select Screens to Export", frame_names)
            
            include_images = st.checkbox("Include Rendered Screen Images (PNG)", value=True)
            
            if st.button("Download ZIP Package"):
                if not selected_frames_names:
                    st.warning("Please select at least one screen.")
                else:
                    start_time = time.time()
                    status_text = st.empty()
                    status_text.text("Starting ZIP generation...")
                    
                    # In-memory ZIP
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        # 1. Export Colors (JSON)
                        colors = parser.extract_colors(document)
                        # Convert to list of dicts for JSON
                        colors_data = [{"hex": k, "r": v['r'], "g": v['g'], "b": v['b']} for k, v in colors.items()]
                        zf.writestr("colors.json", json.dumps(colors_data, indent=2))
                        
                        # 2. Export Typography (JSON)
                        text_styles = parser.extract_typography(document)
                        # Convert values to list
                        typo_data = list(text_styles)
                        zf.writestr("typography.json", json.dumps(typo_data, indent=2))
                        
                        # 3. Export Global CSS variables (Optional idea, maybe later)
                        
                        # 4. Export Selected Screens CSS
                        status_text.text(f"Generating CSS for {len(selected_frames_names)} screens...")
                        for name in selected_frames_names:
                            frame = next(f for f in frames if f['name'] == name)
                            css_content = parser.extract_css_recursive(frame)
                            # Sanitize filename
                            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', name)
                            zf.writestr(f"screens/css/{safe_name}.css", css_content)
                        
                        # 4.5 Export Rendered Screen Images
                        if include_images:
                            status_text.text(f"Fetching rendered images for {len(selected_frames_names)} screens...")
                            selected_ids = [next(f['id'] for f in frames if f['name'] == name) for name in selected_frames_names]
                            
                            rendered_data = get_rendered_images(token, file_key, selected_ids)
                            
                            if rendered_data and 'images' in rendered_data:
                                status_text.text(f"Downloading {len(selected_frames_names)} screen images...")
                                
                                def download_screen_img(name_id):
                                    name, node_id = name_id
                                    img_url = rendered_data['images'].get(node_id)
                                    if img_url:
                                        try:
                                            resp = requests.get(img_url, timeout=10)
                                            if resp.status_code == 200:
                                                safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', name)
                                                return f"screens/images/{safe_name}.png", resp.content
                                        except Exception as e:
                                            print(f"Failed to download screen image {name}: {e}")
                                    return None

                                # Download in parallel
                                name_id_pairs = [(name, next(f['id'] for f in frames if f['name'] == name)) for name in selected_frames_names]
                                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                                    future_to_screen = {executor.submit(download_screen_img, pair): pair for pair in name_id_pairs}
                                    for future in concurrent.futures.as_completed(future_to_screen):
                                        result = future.result()
                                        if result:
                                            filename, content = result
                                            zf.writestr(filename, content)
                        
                        # 5. Export Images (PNGs)
                        # Only download images used in the selected screens
                        relevant_images = []
                        seen_ids = set()
                        
                        for name in selected_frames_names:
                            frame = next(f for f in frames if f['name'] == name)
                            frame_imgs = parser.extract_images(frame)
                            for img in frame_imgs:
                                if img['id'] not in seen_ids:
                                    relevant_images.append(img)
                                    seen_ids.add(img['id'])

                        if relevant_images and image_meta:
                            status_text.text(f"Downloading {len(relevant_images)} unique images (Parallel)...")
                            
                            def download_image(img):
                                ref = img.get('image_ref')
                                if ref and ('images' in image_meta) and (ref in image_meta['images']):
                                    img_url = image_meta['images'][ref]
                                    try:
                                        resp = requests.get(img_url, timeout=5)
                                        if resp.status_code == 200:
                                            img_name = re.sub(r'[^a-zA-Z0-9_-]', '', img['name'])
                                            return f"images/{img_name}_{img['id']}.png", resp.content
                                    except Exception as e:
                                        print(f"Failed to download image {img['name']}: {e}")
                                return None

                            # Download in parallel with more workers
                            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
                                future_to_img = {executor.submit(download_image, img): img for img in relevant_images}
                                for future in concurrent.futures.as_completed(future_to_img):
                                    result = future.result()
                                    if result:
                                        filename, content = result
                                        zf.writestr(filename, content)
                    
                    end_time = time.time()
                    duration = end_time - start_time
                    status_text.empty()
                    st.success(f"ZIP Ready! Completed in {duration:.2f} seconds.")
                    st.download_button(
                        label="Download .zip",
                        data=zip_buffer.getvalue(),
                        file_name="figma_export.zip",
                        mime="application/zip"
                    )
        else:
            st.info("No top-level frames found.")
