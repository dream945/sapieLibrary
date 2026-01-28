# -*- coding: utf-8 -*-
# Debug version of Sapie Client - helps identify correct selectors

import sys
import os

# Add bundled Selenium to path
current_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(current_dir, "lib")
if lib_path not in sys.path:
	sys.path.insert(0, lib_path)

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

def debug_sapie_login_page():
	"""
	デバッグツール: サピエのログインページを解析して、
	正しいセレクターを見つけます
	"""

	print("=== サピエログインページ解析ツール ===\n")

	driver = None
	try:
		# ブラウザ起動
		print("1. ブラウザを起動中...")
		options = webdriver.ChromeOptions()
		# デバッグ用にヘッドレスモードOFF（画面を表示）
		# options.add_argument('--headless')
		options.add_argument('--lang=ja')

		try:
			driver = webdriver.Chrome(options=options)
		except Exception as e:
			print(f"  Chrome起動エラー: {e}")
			print("  Edgeを試します...")
			try:
				from selenium.webdriver.edge.options import Options as EdgeOptions
				edge_options = EdgeOptions()
				edge_options.add_argument('--lang=ja')
				driver = webdriver.Edge(options=edge_options)
			except Exception as e2:
				print(f"  Edge起動エラー: {e2}")
				raise Exception("ChromeもEdgeも起動できませんでした。ブラウザがインストールされているか確認してください。")

		print("  ✓ ブラウザ起動成功\n")

		# ログインページにアクセス
		print("2. ログインページにアクセス中...")
		LOGIN_URL = "https://member.sapie.or.jp/login"
		driver.get(LOGIN_URL)
		time.sleep(3)  # ページ読み込み待ち
		print(f"  現在のURL: {driver.current_url}")
		print(f"  ページタイトル: {driver.title}\n")

		# すべての入力フィールドを検索
		print("3. ページ内のすべての入力フィールドを検索:\n")
		inputs = driver.find_elements(By.TAG_NAME, "input")

		print(f"  見つかった入力フィールド: {len(inputs)}個\n")

		for i, inp in enumerate(inputs):
			inp_type = inp.get_attribute("type") or "text"
			inp_id = inp.get_attribute("id") or "(なし)"
			inp_name = inp.get_attribute("name") or "(なし)"
			inp_class = inp.get_attribute("class") or "(なし)"
			inp_placeholder = inp.get_attribute("placeholder") or "(なし)"

			print(f"  [{i+1}] type='{inp_type}'")
			print(f"      id='{inp_id}'")
			print(f"      name='{inp_name}'")
			print(f"      class='{inp_class}'")
			print(f"      placeholder='{inp_placeholder}'")
			print()

		# すべてのボタンを検索
		print("4. ページ内のすべてのボタンを検索:\n")
		buttons = driver.find_elements(By.TAG_NAME, "button")

		print(f"  見つかったボタン: {len(buttons)}個\n")

		for i, btn in enumerate(buttons):
			btn_type = btn.get_attribute("type") or "button"
			btn_id = btn.get_attribute("id") or "(なし)"
			btn_class = btn.get_attribute("class") or "(なし)"
			btn_text = btn.text or "(なし)"

			print(f"  [{i+1}] type='{btn_type}'")
			print(f"      id='{btn_id}'")
			print(f"      class='{btn_class}'")
			print(f"      テキスト='{btn_text}'")
			print()

		# submitボタンも検索
		submit_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='submit']")
		if submit_inputs:
			print(f"  submitタイプの入力: {len(submit_inputs)}個\n")
			for i, sub in enumerate(submit_inputs):
				sub_id = sub.get_attribute("id") or "(なし)"
				sub_name = sub.get_attribute("name") or "(なし)"
				sub_value = sub.get_attribute("value") or "(なし)"
				print(f"  [{i+1}] id='{sub_id}', name='{sub_name}', value='{sub_value}'")
				print()

		# フォームを検索
		print("5. フォーム要素を検索:\n")
		forms = driver.find_elements(By.TAG_NAME, "form")
		print(f"  見つかったフォーム: {len(forms)}個\n")

		for i, form in enumerate(forms):
			form_id = form.get_attribute("id") or "(なし)"
			form_name = form.get_attribute("name") or "(なし)"
			form_action = form.get_attribute("action") or "(なし)"
			form_method = form.get_attribute("method") or "(なし)"

			print(f"  [{i+1}] id='{form_id}'")
			print(f"      name='{form_name}'")
			print(f"      action='{form_action}'")
			print(f"      method='{form_method}'")
			print()

		# 結果の保存
		print("6. HTMLソースを保存中...")
		html_source = driver.page_source

		output_file = "C:\\prg\\claudecode\\sapie_login_page.html"
		with open(output_file, "w", encoding="utf-8") as f:
			f.write(html_source)

		print(f"  ✓ HTMLを保存しました: {output_file}\n")

		# 推奨セレクター
		print("=" * 60)
		print("推奨される修正:")
		print("=" * 60)
		print("\n上記の情報を基に、sapieClient.py の以下を修正してください:\n")

		print("【ユーザー名フィールド】")
		print("  - type='text' または type='email' のフィールドを探す")
		print("  - name や id を確認\n")

		print("【パスワードフィールド】")
		print("  - type='password' のフィールドを探す")
		print("  - name や id を確認\n")

		print("【ログインボタン】")
		print("  - type='submit' のボタンまたは入力を探す")
		print("  - テキストに'ログイン'が含まれるものを確認\n")

		print("\n※ ブラウザは自動的には閉じません。")
		print("   内容を確認後、手動で閉じてください。")

		input("\nEnterキーを押すとブラウザを閉じます...")

	except WebDriverException as e:
		print(f"\nエラー: ブラウザドライバーが見つかりません")
		print(f"詳細: {str(e)}")
		print("\nChromeまたはEdgeがインストールされているか確認してください。")

	except Exception as e:
		print(f"\nエラーが発生しました: {str(e)}")
		import traceback
		traceback.print_exc()

	finally:
		if driver:
			driver.quit()
		print("\n解析完了。")

if __name__ == "__main__":
	debug_sapie_login_page()
