import os
from typing import Dict
from playwright.sync_api import sync_playwright

class BrowserUploadReceiptSkill:
    def __init__(self, downloads_dir: str):
        self.downloads_dir = downloads_dir
        os.makedirs(self.downloads_dir, exist_ok=True)

    def run(self, file_path: str) -> Dict:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            html = '<input type="file" id="f"><button id="ok">Upload</button><script>document.getElementById("ok").onclick=()=>{const a=document.createElement("a");a.href="data:text/plain;base64,UmVjZWlwdDogT0s=";a.download="receipt.txt";a.click();};</script>'
            page.goto("data:text/html," + html)
            page.set_input_files("#f", file_path)
            with page.expect_download() as dl:
                page.click("#ok")
            download = dl.value
            save_to = os.path.join(self.downloads_dir, download.suggested_filename)
            download.save_as(save_to)
            context.close()
            browser.close()
        return {"path": save_to, "type": "receipt", "size": os.path.getsize(save_to)}
