# Bài B: người canh, phần kiểm bằng code

- Ngày: 2026-10-19
- Commit: `455c3223438706d8cac4f2d3996f68c8a59e5d20`
- Hash đầu vào (sha256, 16 ký tự đầu): `6262603da8f04fdc` của evals/scenarios/guard-b/cases.yaml, config/guard.yaml, data/sample-story/graph.yaml
- Model: không dùng model (phần kiểm bằng code)
- Lệnh: `cd backend && uv run python -m writory.guard.bench_b --out <thư mục này>`

| Phép kiểm | Ca lỗi | Bắt được | Recall | Ca sạch | Báo nhầm |
|---|---|---|---|---|---|
| chapter_rule | 2 | 2 | 100% | 2 | 0 |
| dead_actor | 4 | 4 | 100% | 4 | 0 |
| at_most_one | 3 | 3 | 100% | 4 | 0 |
| teller_does_not_know | 2 | 2 | 100% | 4 | 0 |
| early_reveal | 2 | 2 | 100% | 3 | 0 |
| sudden_relationship | 2 | 2 | 100% | 5 | 0 |

Loại lỗi báo ngoài `expect` (mọi ca): 0
