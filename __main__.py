from zipfile import ZipFile
from rarfile import RarFile
from tarfile import TarFile
from py7zr import SevenZipFile
import shutil
from typing import List

import os, time

from gooey import GooeyParser, Gooey
from pathlib import Path
import img2pdf
from pyrsistent import pmap
from PIL import Image, UnidentifiedImageError

COMPRESSED_FORMATS = pmap ( {
    "zip": ZipFile,
    "rar": RarFile,
    "tar": TarFile,
    "7z": SevenZipFile,
} )

def isImage ( file: os.PathLike ):
    try: Image.open ( file )
    except UnidentifiedImageError: # not an image
        return False
    return True

def splitExtDotless ( path: os.PathLike | str ):
    pure_filename, ext = os.path.splitext ( path )
    # Get clean file extension with no dot, and in lower case
    if len ( ext ) > 0: ext = ext [ 1 : ].lower ( )
    return pure_filename, ext

def uniqueFilename ( path: Path ) -> Path:
    if path.exists ( ):
        dirpath, filename = os.path.split ( path )
        pure_filename, ext = os.path.splitext ( filename )
        i = 1
        while True:
            new_path = Path ( dirpath )/f"{pure_filename}({i}){ext}"
            if not new_path.exists ( ):
                return new_path 
            i += 1
    else:
        return path

def isFolderEmpty ( path: Path ):
    return len ( os.listdir ( path ) ) == 0

def processCompressedFile ( 
        compressed_file: Path, /, 
        output_path: Path,
        ignore_extract_failed: bool = False,
        ignore_convert_failed: bool = False,
        skip_non_image: bool = False,
        replace_existing: bool = False,
) -> bool:
    _, compressed_filename = os.path.split ( compressed_file )
    compressed_pure_filename, compressed_ext = splitExtDotless ( compressed_filename )
    
    # Find the right compressed file class
    Compressed = COMPRESSED_FORMATS.get ( compressed_ext )

    # Ignore non-compressed files
    if Compressed is None: 
        print ( 
            f"    File \"{compressed_filename}\" is not a compressed file, "
            "and is therefore ignored." 
        )
        return None
    
    # Create output path if it does not exist
    if not output_path.exists ( ): output_path.mkdir ( parents = True )

    # Create a temp folder to store extracted files
    # Use a name that is not likely to repeat
    timestamp = time.monotonic_ns ( )
    temp_path = uniqueFilename ( 
        output_path/
        f"__CompressedImages2PDF_temp_{compressed_pure_filename}_{timestamp}" 
    )
    temp_path.mkdir ( parents = True )

    print ( 
        f"    Extracting \"{compressed_filename}\" to \"{temp_path}\" "
        f"using {Compressed.__name__}." 
    )
    try:
        with Compressed ( compressed_file ) as compressed:
            # extract content of the compressed file into the temp folder
            compressed.extractall ( temp_path )
    except Exception as e:
        print ( f"    Extraction failed for file \"{compressed_filename}\"." )
        print ( f"      Error message: {e}" )
        if not ignore_extract_failed:
            shutil.copy ( 
                src = compressed_file,
                dst = output_path/compressed_filename,
            )
            print ( f"      File \"{compressed_filename}\" is directly moved to \"{output_path}\"." )
        shutil.rmtree ( temp_path )
        return False
    else:
        print ( "    Extraction completed." )

    print ( f"    Looking for images in \"{temp_path}\"..." )
    images = [ ]
    for dirpath, _, filenames in temp_path.walk ( ):
        for filename in filenames:
            filepath = dirpath/filename
            if isImage ( filepath ):
                print ( f"      Found image file \"{filename}\"." )
                images.append ( dirpath/filename )
            elif not skip_non_image: # not image
                print ( 
                    f"      File \"{filename}\" is not an image, "
                    f"and is therefore directly moved to \"{output_path}\"." 
                )
                shutil ( 
                    src = dirpath/filename,
                    dst = output_path/filename,
                )
    
    print ( f"    Found {len(images)} image file(s) in total. Converting to PDF..." )
    try:
        pdf_src = img2pdf.convert ( *images )
    except Exception as e:
        print ( 
            f"    Conversion fails for file \"{compressed_filename}\"." 
        )
        print ( f"      Error message: {e}" )
        if ignore_convert_failed:
            shutil.rmtree ( temp_path )
        else:
            # Should an error happen during conversion to PDF, 
            # the extracted files are preserved in a folder.
            preserved_path = output_path/f"{compressed_pure_filename}_extracted"
            print ( f"      Extracted files are preserved at \"{preserved_path}\". " )
            if preserved_path.exists ( ): 
                if replace_existing:
                    shutil.rmtree ( preserved_path )
                else:
                    preserved_path = uniqueFilename ( preserved_path )
            temp_path.rename ( preserved_path )
        return False
    else:
        pdf_path = output_path/f"{compressed_pure_filename}.pdf"
        if pdf_path.exists ( ) and ( not replace_existing ):
            pdf_path = uniqueFilename ( pdf_path )
        with pdf_path.open ( "wb" ) as pdf_file: pdf_file.write ( pdf_src )
        shutil.rmtree ( temp_path )
        print ( 
            f"    Conversion finished for file \"{compressed_filename}\". "
            f"PDF stored as \"{pdf_path}\"." 
        )
        return True

@Gooey ( 
    program_name = "Compressed Images to PDF Converter", 
    program_description = "Convert compressed files with images to PDF files.",
    # language = "chinese",
    progress_regex = r"Completed: (?P<current>\d+) / (?P<total>\d+)",
    progress_expr = "current / total * 100",
    required_cols = 1,
    optional_cols = 1,
    tabbed_groups = True,
)
def main ( ):
    p = GooeyParser ( )

    g1 = p.add_argument_group ( "Input and Output" )
    g1.add_argument (
        "--input-path", "-i",
        metavar = "Input Path",
        help = "The folder in which your compressed files are located.",
        widget = 'DirChooser',
        required = True,
        type = Path,
    )
    g1.add_argument (
        "--output-path", "-o",
        metavar = "Output Path",
        help = ( 
            "The folder to place the output PDF files. "
            "The directory Structure of the input folder will be preserved."
        ),
        default = str ( Path.cwd ( ) ),
        widget = 'DirChooser',
        required = True,
        type = Path,
    )


    g2 = p.add_argument_group ( "Options" )
    g2.add_argument ( 
        "--skip-non-image",
        action = "store_true",
        widget = "BlockCheckbox",
        metavar = "Skip Non-Image Files",
        help = (
            "When selected, non-image files extracted from the compressed files "
            "will be ignored.\n"
            "By default, non-image files are preserved and directly moved to the output path."
        ),
    )
    g2.add_argument ( 
        "--ignore-convert-failed",
        action = "store_true",
        widget = "BlockCheckbox",
        metavar = "Remove Extracted Files for Failed PDF Conversions",
        help = (
            "When checked, once the conversion to PDF fails, "
            "extracted files will be directly deleted.\n"
            "By default, extracted files will be preserved in an independent folder "
            "and moved to the output path when conversion fails."
        ),
    )
    g2.add_argument (
        "--ignore-extract-failed",
        action = "store_true",
        widget = "BlockCheckbox",
        metavar = "Ignore Compressed Files if Extraction Fails",
        help = (
            "When checked, once extraction of a compressed file fails, it will be ignored.\n"
            "By default, failed compressed files will be kept and moved to the output folder."
        )
    )
    g2.add_argument (
        "--flatten",
        action = "store_true",
        widget = "BlockCheckbox",
        metavar = "Flattened Directory Structure",
        help = (
            "If checked, all output files will be put directly in the output folder.\n"
            "By default, directory structure of the input folder is preserved."
        )
    )
    g2.add_argument (
        "--replace-existing",
        action = "store_true",
        widget = "BlockCheckbox",
        metavar = "Auto-Replace Existing Files",
        help = (
            "If checked, existing files will be automatically replaced. \n"
            "By default, these files will be given an alternative name to avoid name clash."
        )
    )
    g2.add_argument (
        "--password", "--pwd",
        metavar = "Password",
        help = ( 
            "Password of the compressed files (if there is any)." 
        ),
        widget = "PasswordField",
    )

    args = p.parse_args ( )

    flatten: bool = args.flatten
    ignore_extract_failed: bool = args.ignore_extract_failed
    ignore_convert_failed: bool = args.ignore_convert_failed
    skip_non_image: bool = args.skip_non_image
    replace_existing: bool = args.replace_existing

    input_path: Path = args.input_path
    output_path: Path = args.output_path
    if not isFolderEmpty ( output_path ):
        output_path = args.output_path/"out"
        if output_path.exists ( ) and ( not replace_existing ):
            output_path = uniqueFilename ( output_path )

    print ( f"Searching compressed files in {input_path}..." )
    compressed_files: List [ Path ] = [ ]
    for dirpath, _, filenames in input_path.walk ():
        for filename in filenames:
            _, ext = splitExtDotless ( filename )
            if ext in COMPRESSED_FORMATS:
                compressed_file = dirpath/filename
                compressed_files.append ( compressed_file )
                print ( f"  Found compressed file \"{compressed_file}\"." )

    n_compressed = len ( compressed_files )
    print ( f"Searching completed. Found {n_compressed} compressed files." )

    print ( "Processing compressed files..." )
    completed = 0
    success_count = 0
    for compressed_file in compressed_files:
        print ( f"  Processing file \"{compressed_file}\"" )
        success = processCompressedFile ( 
            compressed_file,
            output_path = ( 
                output_path if flatten else ( 
                    output_path/
                    compressed_file.parent.relative_to ( input_path ) 
                )
            ),
            ignore_extract_failed = ignore_extract_failed,
            ignore_convert_failed = ignore_convert_failed,
            skip_non_image = skip_non_image,
            replace_existing = replace_existing,
        )
        if success: success_count += 1
        completed += 1
        print ( f"  Completed: {completed} / {n_compressed}." )

    print ( 
        f"All files processed. "
        f"{success_count} successful, "
        f"{n_compressed - success_count} failed" 
    )

if __name__ == "__main__":
    main ( )

