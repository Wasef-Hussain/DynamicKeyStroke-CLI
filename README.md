# DynamicKey — Privacy-First Keystroke Dynamics CLI Tool

DynamicKey is a **secure**, **ethical**, and **privacy-respecting** command-line tool built in Python.  
It measures **keystroke dynamics** — the timing intervals between key presses — to generate meaningful local insights.

No backend server, no external data collection.  
All processing and report generation happen **locally on your machine**.

---

## 🚀 Features

- ⌨️ Capture timing data between key presses (inter-key intervals & key hold durations)  
- 🔒 Anonymize keys using SHA256 with a random session salt  
- 📊 Generate **JSON** and **HTML** reports with detailed analysis  
- 💬 Optionally send summarized metrics to a **Discord webhook** (no raw key data ever sent)  
- 🧭 No backend — runs completely offline  

---

## 📦 Installation

Make sure you have Python **3.8+** installed.

```bash
git clone https://github.com/Wasef-Hussain/DynamicKeyStroke-CLI.git
cd DynamicKey
pip install -r requirements.txt


🧠 Usage

Run the tool directly from the command line:

python cli.py --phrase "the quick brown fox" --rounds 5



Options
Argument	Description	Default
--phrase	The phrase you want to type for timing measurement	"the quick brown fox"
--rounds	Number of times to repeat typing	3
--out-json	Output path for the JSON report	keystroke_report.json
--out-html	Output path for the HTML report	keystroke_report.html
--discord-webhook	(Optional) Send summary to Discord	None
--store-chars	Store raw characters instead of hashed values (requires consent)	False
📄 Output

After completion, two files are generated:

keystroke_report.json – Detailed timing data and aggregate stats

keystroke_report.html – Clean and visual summary report

Example JSON excerpt:

{
  "metadata": {
    "session_id": "2e4b1f...",
    "phrase": "the quick brown fox",
    "rounds_requested": 3,
    "anonymized_keys": true
  },
  "aggregate": {
    "inter_key_intervals": {"mean": 0.142, "stdev": 0.05},
    "key_hold_times": {...}
  }
}

🔔 Discord Summary (Optional)

You can provide a Discord webhook URL to send only summarized metrics (no raw data):

python cli.py --discord-webhook https://discord.com/api/webhooks/XXXX/XXXX

⚙️ Ethical & Privacy Notes

No raw key data or personally identifiable information leaves your machine.

All timing data is anonymized by default using salted SHA256 hashes.

Use this tool responsibly and only with full user consent.

🧑‍💻 Example Session
Phrase: the quick brown fox
Rounds: 3
Press ENTER to start each round, type the phrase, and press ENTER again to finish.

Round 1 completed: duration=4.12s
Round 2 completed: duration=3.98s
Round 3 completed: duration=4.31s
JSON saved to keystroke_report.json
HTML saved to keystroke_report.html
Done. Data stored locally — keep it private.

📘 License

This project is released under the MIT License.
Use it freely, learn from it, and contribute improvements.

Developed by: [Wasef Hussain]
🔗 GitHub: https://github.com/Wasef-Hussain/DynamicKeyStroke-CLI.git


---

### ⚙️ **requirements.txt**

```txt
pynput
requests