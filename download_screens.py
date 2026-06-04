import urllib.request
import os

urls = {
    "product_features.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ7Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpaCiVodG1sXzMzZjY3ZTI2YjFhNTQ3NTI4NjI0OWJlMTlkNWMxODZiEgsSBxDO-ouS_A8YAZIBIwoKcHJvamVjdF9pZBIVQhMyMjQ2MjkyNDk3Mzk2ODQ1MTIy&filename=&opi=89354086",
    "home.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ7Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpaCiVodG1sX2IxODgyYjJhNWM5ZDQzZWNiOWMwYTc2ZDQwNjUxZTI4EgsSBxDO-ouS_A8YAZIBIwoKcHJvamVjdF9pZBIVQhMyMjQ2MjkyNDk3Mzk2ODQ1MTIy&filename=&opi=89354086",
    "workspace.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ7Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpaCiVodG1sXzQ2ZTEzNzg4OGEwYzQ4ODI5NjViODFhOWMwM2ExYTljEgsSBxDO-ouS_A8YAZIBIwoKcHJvamVjdF9pZBIVQhMyMjQ2MjkyNDk3Mzk2ODQ1MTIy&filename=&opi=89354086",
    "pricing_about.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ7Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpaCiVodG1sX2MzYjk5NjBkMTRiNzRjMWJiNzliZGViMmFlZjAyNmUzEgsSBxDO-ouS_A8YAZIBIwoKcHJvamVjdF9pZBIVQhMyMjQ2MjkyNDk3Mzk2ODQ1MTIy&filename=&opi=89354086"
}

output_dir = "front-end-reference"
os.makedirs(output_dir, exist_ok=True)

for filename, url in urls.items():
    dest = os.path.join(output_dir, filename)
    print(f"Downloading {url} to {dest}...")
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"Downloaded {filename} successfully.")
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
