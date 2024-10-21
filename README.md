# File Organization Assistant

This Python script helps you reorganize your file structure using AI-powered suggestions. It scans a directory, proposes a new organization structure, and applies the changes after user confirmation.

## Features

- Recursively scans directories
- Detects and handles large folders and programming projects
- Uses OpenAI's API to suggest an improved file organization
- Provides a dry run option to preview changes
- Creates a detailed change log
- Handles errors gracefully with user prompts to continue or exit

## Requirements

- Python 3.6+
- OpenAI API key

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/file-organization-assistant.git
   cd file-organization-assistant
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root and add your OpenAI API key:
   ```
   API_KEY=your_openai_api_key_here
   MODEL=gpt-3.5-turbo-0125
   DRY_RUN=true
   ```

## Usage

Run the script:

## License

This project is licensed under the MIT License. See the LICENSE file for details.
