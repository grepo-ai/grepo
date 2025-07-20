from dotenv import load_dotenv
import os
import httpx
from zipfile import ZipFile
from uuid import uuid4
import glob


load_dotenv()

BASE_DIR = os.getcwd()


class GithubCloner:
    def __init__(self):
        self.repo_links = []
        self.search_base_url = "https://api.github.com/search/repositories?q="
        self.request_headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.getenv('GH_TOKEN')}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def get_search_results(self, search_term):
        search_url = (
            self.search_base_url
            + search_term
            + "&sort=stars"
            + "&order=desc"
            + "&per_page=50"
        )
        resp = httpx.get(search_url, headers=self.request_headers)

        for repo_data in resp.json()["items"]:
            self.repo_links.append(repo_data["url"])
        return self.repo_links

    def download_repo(self):
        repo_dump_dir_path = os.path.join(BASE_DIR, "repos-dump")
        os.makedirs(repo_dump_dir_path, exist_ok=True)

        with httpx.Client(
            headers=self.request_headers, follow_redirects=True
        ) as client:
            for repo_url in self.repo_links:
                repo_download_url = f"{repo_url}/zipball"
                print(f"⬇️ Downloading repo --> {repo_download_url} ⬇️")
                resp = client.get(repo_download_url)
                with open(f"{repo_dump_dir_path}/{uuid4()}.zip", "wb") as file:
                    file.write(resp.content)

        print("✅ Downloaded repo code successfully")

    def extract_zip(self):
        zip_files_dir = os.path.join(BASE_DIR, "repos-dump")
        zip_files = glob.glob(f"{zip_files_dir}/*.zip")

        for file_path in zip_files:
            with ZipFile(f"{file_path}", "r") as zip_obj:
                zip_obj.extractall(path=zip_files_dir)
                print("⚡️Repo code extraction done⚡️")
                os.remove(file_path)


if __name__ == "__main__":
    print("=== 🔥 Starting the github repo cloner 🔥 ===")
    gh_cloner = GithubCloner()

    search_results = gh_cloner.get_search_results("python")
    print("=== Downloading repos ===.")
    gh_cloner.download_repo()
    gh_cloner.extract_zip()
