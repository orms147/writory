# Bài B: người canh, phần kiểm bằng code

- Ngày: 2026-10-20
- Commit: `2132238c225dddcd5d7514a932602572c9eebb92`
- Hash đầu vào (sha256, 16 ký tự đầu): `a68a67824273cc70` của evals/scenarios/guard-b/cases.yaml, config/guard.yaml, data/sample-story/graph.yaml
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
| overdue_secret | 2 | 2 | 100% | 4 | 0 |
| overdue_thread | 2 | 2 | 100% | 5 | 0 |

Loại lỗi báo ngoài `expect` (mọi ca): 0
