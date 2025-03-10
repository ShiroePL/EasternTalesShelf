function sanitizeFolderName(folderName) {
    // First, handle common special cases
    let name = folderName.replace(/:/g, '_')
                        .replace(/\(/g, '_')
                        .replace(/\)/g, '_');
    
    // Replace any other non-alphanumeric characters (except dash) with underscore
    name = name.replace(/[^a-zA-Z0-9\-]/g, '_');
    
    // Replace multiple underscores with single underscore
    name = name.replace(/_+/g, '_');
    
    // Remove leading/trailing underscores
    name = name.trim('_');
    
    // Ensure the name isn't empty
    if (!name) {
        name = "unnamed";
    }
    
    return name;
} 