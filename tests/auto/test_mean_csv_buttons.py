#!/usr/bin/env python3
"""Selenium test: Mean / CSV buttons under the Input-vector slider.

Verifies:
  1. Both buttons render under the slider.
  2. Clicking Mean toggles active state + disables the slider + recolors the field
     (status line reads "mean (100 vectors)"); clicking again restores single-vector.
  3. Clicking CSV downloads formS6_inputs.csv with 300 data rows (3 cats x 100).

Run:  source venv/bin/activate && python tests/auto/test_mean_csv_buttons.py
"""
import os, sys, time, glob, logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://localhost:8012/web/index.html"
DOWNLOAD_DIR = os.path.join(HERE, "downloads")
LOG = os.path.join(HERE, "test_mean_csv_buttons.log")

logging.basicConfig(filename=LOG, filemode="w", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger()


def info(msg):
    log.info(msg)
    print(msg, flush=True)


def main():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    for f in glob.glob(os.path.join(DOWNLOAD_DIR, "formS6_inputs*.csv")):
        os.remove(f)

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,900")
    opts.add_experimental_option("prefs", {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
    })
    driver = webdriver.Chrome(options=opts)
    failures = []
    try:
        info(f"Loading {URL}")
        driver.get(URL)
        wait = WebDriverWait(driver, 30)

        # 1. app initialized: grid loaded -> status no longer "Loading grid…"
        wait.until(lambda d: "Loading grid" not in
                   d.find_element(By.ID, "info").text)
        info("App initialized: " + driver.find_element(By.ID, "info").text)

        # 1b. buttons present
        btn_mean = wait.until(EC.presence_of_element_located((By.ID, "btnMean")))
        btn_csv = driver.find_element(By.ID, "btnCsv")
        info(f"Buttons found: Mean='{btn_mean.text}' CSV='{btn_csv.text}'")
        if btn_mean.text.strip() != "Mean":
            failures.append("Mean button label wrong")
        if btn_csv.text.strip() != "CSV":
            failures.append("CSV button label wrong")

        slider = driver.find_element(By.ID, "vector")
        if slider.get_attribute("disabled"):
            failures.append("slider unexpectedly disabled before Mean toggle")

        # 2. toggle Mean ON — wait for the computed mean tag "(100 vectors)"
        # (note: normal wind status already contains "land mean", so key on the tag)
        btn_mean.click()
        wait.until(lambda d: "(100 vectors)" in d.find_element(By.ID, "info").text)
        active = "active" in (btn_mean.get_attribute("class") or "")
        disabled = bool(slider.get_attribute("disabled"))
        status = driver.find_element(By.ID, "info").text
        info(f"After Mean ON: active={active} sliderDisabled={disabled} status='{status}'")
        if not active:
            failures.append("Mean button missing 'active' class when on")
        if not disabled:
            failures.append("slider not disabled in mean mode")
        if "(100 vectors)" not in status:
            failures.append(f"status line lacks mean tag: {status!r}")

        # 2b. toggle Mean OFF
        btn_mean.click()
        wait.until(lambda d: "(100 vectors)" not in d.find_element(By.ID, "info").text)
        active2 = "active" in (btn_mean.get_attribute("class") or "")
        disabled2 = bool(slider.get_attribute("disabled"))
        info(f"After Mean OFF: active={active2} sliderDisabled={disabled2}")
        if active2:
            failures.append("Mean button still active after toggle off")
        if disabled2:
            failures.append("slider still disabled after toggle off")

        # 2c. live-model mean path (Holland computes 100 fields in the browser)
        from selenium.webdriver.support.ui import Select
        Select(driver.find_element(By.ID, "model")).select_by_value("holland")
        wait.until(lambda d: "Holland" in d.find_element(By.ID, "info").text)
        btn_mean.click()
        wait.until(lambda d: "(100 vectors)" in d.find_element(By.ID, "info").text)
        hstat = driver.find_element(By.ID, "info").text
        info(f"Holland mean: '{hstat}'")
        if "Peak wind" not in hstat:
            failures.append(f"Holland mean produced no wind stats: {hstat!r}")
        btn_mean.click()  # back off
        wait.until(lambda d: "(100 vectors)" not in d.find_element(By.ID, "info").text)
        Select(driver.find_element(By.ID, "model")).select_by_value("powell")

        # 3. CSV download
        btn_csv.click()
        csv_path = None
        for _ in range(20):
            hits = glob.glob(os.path.join(DOWNLOAD_DIR, "formS6_inputs.csv"))
            if hits and not glob.glob(os.path.join(DOWNLOAD_DIR, "*.crdownload")):
                csv_path = hits[0]
                break
            time.sleep(0.5)
        if not csv_path:
            failures.append("CSV file did not download")
        else:
            with open(csv_path) as fh:
                lines = [ln for ln in fh.read().splitlines() if ln.strip()]
            header, data = lines[0], lines[1:]
            info(f"CSV header: {header}")
            info(f"CSV data rows: {len(data)} (first: {data[0]})")
            expected_cols = "Category,Vector,CP,Rmax,VT,WSP,CF,FFP"
            if header != expected_cols:
                failures.append(f"CSV header mismatch: {header!r}")
            if len(data) != 300:
                failures.append(f"CSV expected 300 data rows, got {len(data)}")
            cats = {ln.split(",")[0] for ln in data}
            if cats != {"1", "3", "5"}:
                failures.append(f"CSV categories unexpected: {cats}")

        driver.save_screenshot(os.path.join(HERE, "selenium_mean_csv.png"))
    finally:
        driver.quit()

    if failures:
        info("FAIL:\n  - " + "\n  - ".join(failures))
        sys.exit(1)
    info("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
