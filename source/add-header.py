#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os

def get_header_format(file_extension):
    if file_extension == '.py':
        copyright_header = """#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""
    elif file_extension == '.ts':
        copyright_header = """/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
"""
    else:
        raise ValueError(f"Unsupported file extension: {file_extension}")
    
    return copyright_header

def add_copyright_header(file_path):
    # Get file extension
    _, file_extension = os.path.splitext(file_path)
    
    try:
        # Get the appropriate header format
        copyright_header = get_header_format(file_extension)
        
        # Read the current content of the file
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Check if the copyright header is already present
        if not content.startswith(copyright_header):
            # Prepend the copyright header to the content
            new_content = copyright_header + "\n" + content
            
            # Write the updated content back to the file
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(new_content)
            print(f"Added copyright header to: {file_path}")
        else:
            print(f"Copyright header already present in: {file_path}")
            
    except UnicodeDecodeError:
        print(f"Error: Unable to read {file_path} - file may be binary or use a different encoding")
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")

def process_directory(directory_path):
    # Walk through the directory and its subdirectories
    for root, dirs, files in os.walk(directory_path):
        # Process each .py and .ts file
        for file in files:
            if file.endswith(('.py', '.ts')):
                file_path = os.path.join(root, file)
                add_copyright_header(file_path)

if __name__ == "__main__":
    # Get the current directory path
    current_dir = os.getcwd()
    
    # Ask for confirmation before proceeding
    print(f"This will add copyright headers to all .py and .ts files in: {current_dir}")
    response = input("Do you want to proceed? (y/n): ")
    
    if response.lower() == 'y':
        process_directory(current_dir)
        print("Processing complete!")
    else:
        print("Operation cancelled.")
