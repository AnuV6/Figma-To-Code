# Figma to Code Extractor

A powerful Streamlit-based tool to extract design tokens, assets, and CSS from Figma files. This tool helps developers bridge the gap between design and code by providing a structured way to export colors, typography, images, and layout as CSS.

## 🚀 Features

- **Color Palette Extraction**: Automatically finds all unique solid colors used in the design.
- **Typography Styles**: Lists unique font families, weights, and sizes.
- **Node Inspector**: Dive into raw Figma properties and see instant CSS generation for any selected node.
- **Asset Management**: View and download all images and SVGs embedded in the design.
- **Bulk Export (ZIP)**:
    - Export design tokens (colors, typography) as JSON.
    - Recursive CSS generation for entire screens.
    - **New**: Download rendered screen frames as high-quality PNGs.
    - Parallelized downloads for lightning-fast exports.
- **Smart Caching**: Minimizes API calls to Figma, respecting rate limits.

## 🛠️ Setup

### Prerequisites
- Python 3.8+
- Figma Personal Access Token ([How to get one](https://help.figma.com/hc/en-us/articles/8085703771159-Manage-personal-access-tokens))

### Installation

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd figma-to-code
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   streamlit run app.py
   ```

## 📖 Usage

1. **Get your Token**: Enter your Figma Personal Access Token in the sidebar.
2. **Enter File URL**: Paste the URL of your Figma design file.
3. **Load File**: Click "Load File" to start the extraction process.
4. **Explore & Export**: Use the tabs to inspect different aspects of the design and use the "Bulk Export" tab to download everything as a ZIP package.

## 📁 Project Structure

- `app.py`: Main Streamlit application and UI logic.
- `src/figma_client.py`: API client for interacting with Figma's REST API.
- `src/parser.py`: Core logic for traversing Figma documents and generating CSS.
- `requirements.txt`: Python package dependencies.

## 📄 License

MIT License - feel free to use and modify for your own projects!
