"""
Custom cell runner to execute main.ipynb and capture stdout, stderr, and base64 matplotlib plots.
"""

import json
import sys
import io
import contextlib
import base64
from pathlib import Path

def run_notebook():
    nb_path = Path("main.ipynb")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Execution namespace
    global_scope = {}

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    exec_count = 1

    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue

        code_text = "".join(cell["source"])
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        outputs = []

        # Hook plt.show to capture figure in outputs
        fig_outputs = []
        original_show = plt.show

        def capture_show(*args, **kwargs):
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)
                buf = io.BytesIO()
                fig.savefig(buf, format="png", bbox_inches="tight")
                buf.seek(0)
                b64_data = base64.b64encode(buf.read()).decode("utf-8")
                fig_outputs.append({
                    "data": {
                        "image/png": b64_data,
                        "text/plain": ["<Figure size ...>"]
                    },
                    "metadata": {},
                    "output_type": "display_data"
                })
            plt.close("all")

        plt.show = capture_show

        print(f"Executing Code Cell #{exec_count}...")
        try:
            with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                exec(code_text, global_scope)
        except Exception as e:
            err_msg = f"{type(e).__name__}: {str(e)}"
            print(f"ERROR in cell {exec_count}: {err_msg}")
            outputs.append({
                "ename": type(e).__name__,
                "evalue": str(e),
                "output_type": "error",
                "traceback": [err_msg]
            })
        finally:
            plt.show = original_show

        stdout_val = stdout_buf.getvalue()
        if stdout_val:
            outputs.append({
                "name": "stdout",
                "output_type": "stream",
                "text": stdout_val.splitlines(keepends=True)
            })

        stderr_val = stderr_buf.getvalue()
        if stderr_val:
            outputs.append({
                "name": "stderr",
                "output_type": "stream",
                "text": stderr_val.splitlines(keepends=True)
            })

        outputs.extend(fig_outputs)

        cell["execution_count"] = exec_count
        cell["outputs"] = outputs
        exec_count += 1

    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)

    print(f"All {exec_count - 1} code cells executed successfully. Saved outputs into {nb_path}.")

if __name__ == "__main__":
    run_notebook()
