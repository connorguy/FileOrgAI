import os
import shutil
from typing import List, Dict
from dotenv import load_dotenv
from openai import OpenAI
import prompts
from loguru import logger


load_dotenv()
client = OpenAI(api_key=os.getenv("API_KEY"))

large_folders = []


def get_relative_paths(directory: str) -> List[str]:
    """
    Recursively get relative paths of files in a directory, handling large folders.

    This function walks through the given directory, prompts the user for large folders
    (>30 files), and collects relative paths of non-hidden files.

    Args:
        directory (str): The root directory to start the search from.

    Returns:
        List[str]: A list of relative file paths.

    Global effects:
        Modifies the global 'large_folders' list to store excluded large folders.
    """
    relative_paths = []
    for root, dirs, files in os.walk(directory):
        # Check if the current folder is large (>30 files) and not the top-level directory
        is_project = (
            any(
                file.lower()
                in [
                    "requirements.txt",
                    "setup.py",
                    "package.json",
                    "cargo.toml",
                    "makefile",
                    "cmakelists.txt",
                    ".git",
                    ".gitignore",
                    "readme.md",
                    "pipfile",
                    "poetry.lock",
                    "build.gradle",
                    "pom.xml",
                    "gemfile",
                    "composer.json",
                    "package-lock.json",
                    "yarn.lock",
                    "go.mod",
                    "dockerfile",
                    "docker-compose.yml",
                    ".travis.yml",
                    "jenkinsfile",
                    ".gitlab-ci.yml",
                    "tox.ini",
                    "pytest.ini",
                    ".eslintrc",
                    "tsconfig.json",
                ]
                for file in files
            )
            or "src" in dirs
        )

        if is_project or (len(files) > 30 and root != directory):
            folder_path = os.path.relpath(root, directory)

            if is_project:
                user_choice = input(
                    f"Programming project detected: {folder_path} ({len(files)} files). Include? (y/n): "
                ).lower()
            else:
                user_choice = input(
                    f"Large folder detected: {folder_path} ({len(files)} files). Include? (y/n): "
                ).lower()

            if user_choice == "y":
                if is_project:
                    logger.info(
                        f"Including programming project: ({len(files)} files) {folder_path}"
                    )
                else:
                    logger.info(
                        f"Including large folder: ({len(files)} files) {folder_path}"
                    )
            else:
                # Exclude project or large folder and skip its subdirectories
                large_folders.append(folder_path)
                if is_project:
                    logger.info(
                        f"Excluding programming project: ({len(files)} files) {folder_path}"
                    )
                else:
                    logger.info(
                        f"Excluding large folder: ({len(files)} files) {folder_path}"
                    )
                dirs[:] = []  # Clear the list of subdirectories to skip them
                continue

        # Process files in the current directory
        for file in files:
            # Exclude hidden (dot) files and OS-specific files
            if not file.startswith(".") and file.lower() not in [
                "$recycle.bin",
                "desktop.ini",
                "thumbs.db",
                "ntuser.dat",
                "ntuser.ini",
                "ntuser.pol",
                "usrclass.dat",
                "iconcache.db",
                "pagefile.sys",
                "hiberfil.sys",
                "swapfile.sys",
                "bootmgr",
                "bootnxt",
                "bootfont.bin",
                "autorun.inf",
                "system volume information",
            ]:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, directory)
                relative_paths.append(relative_path)

    return relative_paths


def check_directory_permissions(directory: str) -> bool:
    """
    Check if the current user has read and write permissions for the given directory.

    Args:
        directory (str): The path to the directory to check.

    Returns:
        bool: True if the user has both read and write permissions, False otherwise.
    """
    if not os.path.exists(directory):
        logger.error(f"The directory {directory} does not exist.")
        return False

    read_permission = os.access(directory, os.R_OK)
    write_permission = os.access(directory, os.W_OK)
    execute_permission = os.access(directory, os.X_OK)

    if read_permission and write_permission and execute_permission:
        logger.info(f"User has read, write, and execute permissions for {directory}")
        return True
    else:
        logger.error(f"Insufficient permissions for {directory}")
        logger.error(
            f"Read: {read_permission}, Write: {write_permission}, Execute: {execute_permission}"
        )
        return False


def get_ai_organization(relative_paths: List[str]) -> Dict:
    completion = client.beta.chat.completions.parse(
        model=os.getenv("MODEL"),
        messages=[
            {"role": "system", "content": prompts.prompt_file_org},
            {"role": "user", "content": "\n".join(relative_paths)},
        ],
        response_format=prompts.NewStructure,
    )

    return completion.choices[0].message.parsed


def display_and_confirm_changes(organization: prompts.NewStructure) -> bool:
    print("Large folders to be moved to the top level directory:")
    for folder in large_folders:
        print(f"  - {folder}")

    print("New folders to be created:")
    for folder in organization.new_folders:
        print(f"  - {folder}")

    print("\nFile moves and renames:")
    for file_path in organization.FilePath:
        print(f"  - {file_path.original} -> {file_path.new}")

    return input("\nDo you want to proceed with these changes? (y/n): ").lower() == "y"


def apply_changes(
    directory: str, organization: prompts.NewStructure, large_folders: List[str]
):
    """
    Apply the organizational changes to the specified directory.

    Args:
        directory (str): The path to the directory being organized.
        organization (prompts.NewStructure): The new structure for the directory.
        large_folders (List[str]): List of large folders to be moved to the top level.

    Raises:
        OSError: If there's an issue with file operations.
    """
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    logger.info("Dry run: {}", dry_run)

    def execute_or_log(action, log_message):
        if dry_run:
            logger.info(f"[DRY RUN] Would {log_message}")
        else:
            logger.info(log_message)
            action()

    def append_to_log(message):
        with open(
            os.path.join(directory, "reorganization_change_log.txt"), "a"
        ) as log_file:
            log_file.write(f"\n{message}\n")

    try:
        # Create deprecated folder
        deprecated_folder = os.path.join(directory, "deprecated")
        execute_or_log(
            lambda: os.makedirs(deprecated_folder, exist_ok=True),
            f"create deprecated folder: {deprecated_folder}",
        )

        # Move large folders to the top level directory
        for folder in large_folders:
            src = os.path.join(directory, folder)
            dst = os.path.join(directory, os.path.basename(folder))
            if src != dst:
                execute_or_log(
                    lambda: shutil.move(src, dst), f"move large folder: {src} -> {dst}"
                )

        # Create new folders
        for folder in organization.new_folders:
            folder_path = os.path.join(directory, folder)
            execute_or_log(
                lambda: os.makedirs(folder_path, exist_ok=True),
                f"create folder: {folder_path}",
            )

        # Move and rename files
        for file_path in organization.FilePath:
            src = os.path.join(directory, file_path.original)
            dst = os.path.join(directory, file_path.new)
            try:
                execute_or_log(
                    lambda: (
                        os.makedirs(os.path.dirname(dst), exist_ok=True),
                        shutil.move(src, dst),
                    ),
                    f"move/rename file: {src} -> {dst}",
                )
            except (PermissionError, OSError) as e:
                error_message = f"Error moving file: {src} -> {dst}. Error: {e}"
                logger.error(error_message)
                append_to_log(f"Error Log:\n{error_message}")
                user_choice = input(
                    "Error occurred. Do you want to skip this file and continue? (y/n): "
                ).lower()
                if user_choice != "y":
                    logger.info("User chose to exit. Stopping the process.")
                    return

        # Move old folders to deprecated folder
        old_folders = (
            set(os.listdir(directory))
            - set(organization.new_folders)
            - set([os.path.basename(f) for f in large_folders])
        )
        for folder in old_folders:
            src = os.path.join(directory, folder)
            dst = os.path.join(deprecated_folder, folder)
            if os.path.isdir(src) and src != deprecated_folder:
                execute_or_log(
                    lambda: shutil.move(src, dst),
                    f"move old folder to deprecated: {src} -> {dst}",
                )

    except OSError as e:
        error_message = f"Error applying changes: {e}"
        logger.error(error_message)
        user_choice = input(
            "An error occurred. Do you want to continue with the remaining changes? (y/n): "
        ).lower()
        if user_choice != "y":
            logger.info("User chose to exit. Stopping the process.")
            append_to_log(f"Error Log:\n{error_message}")
            return
        else:
            append_to_log(f"Error Log:\n{error_message}\nUser chose to continue.")
    if dry_run:
        logger.info("Dry run completed. No changes were made.")
    else:
        logger.info("All changes applied successfully.")


def create_change_log(
    directory: str, organization: prompts.NewStructure, large_folders: List[str]
):
    """
    Create a change log file detailing the reorganization changes.

    Args:
    directory (str): The path to the directory being organized.
    organization (prompts.NewStructure): The new structure for the directory.
    large_folders (List[str]): List of large folders that were moved to the top level.
    """
    change_log_path = os.path.join(directory, "reorganization_change_log.txt")

    with open(change_log_path, "w") as log_file:
        log_file.write("Directory Reorganization Change Log\n")
        log_file.write("====================================\n\n")

        log_file.write("New Folders Created:\n")
        for folder in organization.new_folders:
            log_file.write(f"- {folder}\n")
        log_file.write("\n")

        log_file.write("Files Moved/Renamed:\n")
        for file_path in organization.FilePath:
            log_file.write(f"- {file_path.original} -> {file_path.new}\n")
        log_file.write("\n")

        log_file.write("Large Folders Moved to Top Level:\n")
        for folder in large_folders:
            log_file.write(f"- {folder}\n")
        log_file.write("\n")

        deprecated_folder = os.path.join(directory, "deprecated")
        log_file.write(f"Old folders moved to: {deprecated_folder}\n")

    logger.info(f"Change log created at: {change_log_path}")


def main():
    logger.info("Starting the file organization process")
    directory = input("Enter the directory path to organize: ")
    logger.debug(f"User input directory: {directory}")

    if not check_directory_permissions(directory):
        logger.error("Insufficient permissions for the specified directory. Exiting.")
        return

    relative_paths = get_relative_paths(directory)
    logger.debug(f"Found {len(relative_paths)} files in the directory")

    logger.info("Requesting AI organization")
    organization = get_ai_organization(relative_paths)
    # logger.debug("Received organization plan: {}",organization)

    if display_and_confirm_changes(organization):
        logger.info("User confirmed changes, applying...")
        create_change_log(directory, organization, large_folders)
        apply_changes(directory, organization, large_folders)
        logger.info("Process completed.")
        print("Process completed.")
    else:
        logger.info("User cancelled the operation")
        print("Operation cancelled.")


if __name__ == "__main__":
    main()
