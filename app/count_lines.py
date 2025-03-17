import os

class CodeLineCounter:
    """Class to count lines in various code files across a directory and its subfolders."""
    
    def __init__(self, root_folder="."):
        """Initialize with root folder (default is current folder)."""
        self.root_folder = root_folder
        self.file_extensions = {
            ".js": {"name": "JavaScript", "files": [], "lines": 0},
            ".html": {"name": "HTML", "files": [], "lines": 0},
            ".css": {"name": "CSS", "files": [], "lines": 0},
            ".py": {"name": "Python", "files": [], "lines": 0}
        }
        self.total_files = 0
        self.total_lines = 0
    
    def find_files(self):
        """Recursively find all target files in the folder and subfolders."""
        for root, _, files in os.walk(self.root_folder):
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in self.file_extensions:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.root_folder)
                    self.file_extensions[file_ext]["files"].append(rel_path)
        
        # Count total files
        self.total_files = sum(len(ext_data["files"]) for ext_data in self.file_extensions.values())
        
        return self.total_files
    
    def count_lines(self):
        """Count lines in all found files."""
        # First, find all files if not already done
        if self.total_files == 0:
            self.find_files()
            
        if self.total_files == 0:
            print("No matching files found.")
            return 0
        
        # Process each file type
        for ext, ext_data in self.file_extensions.items():
            if ext_data["files"]:
                print(f"\n{ext_data['name']} Files:")
                print("-" * 50)
                
                for file_path in ext_data["files"]:
                    full_path = os.path.join(self.root_folder, file_path)
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            lines = sum(1 for _ in f)
                            ext_data["lines"] += lines
                            print(f"{file_path}: {lines} lines")
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
                
                print(f"\nSubtotal: {ext_data['lines']} lines in {len(ext_data['files'])} {ext_data['name']} files")
        
        # Calculate grand total
        self.total_lines = sum(ext_data["lines"] for ext_data in self.file_extensions.values())
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for ext_data in self.file_extensions.values():
            if ext_data["files"]:
                print(f"{ext_data['name']}: {len(ext_data['files'])} files, {ext_data['lines']} lines")
        
        print("-" * 60)
        print(f"Total: {self.total_files} files, {self.total_lines} lines")
        
        return self.total_lines

# When run directly
if __name__ == "__main__":
    counter = CodeLineCounter()
    counter.count_lines()
