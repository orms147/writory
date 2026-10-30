"""In khoá support của hệ đồ thị cho mọi câu của ba đề cũ: so trước và sau sửa D-144."""
import json
import sys

from writory.pipeline.bench_a import ContextBuilder
from writory.pipeline.bench_a_data import context_supports, load_data

out = {}
for qf in ("questions.yaml", "questions-ky-ao-vua-1.yaml", "questions-ky-ao-vua-1-facts.yaml"):
    data = load_data(questions_file=qf)
    summaries = {k: f"TÓM-TẮT-GIẢ-{k}" for k in data.story}
    builder = ContextBuilder(data, data.state_at, summaries)
    for q in data.questions.questions:
        for system in ("graph", "graph_quotes"):
            try:
                ctx = builder.build(system, q)
                out[f"{qf}:{q.id}:{system}"] = [context_supports(q, ctx, data), len(ctx.text)]
            except Exception as e:  # noqa: BLE001
                out[f"{qf}:{q.id}:{system}"] = [f"error {type(e).__name__}", 0]
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=0, sort_keys=True)
print(len(out))
