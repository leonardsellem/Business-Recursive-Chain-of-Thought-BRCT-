import subprocess
import os
import logging
import argparse # Added argparse
from pathlib import Path

# Configure logging
# Changed level to WARNING for CLI usage to reduce noise, INFO for debugging if needed
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the path to the CSS file relative to this script's location
# Assuming file_converter.py is in cline_utils/ and css is in cline_utils/assets/
CSS_FILE_PATH = Path(__file__).parent / "assets" / "professional_style.css"
# Get the absolute path for the pandoc command
ABSOLUTE_CSS_PATH = CSS_FILE_PATH.resolve()

def convert_markdown_to_pdf(markdown_file_path: str, output_directory: str = None):
    """
    Converts a Markdown file to a styled PDF using Pandoc and WeasyPrint.

    Args:
        markdown_file_path (str): The absolute path to the input Markdown file.
        output_directory (str, optional): The directory to save the PDF file.
                                         Defaults to the same directory as the Markdown file.

    Returns:
        str: The path to the generated PDF file, or None if conversion failed.
    """
    markdown_path = Path(markdown_file_path)
    if not markdown_path.is_file() or markdown_path.suffix.lower() != '.md':
        logging.error(f"Invalid Markdown file path: {markdown_file_path}")
        return None

    if not ABSOLUTE_CSS_PATH.is_file():
        logging.error(f"CSS file not found at expected location: {ABSOLUTE_CSS_PATH}")
        return None

    # Determine output path
    if output_directory:
        output_dir = Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True) # Ensure output directory exists
    else:
        output_dir = markdown_path.parent

    pdf_file_name = markdown_path.stem + ".pdf"
    pdf_file_path = output_dir / pdf_file_name

    # Construct the Pandoc command
    # Using WeasyPrint as the PDF engine and specifying the CSS file
    command = [
        "pandoc",
        str(markdown_path.resolve()),         # Absolute path to input MD
        "-o", str(pdf_file_path.resolve()),   # Absolute path to output PDF
        "--pdf-engine=weasyprint",
        f"--css={str(ABSOLUTE_CSS_PATH)}",
        "--metadata", "title=" + markdown_path.stem.replace('_', ' ').title(), # Basic title metadata
        "--toc", # Include table of contents
        "--toc-depth=3" # Set TOC depth
    ]

    logging.info(f"Executing command: {' '.join(command)}")

    try:
        # Execute the command
        process = subprocess.run(command, check=True, capture_output=True, text=True)
        logging.info(f"Successfully converted '{markdown_path.name}' to '{pdf_file_path.name}'")
        logging.debug(f"Pandoc stdout:\n{process.stdout}")
        logging.debug(f"Pandoc stderr:\n{process.stderr}")
        return str(pdf_file_path.resolve())
    except FileNotFoundError:
        logging.error("Error: 'pandoc' command not found. Make sure Pandoc is installed and in your PATH.")
        return None
    except subprocess.CalledProcessError as e:
        logging.error(f"Pandoc conversion failed for {markdown_path.name}.")
        logging.error(f"Return code: {e.returncode}")
        logging.error(f"Stderr:\n{e.stderr}")
        logging.error(f"Stdout:\n{e.stdout}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during conversion: {e}")
        return None

def main():
    """ Main function to handle command-line arguments """
    parser = argparse.ArgumentParser(description="Convert a Markdown file to a styled PDF using Pandoc and WeasyPrint.")
    parser.add_argument(
        "markdown_file_path",
        type=str,
        help="The absolute path to the input Markdown file."
    )
    parser.add_argument(
        "--output_directory",
        type=str,
        default=None,
        help="Optional. The directory to save the PDF file. Defaults to the Markdown file's directory."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (INFO level)."
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    logging.info(f"Starting conversion for: {args.markdown_file_path}")
    if args.output_directory:
        logging.info(f"Output directory specified: {args.output_directory}")

    pdf_path = convert_markdown_to_pdf(args.markdown_file_path, args.output_directory)

    if pdf_path:
        # Print the output path clearly for the calling process (like Cline)
        print(f"PDF_GENERATED_SUCCESSFULLY:{pdf_path}")
        logging.info(f"PDF generated successfully at: {pdf_path}")
    else:
        print("PDF_GENERATION_FAILED")
        logging.error("PDF generation failed.")

if __name__ == '__main__':
    main()
