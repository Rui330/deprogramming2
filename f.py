import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import re

# --- 1. データベース準備 ---
dbname = 'google_repos.db'
conn = sqlite3.connect(dbname)
cur = conn.cursor()

# 何度実行しても大丈夫なように、一度テーブルをリセット（削除して再作成）します
cur.execute('DROP TABLE IF EXISTS repositories')
cur.execute('''
    CREATE TABLE repositories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        language TEXT,
        stars INTEGER
    )
''')
conn.commit()

# --- 2. スクレイピング実行 (ページ指定ループ) ---
base_url = "https://github.com/google?tab=repositories"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 1ページ目から4ページ目までを取得 (約100件以上になります)
target_pages = [1, 2, 3, 4]

print("=== スクレイピングを開始します ===")

for page_num in target_pages:
    url = f"{base_url}&page={page_num}"
    print(f"\n--- {page_num} ページ目を読み込み中: {url} ---")

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"アクセス失敗 (Status: {response.status_code})")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # リポジトリ名のリンクを探す
        repo_links = soup.find_all('a', attrs={"itemprop": "name codeRepository"})
        
        if not repo_links:
            print("リポジトリが見つかりませんでした。")
            break

        print(f"{len(repo_links)} 件のデータを取得・保存中...")

        for link in repo_links:
            try:
                # A. リポジトリ名
                repo_name = link.text.strip()

                # 親要素(liタグ)に遡って情報を探す
                container = link.find_parent('li')

                if container:
                    # B. 言語
                    lang_tag = container.find('span', attrs={"itemprop": "programmingLanguage"})
                    language = lang_tag.text.strip() if lang_tag else "No Language"

                    # C. スター数
                    star_tag = container.find('a', href=re.compile(r'/stargazers$'))
                    if star_tag:
                        star_text = star_tag.text.strip().replace(',', '')
                        try:
                            stars = int(star_text)
                        except ValueError:
                            stars = 0
                    else:
                        stars = 0
                else:
                    language = "Unknown"
                    stars = 0

                # D. データベースへ保存
                cur.execute('INSERT INTO repositories (name, language, stars) VALUES (?, ?, ?)', 
                            (repo_name, language, stars))
                
            except Exception as e:
                continue

        conn.commit()
        time.sleep(2) # サーバー負荷軽減

    except Exception as e:
        print(f"エラー: {e}")
        break

print("\n=== 全ページの処理が完了しました ===")


# --- 3. 【重要】保存データの表示 (課題要件: SELECT文で表示) ---
print("\n" + "="*50)
print("   データベース保存結果一覧 (SELECT * FROM repositories)")
print("="*50)

# 保存された全データをスター数が多い順に取得して表示
cur.execute('SELECT * FROM repositories ORDER BY stars DESC')
rows = cur.fetchall()

for row in rows:
    # rowは (id, name, language, stars) のタプル
    print(f"ID: {row[0]:<4} | Name: {row[1]:<35} | Lang: {row[2]:<15} | Stars: {row[3]}")

print("="*50)
print(f"合計 {len(rows)} 件のリポジトリ情報を表示しました。")

conn.close()