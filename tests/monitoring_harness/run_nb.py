# TEST: wykonanie notatnika w jądrze colab313 (jak tests/colab_harness/run_nb.py, dłuższy limit czasu komórki).
# Użycie: python run_nb.py <notatnik> <wynik.ipynb> <katalog roboczy jądra>
import sys
import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

nb = nbformat.read(sys.argv[1], as_version=4)
client = NotebookClient(nb, timeout=3600, kernel_name="colab313", resources={"metadata": {"path": sys.argv[3]}})
status = "OK"
try:
    client.execute()
except CellExecutionError as e:
    status = "BŁĄD: " + str(e).strip().splitlines()[-1][:400]
nbformat.write(nb, sys.argv[2])
full = []
for i, c in enumerate([c for c in nb.cells if c.cell_type == "code"], start=1):
    out = []
    for o in c.get("outputs", []):
        if o.output_type == "stream":
            out.append(o.text)
        elif o.output_type == "error":
            out.append("ERROR " + o.ename + ": " + o.evalue)
        elif "text/markdown" in o.get("data", {}):     # Markdown(...) w notatnikach pokazowych
            out.append(o.data["text/markdown"] + "\n")
        elif "text/html" in o.get("data", {}):         # tabele HTML(...) w notatnikach pokazowych
            out.append(o.data["text/html"] + "\n")
        elif "text/plain" in o.get("data", {}):
            out.append(o.data["text/plain"])
    full.append(f"===== komórka kodu {i} =====\n" + "".join(out))
    print(f"===== komórka kodu {i} =====")
    print("".join(out)[-3000:])
with open(sys.argv[2] + ".txt", "w", encoding="utf-8") as f:     # pełne wyjście komórek (do grep w run_harness.sh)
    f.write("\n".join(full) + f"\nSTATUS: {status}\n")
print("STATUS:", status)
sys.exit(0 if status == "OK" else 1)
