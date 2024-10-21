from typing import List

from pydantic import BaseModel

prompt_file_org = """
Given the following contents from a top-level directory, reorganize them into new folders and rename the files where needed. 

1. Maximum depth of 1 folder (e.g., folder/file.txt).
2. All files MUST be moved to a new location, even if it’s just to a new root folder.
3. The new structure should be more organized and descriptive using file names and types for context.
4. **Remove any existing subfolder structure** and keep only the file's context.
5. Do not use spaces in new paths, only underscores.
6. All new paths should also be lowercase only.
7. Do not use "deprecated" as a folder name.

---
Sample input: `assets/4x/asset_10@4x.png`
Sample output: `images/asset_10_4x.png`
"""

class NewStructure(BaseModel):
    new_folders: List[str]
    FilePath: List['FilePath']

class FilePath(BaseModel):
    original: str
    new: str
