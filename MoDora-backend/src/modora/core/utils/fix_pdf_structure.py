import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    import pikepdf
except ImportError:
    logger.error("pikepdf is not installed. Please install it using 'pip install pikepdf'.")
    sys.exit(1)

DATASET_DIR = Path("/home/yukai/project/MoDora/datasets/MMDA")

def fix_pdf_structure(pdf_path: Path) -> bool:
    """
    Attempts to fix a PDF file's structure using pikepdf (QPDF).
    Returns True if successful, False otherwise.
    """
    temp_path = pdf_path.with_suffix(".pdf.tmp")
    backup_path = pdf_path.with_suffix(".pdf.bak")
    
    try:
        # Open the PDF with pikepdf to repair structure issues
        # allow_overwriting_input=True allows saving to the same file, but we use a temp file for safety
        with pikepdf.Pdf.open(pdf_path) as pdf:
            pdf.save(temp_path)
        
        # Verify the temp file exists and has size > 0
        if not temp_path.exists() or temp_path.stat().st_size == 0:
            logger.error(f"Fix failed: Output file is empty or missing for {pdf_path}")
            if temp_path.exists():
                temp_path.unlink()
            return False

        # Backup original file
        if backup_path.exists():
            backup_path.unlink()
        pdf_path.rename(backup_path)
        
        # Replace original with fixed version
        temp_path.rename(pdf_path)
        logger.info(f"Fixed: {pdf_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to fix {pdf_path}: {e}")
        if temp_path.exists():
            temp_path.unlink()
        return False

def main():
    if not DATASET_DIR.exists():
        logger.error(f"Dataset directory not found: {DATASET_DIR}")
        return

    logger.info(f"Scanning {DATASET_DIR} for PDF files...")
    pdf_files = list(DATASET_DIR.rglob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files.")

    success_count = 0
    fail_count = 0

    for pdf_file in pdf_files:
        # Skip backup and temp files
        if pdf_file.name.endswith(".bak") or pdf_file.name.endswith(".tmp"):
            continue
            
        if fix_pdf_structure(pdf_file):
            success_count += 1
        else:
            fail_count += 1

    logger.info(f"Processing complete. Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    main()
