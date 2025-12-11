# Story Mapper

## Description
This project generates simple maps from narrative data using natural language processing and constraint satisfaction.

https://github.com/user-attachments/assets/8f46f5e3-e1d7-4d38-8472-99471a061789

## Requirements
- Python 3.10+
- pip
- See `requirements.txt` for dependencies

## Setup

1. **Clone the repository:**

(If you are working with the source code you can skip to step 2.)

My recommendation is to use Github Desktop but you can clone the repository through your preferred method.
To use Github Desktop, click the green 'Code' then select 'Open with Github Desktop' and follow the prompts.

 Alternatively, you can use the CLI:
```bash
gh repo clone tforteni/story-map
```

If you are working with the source code you can skip to step 2.

2. **Change to the code directory:**
```bash
cd story-map
cd code
```

3. **Create a virtual environment (optional but recommended):**
```bash
# macOS/Linux
python3.12 -m venv venv
source venv/bin/activate

# Windows
python3.12 -m venv venv
venv\Scripts\activate
```

4. **Install the requirements:**
```bash
pip install -r requirements.txt
```

5. **Run the project locally**
```bash
python3 -m src.main INPUT_FILE WITH_ROUTES(1 or 0)
# e.g. python3 -m src.main src/data/example1.txt 1
# example15.txt, example18.txt, and example19.txt are fun ones to try!
```

You can run the program on your own text files. I suggest using simple sentences. The generated map will be called map.png and will be saved in the code directory.

The Google Docs integration code in the google-docs-integration folder is not able to be run locally but is included for reference.

## Example Gallery

<img width="1470" height="497" alt="Screenshot 2025-11-29 at 1 11 39 PM" src="https://github.com/user-attachments/assets/8e0f6b78-2237-4a28-8c50-e7074ac53e0e" />
<img width="1470" height="588" alt="Screenshot 2025-11-29 at 1 27 40 PM" src="https://github.com/user-attachments/assets/0fdef762-7d4c-4361-bd23-1df8c7322a04" />

