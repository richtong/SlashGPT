import os
import requests
import json
import IPython

folder_path = "./output/notebooks"
if not os.path.isdir(folder_path):
    os.makedirs(folder_path)

ipython = IPython.InteractiveShell()

def create_notebook(name):
    # Create a new notebook
    counter = 0
    file_name = "notebook.ipynb"
    file_path = os.path.join(folder_path, file_name)

    while os.path.exists(file_path):
        counter += 1
        file_name = f"notebook{counter}.ipynb"
        file_path = os.path.join(folder_path, file_name)

    # Create the file
    with open(file_path, 'w') as file:
        # Write something to the file if needed
        file.write('Hello, world!')

    return json.dumps({'notebook_path':file_name})

def create_code_cell(notebook_path, code):
    cell = {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "source": code,
        "outputs": []
    }
    ipython.run_cell(code)
    ret = ipython.user_ns['_']
    # print(ret)
    return str(ret)

