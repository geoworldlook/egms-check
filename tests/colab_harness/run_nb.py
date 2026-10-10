import sys, json, nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError
nb = nbformat.read(sys.argv[1], as_version=4)
client = NotebookClient(nb, timeout=900, kernel_name="colab313", resources={"metadata": {"path": sys.argv[3]}})
status = "OK"
try:
    client.execute()
except CellExecutionError as e:
    status = "BŁĄD: " + str(e).splitlines()[-1][:300]
nbformat.write(nb, sys.argv[2])
for i, c in enumerate([c for c in nb.cells if c.cell_type == "code"], start=1):
    out = []
    for o in c.get("outputs", []):
        if o.output_type == "stream": out.append(o.text)
        elif o.output_type == "error": out.append("ERROR " + o.ename + ": " + o.evalue)
        elif "text/plain" in o.get("data", {}): out.append(o.data["text/plain"])
    print(f"===== komórka kodu {i} =====")
    print("".join(out)[-2500:])
print("STATUS:", status)
