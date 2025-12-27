import requests
import os
import time

class FigmaClient:
    def __init__(self, token):
        self.base_url = "https://api.figma.com/v1"
        self.headers = {
            "X-Figma-Token": token
        }

    def get_file(self, file_key):
        """
        Fetches the Figma file content.
        """
        url = f"{self.base_url}/files/{file_key}"
        # Let app.py handle exceptions so we can show them to user
        response = requests.get(url, headers=self.headers)
        
        # Simple retry logic for 429
        if response.status_code == 429:
             retry_after = int(response.headers.get("Retry-After", 60))
             print(f"Rate limited. Waiting {retry_after} seconds...")
             time.sleep(retry_after)
             # Retry once
             response = requests.get(url, headers=self.headers)
             
        response.raise_for_status()
        return response.json()

    def get_file_nodes(self, file_key, ids):
        """
        Fetches specific nodes from a file.
        ids: list of node IDs (strings)
        """
        ids_str = ",".join(ids)
        url = f"{self.base_url}/files/{file_key}/nodes?ids={ids_str}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching nodes: {e}")
            return None

    def get_image_fills(self, file_key):
        """
        Get image fills from a file.
        """
        url = f"{self.base_url}/files/{file_key}/images"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching images: {e}")
            return None
    def get_images(self, file_key, ids, format='png', scale=1):
        """
        Get rendered images for specific nodes.
        ids: list of node IDs (strings)
        format: 'png', 'jpg', 'svg', 'pdf'
        scale: 1, 2, 3, 4
        """
        ids_str = ",".join(ids)
        url = f"{self.base_url}/images/{file_key}?ids={ids_str}&format={format}&scale={scale}"
        try:
            response = requests.get(url, headers=self.headers)
            # Handle rate limiting
            if response.status_code == 429:
                 retry_after = int(response.headers.get("Retry-After", 60))
                 time.sleep(retry_after)
                 response = requests.get(url, headers=self.headers)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching rendered images: {e}")
            return None
